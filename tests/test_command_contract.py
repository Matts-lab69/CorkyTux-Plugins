"""Contract between the launcher and every plugin's CLI.

`command_contract.json` is the inventory from
`docs/PLUGIN_PROTOCOL.md` section 9 (launcher side, not the v1 target).
The test fails when a plugin drops or renames a command the launcher sends;
regenerate the JSON from the protocol table after a deliberate change.
"""

import importlib.util
import json
from importlib.machinery import SourceFileLoader
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests" / "command_contract.json").read_text())

DISPATCHERS = {"appimage-launcher", "rpgmaker-runtime"}
ARGPARSE = {"heroic-store", "minecraft-launcher"}


def script_for(plugin):
    return ROOT / plugin / plugin


def load_module(path):
    name = "contract_" + path.parent.name.replace("-", "_")
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class CommandContract(unittest.TestCase):
    def test_dispatch_tables_expose_every_documented_command(self):
        for plugin in sorted(DISPATCHERS):
            module = load_module(script_for(plugin))
            documented = {entry["command"] for entry in CONTRACT[plugin]}
            actual = set(module.COMMANDS)
            self.assertEqual(
                documented - actual,
                set(),
                f"{plugin} is missing launcher commands: {sorted(documented - actual)}",
            )

    def test_argparse_plugins_accept_every_documented_command(self):
        for plugin in sorted(ARGPARSE):
            for entry in CONTRACT[plugin]:
                command = entry["command"]
                with self.subTest(plugin=plugin, command=command):
                    proc = subprocess.run(
                        [str(script_for(plugin)), command, "--help"],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    self.assertEqual(
                        proc.returncode,
                        0,
                        f"{plugin} {command} --help failed: {proc.stderr[-300:]}",
                    )
                    self.assertIn(command, proc.stdout)
                    for flag in entry["flags"]:
                        self.assertIn(
                            flag,
                            proc.stdout,
                            f"{plugin} {command} help lost {flag}",
                        )

    def test_custom_parsers_mention_every_documented_command(self):
        for plugin in sorted(set(CONTRACT) - DISPATCHERS - ARGPARSE):
            source = script_for(plugin).read_text()
            for entry in CONTRACT[plugin]:
                command = entry["command"]
                with self.subTest(plugin=plugin, command=command):
                    self.assertIn(
                        command,
                        source,
                        f"{plugin} no longer mentions the launcher command {command}",
                    )
                    for flag in entry["flags"]:
                        self.assertIn(
                            flag,
                            source,
                            f"{plugin} no longer mentions {command} {flag}",
                        )


if __name__ == "__main__":
    unittest.main()
