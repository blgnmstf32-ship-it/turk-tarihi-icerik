"""Verify compact output does not hide failures or modify protected data."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.context_output import notes_view, unittest_view


PASS = b"test_simple (test_module.TestCase.test_simple) ... ok\n"
END = b"\n----------------------------------------------------------------------\nRan 3 tests in 0.080s\n\nOK\n"
EVIDENCE = (
    "Kaynak: https://example.invalid/kaynak?ref=12\n"
    "Sağlık uyarısı: hassasiyet gelişirse kullanmayı durdurun.\n"
    "Ölçüm: −18,63 LUFS, 1080×1920 ve 67,60 sn.\n"
    "WARNING: Some text output uses non-ASCII.\n"
    "ERROR: First diagnostic line with byte \udcfe remains.\n"
    "  Second diagnostic line remains.\n"
).encode("utf-8", "surrogateescape")


class ContextOutputTests(unittest.TestCase):
    def test_only_redundant_pass_records_are_grouped(self):
        numeric = b"test_limit_40 (test_module.TestCase.test_limit_40) ... ok\n"
        formatted = unittest_view(PASS * 2 + EVIDENCE + numeric + END, 0)
        self.assertIn(b"[2 passing unittest records grouped.", formatted)
        self.assertIn(EVIDENCE + numeric + END, formatted)
        self.assertNotIn(PASS, formatted)

    def test_nonzero_exit_keeps_full_diagnostics_and_passes(self):
        raw = PASS + EVIDENCE + b"FAILED (errors=1)\n"
        self.assertEqual(unittest_view(raw, 1), raw)
        self.assertEqual(unittest_view(PASS + END, 2), PASS + END)

    def test_incomplete_or_modified_footer_keeps_full_log(self):
        self.assertEqual(unittest_view(PASS * 4 + EVIDENCE, 0), PASS * 4 + EVIDENCE)
        skipped = PASS + END.replace(b"OK\n", b"OK (skipped=2)\n")
        self.assertEqual(unittest_view(skipped, 0), skipped)

    def test_arbitrary_similar_lines_are_retained(self):
        raw = (
            b"test_simple (test_module.TestCase.test_other) ... ok\n"
            b"test_simple (test_module.TestCase.test_simple) ... ok with notes\n"
        )
        self.assertEqual(unittest_view(raw + END, 0), raw + END)

    def test_exact_duplicate_keeps_source_paths_and_all_unique_bytes(self):
        with TemporaryDirectory() as folder:
            paths = [Path(folder) / filename for filename in ("one.md", "again.md", "updated.md")]
            paths[0].write_bytes(EVIDENCE)
            paths[1].write_bytes(EVIDENCE)
            paths[2].write_bytes(EVIDENCE.replace(b"67,60", b"71,80"))
            compact = notes_view(paths)
            self.assertIn(b"Identical to section 1.", compact)
            for path in paths:
                self.assertIn(path.as_posix().encode(), compact)
            self.assertEqual(compact.count(EVIDENCE), 1)
            self.assertIn(paths[2].read_bytes(), compact)
            self.assertEqual(notes_view(paths, deduplicate=False).count(EVIDENCE), 2)

    def test_original_log_file_is_read_only(self):
        with TemporaryDirectory() as folder:
            log = Path(folder) / "quality.log"
            raw = PASS + END
            log.write_bytes(raw)
            self.assertNotEqual(unittest_view(log.read_bytes(), 0), raw)
            self.assertEqual(log.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
