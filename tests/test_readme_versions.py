"""Keep the plugin overview aligned with the shipped manifest versions."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReadmeVersions(unittest.TestCase):
    def test_updated_plugin_versions_match_manifests(self):
        readme = (ROOT / "README.md").read_text()
        sections = {
            "minecraft-launcher": "Minecraft Launcher",
            "heroic-store": "Heroic Store (Epic/GOG)",
        }
        for plugin, heading in sections.items():
            with self.subTest(plugin=plugin):
                manifest = json.loads((ROOT / plugin / "plugin.json").read_text())
                match = re.search(
                    rf"^### \d+\. {re.escape(heading)}\n\n\*\*Version:\*\* ([^\s|]+)",
                    readme,
                    re.MULTILINE,
                )
                self.assertIsNotNone(match, f"Missing version section for {plugin}")
                self.assertEqual(match.group(1), manifest["version"])


if __name__ == "__main__":
    unittest.main()
