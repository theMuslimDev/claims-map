"""Regression tests from user feedback: numcheck with `sections: []`, dirty-tree warnings, --ref, unresolved macros."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOY = ROOT / "examples" / "toy-paper"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]


def run(script, *args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)], capture_output=True, text=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.paper = self.tmp / "paper"
        shutil.copytree(TOY, self.paper, ignore=shutil.ignore_patterns("out"))
        self.cfg = self.paper / "claims-map.config.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit_all(self):
        subprocess.run(["git", "init", "-q"], cwd=self.paper, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.paper, check=True)
        subprocess.run([*GIT, "commit", "-q", "-m", "init"], cwd=self.paper, check=True)

    def manifest(self, stdout):
        return json.loads((Path(stdout.strip()) / "MANIFEST.json").read_text())


class NumcheckScope(Base):
    def test_empty_sections_list_means_all_sections(self):
        self.cfg.write_text(self.cfg.read_text().replace("terminology:", "numcheck:\n  sections: []\nterminology:"))
        run("snapshot.py", self.cfg)
        r = run("numcheck.py", self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("scanned 0 numbers", r.stdout)

    def test_zero_numbers_prints_a_hint(self):
        for f in (self.paper / "sections").glob("*.tex"):
            f.write_text("No digits here at all.\n")
        run("snapshot.py", self.cfg)
        r = run("numcheck.py", self.cfg)
        self.assertIn("scanned 0 numbers", r.stdout)
        self.assertIn("no numbers found", r.stderr)


class DirtyTree(Base):
    def test_working_tree_snapshot_warns_and_marks_modified_files(self):
        self.commit_all()
        (self.paper / "sections" / "03_results.tex").write_text("Edited after the commit. Accuracy is 99\\%.\n")
        r = run("snapshot.py", self.cfg)
        self.assertIn("differ from the commit", r.stderr)
        self.assertIn("03_results.tex", r.stderr)
        man = self.manifest(r.stdout)
        self.assertTrue(man["dirty_tree"])
        self.assertIsNone(man["ref"])

    def test_clean_tree_has_no_warning(self):
        self.commit_all()
        subprocess.run(["git", "rm", "-rq", "--cached", "out"], cwd=self.paper, capture_output=True)
        r = run("snapshot.py", self.cfg)
        self.assertNotIn("differ from the commit", r.stderr)

    def test_ref_snapshots_committed_content_and_ignores_edits(self):
        self.commit_all()
        edited = self.paper / "sections" / "03_results.tex"
        edited.write_text("Edited after the commit.\n")
        r = run("snapshot.py", self.cfg, "--ref", "HEAD")
        self.assertEqual(r.returncode, 0, r.stderr)
        snap = Path(r.stdout.strip())
        self.assertIn("95.2", (snap / "raw" / "sections" / "03_results.tex").read_text())
        self.assertNotIn("Edited", (snap / "resolved" / "sections" / "03_results.tex").read_text())
        self.assertEqual(self.manifest(r.stdout)["ref"], "HEAD")
        self.assertEqual(edited.read_text(), "Edited after the commit.\n")  # working tree untouched

    def test_ref_with_unknown_file_fails_clearly(self):
        self.commit_all()
        r = run("snapshot.py", self.cfg, "--ref", "no-such-ref")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is not in no-such-ref", r.stderr)

    def test_map_header_names_the_modified_files(self):
        self.commit_all()
        (self.paper / "sections" / "03_results.tex").write_text(
            (self.paper / "sections" / "03_results.tex").read_text() + "Extra line.\n")
        snap = run("snapshot.py", self.cfg).stdout.strip()
        out = Path(snap).parent
        shutil.copy(TOY / "claims.json", out / "claims.json")
        shutil.copytree(TOY / "verdicts", out / "verdicts")
        self.assertEqual(run("build_map.py", self.cfg).returncode, 0)
        self.assertIn("snapshot taken from the working tree", (out / "claims_map.md").read_text())


class UnresolvedMacros(Base):
    def test_missing_key_warns_but_comment_mentions_do_not(self):
        defs = self.paper / "sections" / "nums.tex"
        defs.write_text("\\expandafter\\def\\csname rn@acc\\endcsname{95.2}\n")
        (self.paper / "sections" / "03_results.tex").write_text(
            "% the macro \\rn{in_a_comment} is mentioned here only\nAccuracy is \\rn{acc} and \\rn{missing_key}.\n")
        self.cfg.write_text(self.cfg.read_text().replace(
            "terminology:", "number_macros:\n  macro: rn\n  definitions_file: sections/nums.tex\n"
            "  definition_regex: '\\\\csname rn@(.*?)\\\\endcsname\\{(.*?)\\}'\nterminology:"))
        r = run("snapshot.py", self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("missing_key", r.stderr)
        self.assertNotIn("in_a_comment", r.stderr)
        resolved = (Path(r.stdout.strip()) / "resolved" / "sections" / "03_results.tex").read_text()
        self.assertIn("Accuracy is 95.2 and", resolved)


if __name__ == "__main__":
    unittest.main()
