"""init_config.py: draft config from a paper folder, then the config must load and snapshot."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cm_common  # noqa: E402

TOY = ROOT / "examples" / "toy-paper"


def run(script, *args):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)], capture_output=True, text=True)
    return r


class InitConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.paper = self.tmp / "paper"
        shutil.copytree(TOY, self.paper, ignore=shutil.ignore_patterns("out", "claims.json", "verdicts", "claims-map.config.md"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def roles(self):
        cfg = cm_common.load_config(self.paper / "claims_map" / "claims-map.config.md")
        return {s["file"]: s["role"] for s in cfg["sections"]}, cfg

    def test_sorted_names_without_main_file(self):
        r = run("init_config.py", self.paper)
        self.assertEqual(r.returncode, 0, r.stderr)
        roles, _ = self.roles()
        self.assertEqual(roles["sections/00_abstract.tex"], "front")
        self.assertEqual(roles["sections/01_intro.tex"], "front")
        self.assertEqual(roles["sections/03_results.tex"], "body")

    def test_main_file_sets_order_and_skips_commented_inputs(self):
        (self.paper / "main.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\n\\input{sections/03_results}\n"
            "\\input{sections/00_abstract}\n% \\input{sections/02_methods}\n\\input{sections/acronyms}\n\\end{document}\n")
        (self.paper / "sections" / "acronyms.tex").write_text("x\n")
        run("init_config.py", self.paper)
        roles, cfg = self.roles()
        self.assertEqual([s["file"] for s in cfg["sections"]],
                         ["sections/03_results.tex", "sections/00_abstract.tex", "sections/acronyms.tex"])
        self.assertEqual(roles["sections/acronyms.tex"], "skip")

    def test_generated_config_runs_snapshot(self):
        run("init_config.py", self.paper)
        r = run("snapshot.py", self.paper / "claims_map" / "claims-map.config.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.paper / "claims_map").exists())

    def test_missing_folder_fails_clearly(self):
        r = run("init_config.py", self.tmp / "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a folder", r.stderr)


if __name__ == "__main__":
    unittest.main()
