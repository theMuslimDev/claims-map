"""The README example must match the toy paper's golden output."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = ROOT / "examples" / "toy-paper" / "expected"
FIX = "Copy the text from examples/toy-paper/expected/{} into the README example."


def between(text, name):
    m = re.search(rf"<!-- example-{name}:start -->\n(.*?)\n<!-- example-{name}:end -->", text, re.S)
    if not m:
        raise AssertionError(f"README.md has no example-{name} start/end markers")
    return m.group(1).strip("\n")


class ReadmeExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_briefing_matches_golden(self):
        block = between(self.readme, "briefing")
        m = re.fullmatch(r"```text\n(.*)\n```", block, re.S)
        self.assertIsNotNone(m, "the briefing example must be one ```text fenced block")
        golden = (EXPECTED / "briefing.md").read_text(encoding="utf-8").strip()
        self.assertEqual(m.group(1), golden, FIX.format("briefing.md"))

    def test_ledger_rows_come_from_golden(self):
        rows = between(self.readme, "ledger").strip().splitlines()
        self.assertGreaterEqual(len(rows), 3, "expected a header, a divider and at least one row")
        golden = (EXPECTED / "claim_ledger.md").read_text(encoding="utf-8").splitlines()
        self.assertTrue(rows[0].startswith("| id | status |"), "first line must be the ledger table header")
        for row in rows:
            self.assertIn(row, golden, FIX.format("claim_ledger.md") + f"\nNot found: {row}")


if __name__ == "__main__":
    unittest.main()
