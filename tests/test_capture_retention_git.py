import subprocess
import tempfile
import unittest
from pathlib import Path


class CaptureRetentionGitTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout.decode().strip()

    def stage_selected_or_abort(self, root, selected):
        staged = set(self.git(root, "diff", "--cached", "--name-only").splitlines())
        if staged and staged != set(selected):
            raise RuntimeError("pre-staged paths differ from the explicit selection")
        self.git(root, "add", "--", *selected)
        actual = set(self.git(root, "diff", "--cached", "--name-only").splitlines())
        if actual != set(selected):
            raise RuntimeError("staged paths differ from the explicit selection")

    def test_commit_contains_selected_capture_and_provenance_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Synthetic Test")
            self.git(root, "config", "user.email", "synthetic@example.invalid")
            raw = root / "kb/research/study/raw/001-page.md"
            brief = root / "kb/research/study/brief.md"
            prior = root / "kb/research/study/raw/000-prior.md"
            unrelated = root / "notes.md"
            for p in (raw, brief, prior, unrelated):
                p.parent.mkdir(parents=True, exist_ok=True)
            raw_bytes = b"---\ntype: RawCapture\n---\nSynthetic captured page.\n"
            brief_bytes = b"---\ntype: Brief\n---\nSynthetic provenance.\n"
            prior_bytes = b"---\ntype: RawCapture\n---\nPrior capture.\n"
            raw.write_bytes(raw_bytes)
            brief.write_bytes(brief_bytes)
            prior.write_bytes(prior_bytes)
            unrelated.write_bytes(b"original\n")
            paths = [p.relative_to(root).as_posix() for p in (raw, brief, prior)]
            self.git(root, "add", "--", paths[2], unrelated.name)
            self.git(root, "commit", "-qm", "seed")
            prior_blob = self.git(root, "rev-parse", f"HEAD:{paths[2]}")

            # Foreign staged content makes the ordinary workflow abort without touching it.
            extra = root / "unrelated-new.md"
            extra.write_bytes(b"not selected\n")
            self.git(root, "add", "--", extra.name)
            self.assertEqual(self.git(root, "diff", "--cached", "--name-only"), extra.name)
            head_before = self.git(root, "rev-parse", "HEAD")
            staged_before = self.git(root, "ls-files", "--stage").splitlines()
            bytes_before = (raw.read_bytes(), brief.read_bytes(), prior.read_bytes(), unrelated.read_bytes(), extra.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "pre-staged paths differ"):
                self.stage_selected_or_abort(root, [paths[0], paths[1]])
            self.assertEqual(self.git(root, "rev-parse", "HEAD"), head_before)
            self.assertEqual(self.git(root, "ls-files", "--stage").splitlines(), staged_before)
            self.assertEqual((raw.read_bytes(), brief.read_bytes(), prior.read_bytes(), unrelated.read_bytes(), extra.read_bytes()), bytes_before)

    def test_selected_capture_commit_preserves_prior_and_excludes_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "Synthetic Test")
            self.git(root, "config", "user.email", "synthetic@example.invalid")
            raw = root / "kb/research/study/raw/001-page.md"
            brief = root / "kb/research/study/brief.md"
            prior = root / "kb/research/study/raw/000-prior.md"
            unrelated = root / "notes.md"
            for p in (raw, brief, prior, unrelated):
                p.parent.mkdir(parents=True, exist_ok=True)
            raw_bytes = b"---\ntype: RawCapture\n---\nSynthetic captured page.\n"
            brief_bytes = b"---\ntype: Brief\n---\nSynthetic provenance.\n"
            prior_bytes = b"---\ntype: RawCapture\n---\nPrior capture.\n"
            unrelated_before = b"original\\n"
            raw.write_bytes(raw_bytes)
            brief.write_bytes(brief_bytes)
            prior.write_bytes(prior_bytes)
            unrelated.write_bytes(unrelated_before)
            paths = [p.relative_to(root).as_posix() for p in (raw, brief, prior)]
            self.git(root, "add", "--", paths[2], unrelated.name)
            self.git(root, "commit", "-qm", "seed")
            prior_blob = self.git(root, "rev-parse", f"HEAD:{paths[2]}")
            self.assertEqual(prior.read_bytes(), prior_bytes)

            unrelated_after = b"working-tree edit, not selected\n"
            unrelated.write_bytes(unrelated_after)
            selected = [paths[0], paths[1]]
            self.stage_selected_or_abort(root, selected)
            staged = self.git(root, "diff", "--cached", "--name-only").splitlines()
            self.assertEqual(staged, sorted(selected))
            staged_blobs = {rel: self.git(root, "rev-parse", f":{rel}") for rel in selected}
            self.assertEqual(set(staged_blobs), set(selected))
            self.assertEqual(staged_blobs[paths[0]], self.git(root, "hash-object", str(raw)))
            self.assertEqual(staged_blobs[paths[1]], self.git(root, "hash-object", str(brief)))
            for rel, content in ((paths[0], raw_bytes), (paths[1], brief_bytes)):
                blob = self.git(root, "rev-parse", f":{rel}")
                self.assertEqual(subprocess.run(["git", "cat-file", "blob", blob], cwd=root, check=True, capture_output=True).stdout, content)
            self.git(root, "commit", "-qm", "retain selected capture")
            committed = self.git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
            self.assertEqual(committed, sorted(selected))
            for rel, content in ((paths[0], raw_bytes), (paths[1], brief_bytes)):
                self.assertEqual(subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=root, check=True, capture_output=True).stdout, content)
            self.assertEqual(self.git(root, "rev-parse", f"HEAD:{paths[2]}"), prior_blob)
            self.assertEqual(prior.read_bytes(), prior_bytes)
            self.assertEqual(unrelated.read_bytes(), unrelated_after)
            self.assertEqual(self.git(root, "status", "--short").splitlines(), ["M notes.md"])


if __name__ == "__main__":
    unittest.main()
