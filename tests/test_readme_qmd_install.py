"""Regression checks for the documented QMD installation instructions."""
from pathlib import Path
import unittest


class ReadmeQmdInstallTests(unittest.TestCase):
    def test_readme_uses_supported_npm_install_and_node_requirement(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
        self.assertIn("Node.js 22 or newer", readme)
        self.assertIn("npm install -g @tobilu/qmd", readme)
        self.assertIn("bun install -g @tobilu/qmd", readme)
        self.assertIn("qmd --version", readme)
        self.assertNotIn("go install github.com/tobi/qmd", readme)
        self.assertNotIn("Install Go", readme)


if __name__ == "__main__":
    unittest.main()
