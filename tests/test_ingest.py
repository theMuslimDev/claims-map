"""ingest.py: PDF, DOCX, Markdown, text and error paths. The PDF tests need pdftotext or pypdf."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cm_common  # noqa: E402
import ingest  # noqa: E402

FIXTURE_PDF = ROOT / "tests" / "fixtures" / "toy-paper.pdf"
HAVE_PDF = bool(shutil.which("pdftotext") or importlib.util.find_spec("pypdf"))
MD = "# Abstract\nWe reach 95% accuracy.\n# Introduction\nPrior work exists.\n# Methods\nWe train it.\n# Results\nIt works.\n# References\n[1] A.\n"


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "ingest.py"), *map(str, args)], capture_output=True, text=True)


def sections(out):
    cfg = cm_common.load_config(out / "claims-map.config.md")
    return {s["id"]: s["role"] for s in cfg["sections"]}


class Ingest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @unittest.skipUnless(HAVE_PDF, "needs pdftotext or pypdf")
    def test_pdf_sections_and_roles(self):
        r = run(FIXTURE_PDF, "--out", self.tmp / "o")
        self.assertEqual(r.returncode, 0, r.stderr)
        roles = sections(self.tmp / "o")
        self.assertEqual(roles["abstract"], "front")
        self.assertEqual(roles["introduction"], "front")
        self.assertEqual(roles["methods"], "body")
        self.assertEqual(roles["results"], "body")
        self.assertEqual(roles["conclusion"], "front")
        self.assertEqual(roles["references"], "skip")

    @unittest.skipUnless(HAVE_PDF, "needs pdftotext or pypdf")
    def test_pdf_config_runs_snapshot(self):
        run(FIXTURE_PDF, "--out", self.tmp / "o")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "snapshot.py"), str(self.tmp / "o" / "claims-map.config.md")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        snap = Path(r.stdout.strip())
        results = next((snap / "resolved" / "ingested").glob("*_results.txt"))
        self.assertIn("accuracy", results.read_text())

    def test_markdown_headings(self):
        f = self.tmp / "p.md"
        f.write_text(MD)
        self.assertEqual(run(f, "--out", self.tmp / "o").returncode, 0)
        roles = sections(self.tmp / "o")
        self.assertEqual((roles["abstract"], roles["methods"], roles["references"]), ("front", "body", "skip"))

    def test_docx_heading_styles(self):
        body = "".join(
            f'<w:p><w:pPr><w:pStyle w:val="{"Heading1" if h else "Normal"}"/></w:pPr><w:r><w:t>{t}</w:t></w:r></w:p>'
            for h, t in [(1, "Abstract"), (0, "We reach 95% accuracy."), (1, "Introduction"), (0, "Prior work."),
                         (1, "Methods"), (0, "We train."), (1, "Results"), (0, "Good.")])
        xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               f"<w:body>{body}</w:body></w:document>")
        f = self.tmp / "p.docx"
        with zipfile.ZipFile(f, "w") as z:
            z.writestr("word/document.xml", xml)
        self.assertEqual(run(f, "--out", self.tmp / "o").returncode, 0)
        self.assertEqual(sections(self.tmp / "o")["results"], "body")

    def test_unsupported_type_fails_clearly(self):
        f = self.tmp / "p.xyz"
        f.write_text("x")
        r = run(f)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unsupported file type", r.stderr)

    def test_no_headings_fails_clearly(self):
        f = self.tmp / "p.txt"
        f.write_text("just one long paragraph without any headings at all\n")
        r = run(f, "--out", self.tmp / "o")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("headings were not recognised", r.stderr)

    def test_missing_file_fails_clearly(self):
        r = run(self.tmp / "nope.pdf")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a file", r.stderr)

    def test_small_caps_titles_are_tidied(self):
        self.assertEqual(ingest.tidy_title("I. I NTRODUCTION"), "Introduction")
        self.assertEqual(ingest.tidy_title("II. S YSTEM M ODEL"), "System Model")
        self.assertEqual(ingest.tidy_title("3 Experimental Setup"), "Experimental Setup")


if __name__ == "__main__":
    unittest.main()
