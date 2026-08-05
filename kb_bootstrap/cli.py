import os
import shutil
import argparse
import sys
from pathlib import Path

def create_dirs(base_path: Path, dirs: list):
    for d in dirs:
        (base_path / d).mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description="Bootstrap Knowledge Base architecture (OKF + QMD)")
    parser.add_argument("--target", default=".", help="Target directory for initialization (default: current directory)")
    parser.add_argument("--type", choices=["single", "umbrella"], default="single", help="Project architecture type")
    args = parser.parse_args()

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

    if args.type == "umbrella":
        create_dirs(target, ["qmd/collections", "kb/apps", "kb/systems", "kb/architecture"])
        
        qmd_config = """{
  "version": "1.0",
  "workspace": {
    "name": "umbrella_kb",
    "collections_dir": "./collections",
    "db_path": ".qmd/vector.db"
  },
  "models": {
    "embedding": "text-embedding-3-small"
  }
}"""
        with open(target / "qmd/qmd.json", "w", encoding="utf-8") as f:
            f.write(qmd_config)

        print("Created umbrella structure: qmd/collections/, kb/apps/, kb/systems/, kb/architecture/")
        
    elif args.type == "single":
        create_dirs(target, ["kb/raw", "qmd/collections"])
        
        qmd_config = """{
  "version": "1.0",
  "workspace": {
    "name": "project_kb",
    "collections_dir": "./collections",
    "db_path": ".qmd/vector.db"
  },
  "models": {
    "embedding": "text-embedding-3-small"
  }
}"""
        with open(target / "qmd.json", "w", encoding="utf-8") as f:
            f.write(qmd_config)
            
        with open(target / "qmd/collections/default.yaml", "w", encoding="utf-8") as f:
            f.write(f"name: default\npaths:\n  - ../../kb/\nexclude:\n  - \"**/.DS_Store\"\n")

        print("Created single project structure: kb/raw/, qmd.json")

    print(f"Success! Agent skills kb-wiki-builder, qmd-operator, kb-capture, and kb-lookup installed to {target / '.agents/skills/'}")

if __name__ == "__main__":
    main()
