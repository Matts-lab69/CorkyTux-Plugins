import fcntl
import importlib.util
import multiprocessing
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def _install_worker(java_dir, lock_attempting, result_queue):
    m.JAVA_DIR = Path(java_dir)
    real_flock = fcntl.flock
    emitted = []

    def observed_flock(lock, operation):
        if operation == fcntl.LOCK_EX:
            lock_attempting.set()
        return real_flock(lock, operation)

    try:
        with mock.patch.object(m, "_read_java_json", return_value={"installs": {}}), \
                mock.patch.object(m, "_write_java_json"), \
                mock.patch.object(m, "emit", side_effect=emitted.append), \
                mock.patch.object(fcntl, "flock", side_effect=observed_flock), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("downloaded")):
            m.cmd_java_install(SimpleNamespace(version="17"))
        result_queue.put({"ok": True, "events": emitted})
    except BaseException as error:
        result_queue.put({"ok": False, "error": repr(error)})


SCRIPT = Path(__file__).resolve().parents[1] / "minecraft-launcher"


def load_module():
    spec = importlib.util.spec_from_loader(
        "mc_java_shared", importlib.machinery.SourceFileLoader("mc_java_shared", str(SCRIPT))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = load_module()


class JavaSharedTests(unittest.TestCase):
    def test_major_of_version_strings(self):
        self.assertEqual(m.java_major("17"), 17)
        self.assertEqual(m.java_major("17.0.9"), 17)
        self.assertEqual(m.java_major("1.8"), 8)
        self.assertEqual(m.java_major("21.0.1+12"), 21)

    def test_one_directory_per_major(self):
        base = Path("/tmp/java-base")
        self.assertEqual(m.java_dir_for("17", base), base / "17")
        self.assertEqual(m.java_dir_for("17.0.9", base), base / "17")
        self.assertEqual(m.java_dir_for("21", base), base / "21")

    def test_existing_java_bin_requires_a_working_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dest = base / "17"
            self.assertEqual(m.existing_java_bin(dest), "")
            (dest / "jdk-17" / "bin").mkdir(parents=True)
            java = dest / "jdk-17" / "bin" / "java"
            java.write_text('#!/bin/sh\necho \'openjdk version "17.0.9" 2024-01-01\' >&2\n')
            java.chmod(java.stat().st_mode | stat.S_IXUSR)
            self.assertEqual(m.existing_java_bin(dest), str(java))
            # A directory with no usable binary is not reused.
            bad = base / "21"
            (bad / "bin").mkdir(parents=True)
            (bad / "bin" / "java").write_text("#!/bin/sh\nexit 1\n")
            (bad / "bin" / "java").chmod(0o755)
            self.assertEqual(m.existing_java_bin(bad), "")

    def test_install_reuses_existing_java_without_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            java_dir = Path(tmp)
            java = java_dir / "17" / "jdk-17" / "bin" / "java"
            java.parent.mkdir(parents=True)
            java.write_text('#!/bin/sh\necho \'openjdk version "17.0.9" 2024-01-01\' >&2\n')
            java.chmod(java.stat().st_mode | stat.S_IXUSR)
            with mock.patch.object(m, "JAVA_DIR", java_dir), \
                    mock.patch.object(m, "_read_java_json", return_value={"installs": {}}), \
                    mock.patch.object(m, "_write_java_json"), \
                    mock.patch.object(m, "emit") as emit, \
                    mock.patch("urllib.request.urlopen", side_effect=AssertionError("downloaded")):
                m.cmd_java_install(SimpleNamespace(version="17"))

            self.assertEqual(emit.call_args.args[0]["path"], str(java))
            self.assertTrue(emit.call_args.args[0]["reused"])

    def test_install_waits_for_lock_then_reuses_java_installed_by_other_process(self):
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as tmp:
            java_dir = Path(tmp)
            lock_path = java_dir / ".java.lock"
            lock_attempting = context.Event()
            result_queue = context.Queue()
            process = context.Process(
                target=_install_worker,
                args=(str(java_dir), lock_attempting, result_queue),
            )
            with open(lock_path, "w") as held_lock:
                fcntl.flock(held_lock, fcntl.LOCK_EX)
                process.start()
                try:
                    self.assertTrue(lock_attempting.wait(5), "install did not attempt lock")
                    process.join(0.1)
                    self.assertTrue(process.is_alive(), "install escaped held lock")
                    java = java_dir / "17" / "jdk-17" / "bin" / "java"
                    java.parent.mkdir(parents=True)
                    java.write_text(
                        '#!/bin/sh\necho \'openjdk version "17.0.9" 2024-01-01\' >&2\n'
                    )
                    java.chmod(java.stat().st_mode | stat.S_IXUSR)
                    fcntl.flock(held_lock, fcntl.LOCK_UN)
                    result = result_queue.get(timeout=5)
                    process.join(5)
                finally:
                    if process.is_alive():
                        fcntl.flock(held_lock, fcntl.LOCK_UN)
                        process.join(5)
                    if process.is_alive():
                        process.terminate()
                        process.join(5)
                self.assertEqual(process.exitcode, 0)
                self.assertTrue(result["ok"], result.get("error"))
                done = [event for event in result["events"] if event.get("type") == "done"]
                self.assertEqual(len(done), 1)
                self.assertTrue(done[0]["reused"])
                self.assertEqual(done[0]["path"], str(java))


if __name__ == "__main__":
    unittest.main()
