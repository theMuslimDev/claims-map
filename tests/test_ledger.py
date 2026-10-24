"""Claim ledger and briefing: status rule, precedence, uncounted cells, and the toy paper's expected output."""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import ledger  # noqa: E402

TOY = ROOT / "examples" / "toy-paper"


def cell(verdict, basis=None, **kw):
    c = {"verdict": verdict, "file": "sections/s.tex", "line": 1, "quote": "a quote", "weak": False, "basis": basis}
    c.update(kw)
    return c


def status(cells, ctype="numeric"):
    claim = {"id": "C1", "type": ctype}
    return ledger.classify(claim, [(f"s{i}", c) for i, c in enumerate(cells)])[0]


ABSENT = {"verdict": "absent"}
MISSING = {"verdict": "missing"}
INVALID = {"verdict": "invalid-anchor", "claimed": "anchored", "quote": "x"}


class StatusRule(unittest.TestCase):
    def test_established_needs_a_shown_anchor(self):
        self.assertEqual(status([cell("anchored", "shown"), ABSENT]), "Established")

    def test_anchored_without_basis_counts_as_shown(self):
        self.assertEqual(status([cell("anchored")]), "Established")

    def test_assumed_only_when_every_anchor_is_assumed(self):
        self.assertEqual(status([cell("anchored", "assumed"), ABSENT]), "Assumed")
        self.assertEqual(status([cell("anchored", "assumed"), cell("anchored", "shown")]), "Established")

    def test_narrower_is_partial_only(self):
        self.assertEqual(status([cell("partial"), ABSENT]), "Narrower")

    def test_cited_is_external_or_citation_claim_without_anchor(self):
        self.assertEqual(status([cell("external"), ABSENT]), "Cited")
        self.assertEqual(status([ABSENT, ABSENT], ctype="citation"), "Cited")

    def test_unsupported_is_absent_everywhere(self):
        self.assertEqual(status([ABSENT, ABSENT]), "Unsupported")

    def test_citation_claim_with_a_body_anchor_follows_the_normal_rule(self):
        self.assertEqual(status([cell("anchored", "shown")], ctype="citation"), "Established")
        self.assertEqual(status([cell("partial")], ctype="citation"), "Narrower")


class Precedence(unittest.TestCase):
    def test_differs_beats_everything(self):
        self.assertEqual(status([cell("differs"), cell("anchored", "shown")]), "Conflicting")

    def test_established_beats_assumed_narrower_and_cited(self):
        self.assertEqual(status([cell("anchored", "shown"), cell("anchored", "assumed"), cell("partial"),
                                 cell("external")]), "Established")

    def test_assumed_beats_narrower_and_cited(self):
        self.assertEqual(status([cell("anchored", "assumed"), cell("partial"), cell("external")]), "Assumed")

    def test_narrower_beats_cited(self):
        self.assertEqual(status([cell("partial"), cell("external")]), "Narrower")

    def test_cited_beats_unsupported(self):
        self.assertEqual(status([cell("external"), ABSENT]), "Cited")


class UncountedCells(unittest.TestCase):
    def test_invalid_anchor_is_not_support(self):
        self.assertEqual(status([INVALID, ABSENT]), "Unsupported")
        self.assertEqual(status([INVALID, cell("partial")]), "Narrower")

    def test_missing_is_not_support(self):
        self.assertEqual(status([MISSING, ABSENT]), "Unsupported")
        self.assertEqual(status([MISSING, cell("anchored", "assumed")]), "Assumed")

    def test_invalid_verdict_is_not_support(self):
        self.assertEqual(status([{"verdict": "invalid-verdict", "note": "maybe"}, ABSENT]), "Unsupported")

    def test_uncounted_cells_are_named_in_the_evidence(self):
        claim = {"id": "C1", "type": "numeric", "sentence": "s", "location": "l", "file": "f", "sentence_ok": True}
        body = [{"id": "m"}, {"id": "r"}]
        cells = {("C1", "m"): INVALID, ("C1", "r"): MISSING}
        (e,) = ledger.build_entries([claim], body, cells)
        self.assertEqual(e["status"], "Unsupported")
        self.assertIn("not counted: invalid-anchor in m, missing in r", ledger.evidence(e, ["m", "r"]))

    def test_anchored_without_basis_says_so(self):
        claim = {"id": "C1", "type": "numeric", "sentence": "s", "location": "l", "file": "f", "sentence_ok": True}
        (e,) = ledger.build_entries([claim], [{"id": "m"}], {("C1", "m"): cell("anchored")})
        self.assertIn("basis: not given", ledger.evidence(e, ["m"]))


