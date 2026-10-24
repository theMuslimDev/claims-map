"""Unit tests for the small pure functions and the failure paths of the scripts."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_map  # noqa: E402
import cm_common  # noqa: E402
import numcheck  # noqa: E402

TOY = ROOT / "examples" / "toy-paper"


class WeakAnchor(unittest.TestCase):
    def test_shared_word_is_not_weak(self):
        self.assertFalse(build_map.weak_anchor("The method reaches 95\\% accuracy.", "The classifier reaches 95.2\\% accuracy."))

    def test_stem_matching(self):
        self.assertFalse(build_map.weak_anchor("The network leaks less.", "The leakage is lower."))

    def test_acronym_inside_ac_macro_counts(self):
        self.assertFalse(build_map.weak_anchor("Classical \\ac{zf} has no constraint.", "The kinematic ZF does not control the gain."))

    def test_math_symbol_names_count(self):
        self.assertFalse(build_map.weak_anchor("up to $K_{\\max}=4$ eavesdroppers", "At most $K_{\\max}$ are active."))

    def test_unrelated_quote_is_weak(self):
        self.assertTrue(build_map.weak_anchor("No signs of catastrophic forgetting.", "Latency is 1.388 ms per frame."))

    def test_citation_commands_do_not_count(self):
        self.assertTrue(build_map.weak_anchor("Prior work \\cite{smith2020}.", "Another study \\cite{smith2020}."))


class NumberHelpers(unittest.TestCase):
    def test_decimals(self):
        self.assertEqual((numcheck.decimals("12"), numcheck.decimals("1.388")), (0, 3))

    def test_rounds_to(self):
        self.assertTrue(numcheck.rounds_to("1.388", "1.39"))
        self.assertTrue(numcheck.rounds_to("12.05", "12"))
        self.assertFalse(numcheck.rounds_to("1.41", "1.39"))

    def test_half_up_rounding(self):
        self.assertTrue(numcheck.rounds_to("0.125", "0.13"))


class DocLineMap(unittest.TestCase):
    def test_find_returns_line_across_line_breaks(self):
        tmp = Path(tempfile.mkdtemp())
        f = tmp / "a.tex"
        f.write_text("first line\nthe quick brown\nfox jumps\nlast\n")
        d = build_map.Doc(f)
        self.assertEqual(d.find("quick brown fox"), 2)
        self.assertIsNone(d.find("not in file"))
        self.assertIsNone(d.find(""))
        shutil.rmtree(tmp)


class ConfigErrors(unittest.TestCase):
    def test_missing_required_key_exits_with_message(self):
        tmp = Path(tempfile.mkdtemp())
        cfg = tmp / "c.md"
        cfg.write_text("```yaml\ntitle: x\n```\n")
        with self.assertRaises(SystemExit) as cm:
            cm_common.load_config(cfg)
        self.assertIn("missing required keys", str(cm.exception))
        shutil.rmtree(tmp)

    def test_no_yaml_block_exits(self):
        tmp = Path(tempfile.mkdtemp())
        cfg = tmp / "c.md"
        cfg.write_text("no block here\n")
        with self.assertRaises(SystemExit):
            cm_common.load_config(cfg)
        shutil.rmtree(tmp)

    def test_missing_pyyaml_exits_with_one_line(self):
        r = subprocess.run([sys.executable, "-c", "import sys; sys.modules['yaml'] = None; import cm_common"],
                           cwd=ROOT / "scripts", capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stderr.strip(), "PyYAML is required: pip install pyyaml")
        self.assertNotIn("Traceback", r.stderr)


class FailurePaths(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(TOY, self.tmp / "paper", ignore=shutil.ignore_patterns("out"))
        self.cfg = self.tmp / "paper" / "claims-map.config.md"
        self.out = self.tmp / "paper" / "out"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def script(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / name), *map(str, args)], capture_output=True, text=True)

    def test_snapshot_fails_clearly_on_missing_file(self):
        (self.tmp / "paper" / "sections" / "02_methods.tex").unlink()
        r = self.script("snapshot.py", self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("configured file not found", r.stderr)

    def test_build_fails_clearly_without_claims(self):
        self.script("snapshot.py", self.cfg)
        r = self.script("build_map.py", self.cfg)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("claims.json", r.stderr)

    def test_section_without_verdict_file_is_missing(self):
        self.script("snapshot.py", self.cfg)
        (self.out / "verdicts").mkdir()
        shutil.copy(TOY / "claims.json", self.out / "claims.json")
        shutil.copy(TOY / "verdicts" / "results.json", self.out / "verdicts" / "results.json")
        r = self.script("build_map.py", self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        md = (self.out / "claims_map.md").read_text()
        self.assertIn("**missing**", md)

    def test_claim_sentence_not_in_snapshot_is_flagged(self):
        self.script("snapshot.py", self.cfg)
        (self.out / "verdicts").mkdir()
        shutil.copy(TOY / "verdicts" / "results.json", self.out / "verdicts" / "results.json")
        shutil.copy(TOY / "verdicts" / "methods.json", self.out / "verdicts" / "methods.json")
        (self.out / "claims.json").write_text(
            '[{"id":"T01","sentence":"A sentence the paper never contains.","file":"sections/00_abstract.tex","location":"x","type":"scope"}]')
        self.script("build_map.py", self.cfg)
        self.assertIn("sentence not found in snapshot", (self.out / "claims_map.md").read_text())

    def test_invalid_verdict_word_is_not_accepted(self):
        self.script("snapshot.py", self.cfg)
        (self.out / "verdicts").mkdir()
        shutil.copy(TOY / "claims.json", self.out / "claims.json")
        shutil.copy(TOY / "verdicts" / "results.json", self.out / "verdicts" / "results.json")
        (self.out / "verdicts" / "methods.json").write_text(
            '{"section":"methods","verdicts":[{"claim":"T01","verdict":"correct","anchor":{"quote":"We train a classifier in three stages"}}],"unclaimed":[]}')
        self.script("build_map.py", self.cfg)
        self.assertIn("invalid-verdict", (self.out / "claims_map.md").read_text())


if __name__ == "__main__":
    unittest.main()
