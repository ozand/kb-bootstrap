import os
import shutil
import argparse
import sys
from pathlib import Path

from .graph_linter import validate
from .qmd_validator import validate_qmd_collections

def create_dirs(base_path: Path, dirs: list):
    for d in dirs:
        (base_path / d).mkdir(parents=True, exist_ok=True)


def project_slug(target: Path) -> str:
    slug = "".join(
        character.lower() if character.isalnum() or character in "._-" else "-"
        for character in target.name
    ).strip("-._")
    return slug or "project"


def append_gitignore_rules(target: Path) -> None:
    marker = "# kb-bootstrap generated artifacts"
    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if marker in existing:
        return
    separator = "" if not existing or existing.endswith("\n") else "\n"
    with open(gitignore, "a", encoding="utf-8") as file:
        file.write(
            separator
            + "\n# kb-bootstrap generated artifacts\n"
            "/models/\n/artifacts/\n"
            "/kb/raw/**/*.log\n/kb/raw/**/*.bin\n/kb/raw/**/*.jsonl\n"
        )


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Knowledge Base architecture (OKF + QMD)")
    parser.add_argument("--target", default=".", help="Target directory for initialization (default: current directory)")
    parser.add_argument("--type", choices=["single", "umbrella"], default="single", help="Project architecture type")
    subparsers = parser.add_subparsers(dest="command")
    validate_parser = subparsers.add_parser(
        "validate", help="Validate Markdown links and QMD collection configuration"
    )
    validate_parser.add_argument("--dir", default="docs", help="Base directory to scan")
    validate_parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing qmd/collections (default: current directory)",
    )
    args = parser.parse_args()

    if args.command == "validate":
        graph_report, graph_valid = validate(args.dir)
        qmd_report, qmd_valid = validate_qmd_collections(args.project_root)
        print(graph_report)
        print()
        print(qmd_report)
        return 0 if graph_valid and qmd_valid else 1

    target = Path(args.target).resolve()
    # The package directory is where this cli.py is located
    pkg_dir = Path(__file__).parent.resolve()

    print(f"Initializing {args.type} Knowledge Base in {target}...")

    # Create skill directories
    create_dirs(target, [
        ".agents/skills/qmd-operator", 
        ".agents/skills/kb-wiki-builder", 
        ".agents/skills/kb-capture", 
        ".agents/skills/kb-lookup"
    ])
    
    # Copy skills
    skills_src = pkg_dir / "templates" / "skills"
    shutil.copy2(skills_src / "qmd-operator" / "SKILL.md", target / ".agents/skills/qmd-operator/SKILL.md")
    shutil.copy2(skills_src / "kb-wiki-builder" / "SKILL.md", target / ".agents/skills/kb-wiki-builder/SKILL.md")
    shutil.copy2(skills_src / "kb-capture" / "SKILL.md", target / ".agents/skills/kb-capture/SKILL.md")
    shutil.copy2(skills_src / "kb-lookup" / "SKILL.md", target / ".agents/skills/kb-lookup/SKILL.md")

    project_name = project_slug(target)

    if args.type == "umbrella":
        create_dirs(
            target,
            ["qmd/collections", "kb/apps", "kb/systems", "kb/architecture", "kb/raw"],
        )

        qmd_config = """{
  "version": "1.0",
  "workspace": {
    "name": "%s_kb",
    "collections_dir": "./qmd/collections",
    "db_path": ".qmd/vector.db"
  },
  "models": {
    "embedding": "text-embedding-3-small"
  }
}""" % project_name
        with open(target / "qmd.json", "w", encoding="utf-8") as f:
            f.write(qmd_config)

        print("Created umbrella structure: qmd/collections/, kb/apps/, kb/systems/, kb/architecture/")

    elif args.type == "single":
        create_dirs(target, ["kb/raw", "qmd/collections"])

        qmd_config = """{
  "version": "1.0",
  "workspace": {
    "name": "%s_kb",
    "collections_dir": "./qmd/collections",
    "db_path": ".qmd/vector.db"
  },
  "models": {
    "embedding": "text-embedding-3-small"
  }
}""" % project_name
        with open(target / "qmd.json", "w", encoding="utf-8") as f:
            f.write(qmd_config)

        print("Created single project structure: kb/raw/, qmd.json")

    with open(target / "qmd/collections/wiki.yaml", "w", encoding="utf-8") as f:
        f.write(
            "name: %s-wiki\npaths:\n  - ../../kb/\nexclude:\n"
            "  - \"raw/**\"\n  - \"**/.DS_Store\"\n" % project_name
        )
    with open(target / "qmd/collections/raw.yaml", "w", encoding="utf-8") as f:
        f.write(
            "name: %s-raw\npaths:\n  - ../../kb/raw/\nexclude:\n"
            "  - \"**/.DS_Store\"\n" % project_name
        )

    append_gitignore_rules(target)

    print(f"Success! Agent skills kb-wiki-builder, qmd-operator, kb-capture, and kb-lookup installed to {target / '.agents/skills/'}")

if __name__ == "__main__":
    sys.exit(main() or 0)
