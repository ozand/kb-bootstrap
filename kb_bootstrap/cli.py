import os
import shutil
import argparse
import sys
from pathlib import Path

from .graph_linter import validate
from .qmd_validator import validate_qmd_collections
from .repository_doctor import inspect_repository
from .completion_validator import validate_completion
from .repository_manifest import validate_manifest_file, write_manifest
from .agents_governance import update_agents_file

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
    parser.add_argument(
        "--with-project-lessons",
        action="store_true",
        help="Generate an opt-in project-local lessons store and routing contract",
    )
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
    doctor_parser = subparsers.add_parser(
        "doctor", help="Check repository identity before GitHub work"
    )
    doctor_parser.add_argument(
        "--repo",
        required=True,
        help="Expected GitHub repository in owner/name form",
    )
    completion_parser = subparsers.add_parser(
        "check-completion",
        help="Verify that a commit belongs to the target default branch or pull request",
    )
    completion_parser.add_argument(
        "--repo", required=True, help="Issue repository in owner/name form"
    )
    completion_parser.add_argument(
        "--commit", required=True, help="Completion commit ID"
    )
    completion_parser.add_argument(
        "--pr", type=int, help="Associated pull request number"
    )
    manifest_parser = subparsers.add_parser(
        "manifest", help="Generate or validate sanitized repository context"
    )
    manifest_parser.add_argument(
        "--repo", help="Repository in owner/name form when generating"
    )
    manifest_parser.add_argument(
        "--output",
        default="repository-context.json",
        help="Manifest output path (default: repository-context.json)",
    )
    manifest_parser.add_argument(
        "--check", action="store_true", help="Validate the existing output file"
    )
    agents_parser = subparsers.add_parser(
        "agents-governance", help="Create or update the managed AGENTS.md block"
    )
    agents_parser.add_argument(
        "--repo", required=True, help="Expected repository in owner/name form"
    )
    agents_parser.add_argument(
        "--file", default="AGENTS.md", help="AGENTS.md path (default: AGENTS.md)"
    )
    args = parser.parse_args()

    if args.command == "validate":
        graph_report, graph_valid = validate(args.dir)
        qmd_report, qmd_valid = validate_qmd_collections(args.project_root)
        print(graph_report)
        print()
        print(qmd_report)
        return 0 if graph_valid and qmd_valid else 1

    if args.command == "doctor":
        report, is_valid = inspect_repository(args.repo)
        print(report)
        return 0 if is_valid else 1

    if args.command == "check-completion":
        report, is_valid = validate_completion(args.repo, args.commit, args.pr)
        print(report)
        return 0 if is_valid else 1

    if args.command == "manifest":
        output = Path(args.output)
        if args.check:
            report, is_valid = validate_manifest_file(output)
        elif not args.repo:
            report, is_valid = "--repo is required when generating a manifest", False
        else:
            report, is_valid = write_manifest(args.repo, output)
        print(report)
        return 0 if is_valid else 1

    if args.command == "agents-governance":
        report, is_valid = update_agents_file(Path(args.file), args.repo)
        print(report)
        return 0 if is_valid else 1

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

    if args.with_project_lessons:
        lessons_src = pkg_dir / "templates" / "lessons"
        create_dirs(target, ["kb/lessons"])
        shutil.copy2(lessons_src / "SCHEMA.md", target / "kb/lessons/SCHEMA.md")
        shutil.copy2(lessons_src / "index.yaml", target / "kb/lessons/index.yaml")
        shutil.copy2(lessons_src / "lesson-stores.json", target / "lesson-stores.json")

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
    (target / "kb/raw/.gitkeep").touch(exist_ok=True)

    if args.with_project_lessons:
        print("Enabled project-local lessons: kb/lessons/, lesson-stores.json")

    print(f"Success! Agent skills kb-wiki-builder, qmd-operator, kb-capture, and kb-lookup installed to {target / '.agents/skills/'}")

if __name__ == "__main__":
    sys.exit(main() or 0)
