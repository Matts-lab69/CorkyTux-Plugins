"""Regression coverage for the vendored sandbox executable lookup policy."""

import ast
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch


def sandbox_executable():
    source = (
        Path(__file__).resolve().parents[1]
        / "vendor/box-rpg-src/box/launch/sandbox.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    # Execute the actual import and assignment nodes without initializing the
    # sandbox or importing its unrelated engine/runtime dependencies.
    nodes = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Import)
            and any(alias.name == "shutil" for alias in node.names)
        )
        or (isinstance(node, ast.ImportFrom) and node.module == "pathlib")
        or (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "BWRAP"
                for target in node.targets
            )
        )
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["BWRAP"]


class BubblewrapPathTests(unittest.TestCase):
    def test_prefers_executable_resolved_from_path(self):
        with patch.object(shutil, "which", return_value="/custom/bin/bwrap") as lookup:
            self.assertEqual(sandbox_executable(), Path("/custom/bin/bwrap"))
            lookup.assert_called_once_with("bwrap")

    def test_retains_system_fallback_when_path_has_no_match(self):
        with patch.object(shutil, "which", return_value=None):
            self.assertEqual(sandbox_executable(), Path("/usr/bin/bwrap"))
