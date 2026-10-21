"""End-to-end test on the toy paper: snapshot, number check, build, render. No agents involved;
claims and verdicts are fixed files, so the checks below test the scripts, not any model."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TOY = ROOT / "examples" / "toy-paper"


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, f"{script} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout


class ToyPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(TOY, cls.tmp / "paper", ignore=shutil.ignore_patterns("out"))
        cls.cfg = cls.tmp / "paper" / "claims-map.config.md"
        out = cls.tmp / "paper" / "out"
        out.mkdir()
        shutil.copy(TOY / "claims.json", out / "claims.json")
        shutil.copytree(TOY / "verdicts", out / "verdicts")
        cls.snap = Path(run("snapshot.py", cls.cfg).strip())
        run("numcheck.py", cls.cfg)
        run("build_map.py", cls.cfg)
        run("render_html.py", out / "claims_map.md")
        cls.md = (out / "claims_map.md").read_text()
        cls.out = out

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_snapshot_records_hashes_and_resolves_files(self):
        man = json.loads((self.snap / "MANIFEST.json").read_text())
        self.assertEqual(len(man["files"]), 4)
        self.assertTrue(all(len(f["sha256"]) == 64 for f in man["files"]))
        self.assertTrue((self.snap / "resolved" / "sections" / "03_results.tex").exists())

    def test_invalid_anchor_is_rejected(self):
        self.assertIn("invalid-anchor", self.md)

    def test_absent_everywhere_and_citation_lists_are_separate(self):
        head = self.md.split("## Claims absent from every body section")[1].split("## Citation claims")[0]
        self.assertIn("T03", head)
        self.assertNotIn("T04", head)
        cites = self.md.split("## Citation claims with no body anchor")[1].split("## Matrix")[0]
        self.assertIn("T04", cites)

    def test_weak_anchor_flagged(self):
        self.assertIn("T05", self.md)
        self.assertIn("partial (weak anchor)", self.md)
        self.assertNotIn("anchored (weak anchor)", self.md)

    def test_unclaimed_statement_listed(self):
        self.assertIn("twice as fast as the older design", self.md)

    def test_number_check_reports_rounding(self):
        nc = json.loads((self.out / "numcheck.json").read_text())
        pairs = {(f["a"]["number"], f["b"]["number"]): f["class"] for f in nc["findings"]}
        self.assertEqual(pairs.get(("1.39", "1.388")) or pairs.get(("1.388", "1.39")), "rounding")
        self.assertEqual(pairs.get(("95", "95.2")) or pairs.get(("95.2", "95")), "rounding")

    def test_terminology_lint_hit(self):
        self.assertIn("no-Phase", self.md)

    def test_html_rendered(self):
        html = (self.out / "claims_map.html").read_text()
        self.assertIn("<table>", html)
        self.assertIn("Toy paper", html)


if __name__ == "__main__":
    unittest.main()
