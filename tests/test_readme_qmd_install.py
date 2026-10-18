"""Regression checks for the documented QMD installation instructions."""
from pathlib import Path
import unittest


class ReadmeQmdInstallTests(unittest.TestCase):
    def test_readme_documents_main_tip_and_reproducible_release_install(self):
        readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
        main_install = "pipx install git+https://github.com/ozand/kb-bootstrap.git"
        pinned_install = main_install + "@v0.4.0"
        self.assertIn(main_install, readme)
        self.assertIn(pinned_install, readme)
        self.assertIn("older published v0.4.0 release", readme)
        self.assertIn("not the latest `main` code", readme)
        self.assertNotIn("latest release", readme)

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