def build_toy(tmp, mutate=None):
    paper = Path(tmp) / "paper"
    shutil.copytree(TOY, paper, ignore=shutil.ignore_patterns("out", "expected"))
    out = paper / "out"
    out.mkdir()
    shutil.copy(TOY / "claims.json", out / "claims.json")
    shutil.copytree(TOY / "verdicts", out / "verdicts")
    if mutate:
        mutate(out)
    cfg = paper / "claims-map.config.md"
    for script in ("snapshot.py", "numcheck.py", "build_map.py"):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / script), str(cfg)], capture_output=True,
                           text=True, check=False)
        assert r.returncode == 0, r.stderr
    return out


def masked(text):
    return re.sub(r"snapshot_\d{8}T\d{6}Z", "snapshot_<UTC>", text)


class ToyLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.out = build_toy(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_ledger_matches_expected(self):
        got = masked((self.out / "claim_ledger.md").read_text())
        self.assertEqual(got, (TOY / "expected" / "claim_ledger.md").read_text())

    def test_briefing_matches_expected(self):
        got = (self.out / "briefing.md").read_text()
        self.assertEqual(got, (TOY / "expected" / "briefing.md").read_text())

    def test_ledger_is_worst_first(self):
        text = (self.out / "claim_ledger.md").read_text()
        rows = re.findall(r"^\| (T\d\d) \| (\w+) \|", text, re.M)
        self.assertEqual([s for _, s in rows],
                         ["Unsupported", "Conflicting", "Narrower", "Cited", "Established", "Established"])

    def test_invalid_anchor_cell_does_not_support_its_claim(self):
        # T01's methods cell has a quote that is not in the file; results alone makes it Established
        text = (self.out / "claim_ledger.md").read_text()
        self.assertIn("not counted; the agent said partial", text)

    def test_generated_markdown_follows_lint_basics(self):
        for name in ("claim_ledger.md", "briefing.md"):
            lines = (self.out / name).read_text().split("\n")
            self.assertEqual(lines[-1], "", name)
            self.assertNotEqual(lines[-2], "", name)
            self.assertEqual(sum(1 for ln in lines if ln.startswith("# ")), 1, name)
            for i, ln in enumerate(lines):
                self.assertEqual(ln, ln.rstrip(), f"{name}:{i + 1} trailing space")
                if ln.startswith("#"):
                    self.assertEqual(lines[i + 1], "", f"{name}:{i + 1}")
                    self.assertTrue(i == 0 or lines[i - 1] == "", f"{name}:{i + 1}")
                if not ln.startswith("|"):
                    self.assertLessEqual(len(ln), 80, f"{name}:{i + 1}")

    def test_no_advice_words_in_briefing(self):
        text = (self.out / "briefing.md").read_text().lower()
        for word in ("should", "recommend", "consider", "rewrite", "fix"):
            self.assertNotIn(word, text)


class MissingAndInvalidEndToEnd(unittest.TestCase):
    def test_missing_verdict_file_and_bad_quote_do_not_count(self):
        def mutate(out):
            (out / "verdicts" / "results.json").unlink()

        tmp = tempfile.mkdtemp()
        try:
            out = build_toy(tmp, mutate)
            text = (out / "claim_ledger.md").read_text()
            rows = dict(re.findall(r"^\| (T\d\d) \| (\w+) \|", text, re.M))
            # without the results agent, only methods speaks: T05 anchored there, the rest has no support
            self.assertEqual(rows["T05"], "Established")
            self.assertEqual(rows["T01"], "Unsupported")
            self.assertEqual(rows["T04"], "Cited")
            self.assertIn("no answer from the agent; not counted", text)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
