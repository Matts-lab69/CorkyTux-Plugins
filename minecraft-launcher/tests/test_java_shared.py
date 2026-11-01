import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path

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


    def test_the_lock_serializes_two_writers(self):
        import fcntl
        import multiprocessing
        import time

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "java.lock"

            def child(started, order):
                with open(lock_path, "w") as fh:
                    fcntl.flock(fh, fcntl.LOCK_EX)
                    order.put("child")
                    time.sleep(0.05)
                    fcntl.flock(fh, fcntl.LOCK_UN)
                    started.set()

            ctx = multiprocessing.get_context("fork")
            started = ctx.Event()
            order = ctx.Queue()
            proc = ctx.Process(target=child, args=(started, order))
            proc.start()
            with open(lock_path, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                # While the parent holds the lock the child must not proceed.
                self.assertTrue(order.empty())
                fcntl.flock(fh, fcntl.LOCK_UN)
            proc.join(timeout=5)
            self.assertEqual(order.get(timeout=1), "child")
            self.assertTrue(started.is_set())


if __name__ == "__main__":
    unittest.main()
