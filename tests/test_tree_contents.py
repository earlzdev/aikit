"""The acceptance tripwire detects content changes even with unchanged status."""
import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

loader = importlib.machinery.SourceFileLoader("aikit_tree_verdict", str(Path(__file__).resolve().parents[1] / "bin/verdict"))
spec = importlib.util.spec_from_loader(loader.name, loader)
v = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v
loader.exec_module(v)


class TestContentTripwire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def test_already_modified_file_content_changes_digest(self):
        path = self.root / "dirty.txt"
        path.write_text("base\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=self.root, check=True)
        path.write_text("first modification\n")
        before, names = v.tree_state(self.root)
        path.write_text("second modification\n")
        after, after_names = v.tree_state(self.root)
        self.assertEqual(names, after_names)
        self.assertNotEqual(before, after)

    def test_nested_untracked_file_content_and_quoted_paths(self):
        folder = self.root / "new folder"
        folder.mkdir()
        path = folder / 'name " with newline\n.txt'
        path.write_text("first")
        before, names = v.tree_state(self.root)
        self.assertIn(str(path.relative_to(self.root)), names)
        path.write_text("second")
        self.assertNotEqual(before, v.tree_digest(self.root))

    def test_ignore_still_excludes_content(self):
        path = self.root / "generated.txt"
        path.write_text("first")
        before = v.tree_digest(self.root, ignore=("generated.txt",))
        path.write_text("second")
        self.assertEqual(before, v.tree_digest(self.root, ignore=("generated.txt",)))

    def test_staged_content_changes_with_same_worktree(self):
        path = self.root / "staged.txt"
        path.write_text("index one")
        subprocess.run(["git", "add", "staged.txt"], cwd=self.root, check=True)
        path.write_text("working content")
        before = v.tree_digest(self.root)
        path.write_text("index two")
        subprocess.run(["git", "add", "staged.txt"], cwd=self.root, check=True)
        path.write_text("working content")
        self.assertNotEqual(before, v.tree_digest(self.root))


if __name__ == "__main__":
    unittest.main()
