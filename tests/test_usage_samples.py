"""The sample output in USAGE.md must match what the scripts print on the toy paper."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import usage_samples  # noqa: E402

ROOT = usage_samples.ROOT
REGEN = "Regenerate with `python tests/usage_samples.py`, review the diff, then copy the text of {} into USAGE.md."


def block(text, name):
    """The sample between its markers: a ```text block, except the matrix, which is a table."""
    inner = r"(.*?)\n" if name == "matrix" else r"```text\n(.*?)\n```\n"
    pattern = rf"<!-- usage-{name}:start -->\n{inner}<!-- usage-{name}:end -->"
    m = re.search(pattern, text, re.S)
    if not m:
        raise AssertionError(f"USAGE.md has no usage-{name} start/end markers around the sample")
    return m.group(1).strip("\n") + "\n"


class UsageSamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = usage_samples.generate()
        cls.usage = (ROOT / "USAGE.md").read_text(encoding="utf-8")

    def test_golden_files_match_the_scripts(self):
        for name in usage_samples.NAMES:
            golden = (usage_samples.GOLDEN / f"{name}.txt").read_text(encoding="utf-8")
            self.assertEqual(self.generated[name], golden,
                             f"examples/toy-paper/expected/usage/{name}.txt is stale. " + REGEN.format(name + ".txt"))

    def test_usage_md_matches_golden_files(self):
        for name in usage_samples.NAMES:
            golden = (usage_samples.GOLDEN / f"{name}.txt").read_text(encoding="utf-8")
            self.assertEqual(block(self.usage, name), golden,
                             f"USAGE.md sample '{name}' differs from the golden file. "
                             + REGEN.format(f"examples/toy-paper/expected/usage/{name}.txt"))


if __name__ == "__main__":
    unittest.main()
