"""Run: python -m unittest -v test_main_2."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from zipfile import ZipFile

from main_2 import Application, ConversionError, convert_text, read_source


def write_docx_fixture(path: Path) -> None:
    """A real OOXML document: runs, table, header, and automatic numbering."""
    parts = {
        "[Content_Types].xml": '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
          <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
          <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
        </Types>''',
        "_rels/.rels": '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
        </Relationships>''',
        "word/_rels/document.xml.rels": '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
          <Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
        </Relationships>''',
        "word/numbering.xml": '''<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:abstractNum w:abstractNumId="0">
            <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl>
            <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2)"/></w:lvl>
          </w:abstractNum>
          <w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
        </w:numbering>''',
        "word/header1.xml": '''<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:p><w:r><w:t>Ten nagłówek nie jest pytaniem.</w:t></w:r></w:p>
        </w:hdr>''',
        "word/document.xml": '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>
          <w:p><w:r><w:t>1. Czy x &lt; y?</w:t></w:r></w:p>
          <w:p><w:r><w:t xml:space="preserve">A) </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>Tak &amp; już</w:t></w:r></w:p>
          <w:p><w:r><w:t>B) Nie</w:t></w:r></w:p>
          <w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="5000"/></w:tblGrid>
            <w:tr><w:tc><w:p><w:r><w:t>Pytanie 2:</w:t></w:r></w:p><w:p><w:r><w:t>Ile to 2 + 2?</w:t></w:r></w:p></w:tc></w:tr>
            <w:tr><w:tc><w:p><w:r><w:t>A. 3</w:t></w:r></w:p></w:tc></w:tr>
            <w:tr><w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>B. 4</w:t></w:r></w:p></w:tc></w:tr>
          </w:tbl>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Automatyczna numeracja?</w:t></w:r></w:p>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>Tak</w:t></w:r></w:p>
          <w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Nie</w:t></w:r></w:p>
          <w:sectPr><w:headerReference w:type="default" r:id="rIdHeader"/></w:sectPr>
        </w:body></w:document>''',
    }
    with ZipFile(path, "w") as archive:
        for name, contents in parts.items():
            archive.writestr(name, contents.encode("utf-8"))


class ConversionTests(unittest.TestCase):
    def test_numbered_questions_and_canonical_output(self):
        text = """13.13.d – 2 pytania
Pytanie 1:
Jaka jest
stolica Polski?
a. Warszawa
b. Kraków
ANSWER:a)
2) Ile to 2 + 2?
A) 3
B) 4
ODPOWIEDŹ: B
"""
        self.assertEqual(convert_text(text),
                         "Jaka jest stolica Polski?\nA) Warszawa\nB) Kraków\nANSWER: A\n\n"
                         "Ile to 2 + 2?\nA) 3\nB) 4\nANSWER: B\n")

    def test_unnumbered_questions_keep_their_prompts(self):
        text = "Pierwsze pytanie?\nA) <b>Tak</b>\nB) Nie\nDrugie pytanie?\nA) Nie\nB) <b>Tak</b>"
        self.assertEqual(convert_text(text, html=True),
                         "Pierwsze pytanie?\nA) Tak\nB) Nie\nANSWER: A\n\n"
                         "Drugie pytanie?\nA) Nie\nB) Tak\nANSWER: B\n")

    def test_more_than_four_options_and_literal_content(self):
        text = "Test diagnostyczny wykrywa witaminę D. i x < y?\n" + "\n".join(
            f"{letter.lower()}. {letter} — witamina D." for letter in "ABCDE"
        ) + "\nANSWER: E"
        output = convert_text(text)
        self.assertTrue(output.startswith("Test diagnostyczny wykrywa witaminę D. i x < y?\n"))
        self.assertIn("E) E — witamina D.\nANSWER: E\n", output)

    def test_html_wrapped_labels_entities_and_nested_styles(self):
        text = "<b>1. Czy x &lt; y &amp; z &gt; 0?</b>\n<b>a) Tak &amp; już</b>\nB) Nie"
        self.assertEqual(convert_text(text, html=True),
                         "Czy x < y & z > 0?\nA) Tak & już\nB) Nie\nANSWER: A\n")

    def test_style_selection(self):
        for style, tag in [("underline", "u"), ("italic", "i"), ("bold", "strong")]:
            with self.subTest(style=style):
                text = f"Pytanie?\nA) Tak\nB) <{tag}>Nie</{tag}>"
                self.assertTrue(convert_text(text, style, html=True).endswith("ANSWER: B\n"))

    def test_explicit_key_overrides_formatting(self):
        text = "Pytanie?\nA) <b>Tak</b>\nB) <b>Nie</b>\nANSWER: B"
        self.assertTrue(convert_text(text, html=True).endswith("ANSWER: B\n"))
        self.assertTrue(convert_text(text, "none", html=True).endswith("ANSWER: B\n"))

    def test_multiline_options_before_next_label_and_key(self):
        text = "Pytanie?\nA) Pierwszy\nciąg dalszy\nB) Drugi\nciąg dalszy\nANSWER: B"
        self.assertEqual(convert_text(text), "Pytanie?\nA) Pierwszy ciąg dalszy\nB) Drugi ciąg dalszy\nANSWER: B\n")

    def test_multiline_formatted_option_at_eof(self):
        text = "Pytanie?\nA) Nie\n<b>B) Tak\ni jeszcze raz</b>"
        self.assertEqual(convert_text(text, html=True), "Pytanie?\nA) Nie\nB) Tak i jeszcze raz\nANSWER: B\n")

    def test_blank_lines_and_bom(self):
        text = "\ufeffPytanie?\r\n\r\nA) Tak\r\n\r\nB) Nie\r\nANSWER: A\r\n"
        self.assertEqual(convert_text(text), "Pytanie?\nA) Tak\nB) Nie\nANSWER: A\n")

    def test_plain_txt_preserves_html_like_literals(self):
        text = "Co znaczy <b>?\nA) Znacznik <b>\nB) Inne\nANSWER: A"
        self.assertIn("Co znaczy <b>?\nA) Znacznik <b>\n", convert_text(text))

    def test_missing_and_ambiguous_keys_are_errors(self):
        cases = [
            "Pytanie?\nA) Tak\nB) Nie",
            "Pytanie?\nA) <b>Tak</b>\nB) <b>Nie</b>",
            "Pytanie?\nA) <span style='color:red'>Tak</span>\nB) Nie",
            "Pytanie?\n<b>A)</b> Tak\nB) Nie",
            "Pytanie?\nA) <b>Tylko</b> część\nB) Nie",
            "Pytanie?\nA) <i>Tak</i>\nB) Nie",
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ConversionError):
                convert_text(text, html=True)

    def test_bad_structure_is_not_silently_exported(self):
        cases = [
            "Pytanie?\nA) Tak\nANSWER: A",  # only one option
            "A) Tak\nB) Nie\nANSWER: A",  # missing prompt
            "Pytanie?\nA) Tak\nC) Nie\nANSWER: A",  # label gap
            "Pytanie?\nA) Tak\nB) Nie\nB) Może\nANSWER: A",  # duplicate label
            "Pytanie?\nA)\nB) Nie\nANSWER: A",  # empty option
            "Pytanie?\nA) Tak\nB) Nie\nANSWER: Z",  # nonexistent key
            "Pytanie?\nA) Tak\nB) Nie\nANSWER: A\nANSWER: A",  # duplicate key
            "Pytanie?\nA) Tak\nB) Nie\nANSWER: A, B",  # multiple answers
            "Pytanie?\nA) Tak\nB) Nie\nANSWER: A\nC) Może",  # option after key
            "Pytanie?\nA) Tak\nB) Nie\nANSWER: A\nA) Inne\nB) Inne\nANSWER: A",
            "Pytanie ----image1.png----?\nA) Tak\nB) Nie\nANSWER: A",
            "1. Brak odpowiedzi\n2. Pytanie?\nA) Tak\nB) Nie\nANSWER: A",
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ConversionError):
                convert_text(text)

    def test_errors_report_question_and_line(self):
        text = "1. Dobre?\nA) Tak\nB) Nie\nANSWER: A\n2. Złe?\nA) Tak\nB) Nie"
        with self.assertRaisesRegex(ConversionError, r"Pytanie 2 \(wiersz 5\)"):
            convert_text(text)

    def test_empty_document(self):
        with self.assertRaises(ConversionError):
            convert_text("\n \n")

    def test_txt_reader(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "quiz.txt"
            path.write_text("Pytanie?\nA) Tak\nB) Nie\nANSWER: A", encoding="utf-8-sig")
            text, is_html = read_source(path)
            self.assertFalse(is_html)
            self.assertTrue(convert_text(text).endswith("ANSWER: A\n"))

    def test_docx_reader_uses_body_and_preserves_paragraphs(self):
        try:
            import docx2python
        except ImportError:
            self.skipTest("Biblioteka docx2python nie jest zainstalowana")
        with patch.object(docx2python, "docx2python") as reader:
            document = reader.return_value.__enter__.return_value
            document.body = [[[["Pytanie?", "A) <b>Tak</b>", "B) Nie"]]]]
            text, is_html = read_source("quiz.docx")
            self.assertTrue(is_html)
            self.assertTrue(convert_text(text, html=is_html).endswith("ANSWER: A\n"))
            reader.assert_called_once_with(Path("quiz.docx"), html=True, duplicate_merged_cells=False)

    def test_real_docx_with_table_numbering_and_header(self):
        try:
            import docx2python
        except ImportError:
            self.skipTest("Biblioteka docx2python nie jest zainstalowana")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "quiz.docx"
            write_docx_fixture(path)
            text, is_html = read_source(path)
            self.assertEqual(convert_text(text, html=is_html),
                             "Czy x < y?\nA) Tak & już\nB) Nie\nANSWER: A\n\n"
                             "Ile to 2 + 2?\nA) 3\nB) 4\nANSWER: B\n\n"
                             "Automatyczna numeracja?\nA) Tak\nB) Nie\nANSWER: A\n")


class ExportTests(unittest.TestCase):
    def make_controller(self, source: Path) -> Application:
        # Exercise the actual export handler without requiring a display/Tcl.
        app = Application.__new__(Application)
        app.file_path = source
        app.out_num_var = Mock()
        app.out_num_var.get.return_value = "1"
        app.style_var = Mock()
        app.style_var.get.return_value = "Pogrubienie"
        app.styles = {"Pogrubienie": "bold"}
        app.set_report = Mock()
        return app

    def test_validated_export_writes_utf8(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            output = Path(directory) / "aiken.txt"
            source.write_text("Pytanie?\nA) Żółć\nB) Nie\nANSWER: A", encoding="utf-8")
            app = self.make_controller(source)
            with patch("tkinter.filedialog.asksaveasfilename", return_value=str(output)), patch("tkinter.messagebox.showinfo"):
                app.process_file()
            self.assertEqual(output.read_text(encoding="utf-8"), "Pytanie?\nA) Żółć\nB) Nie\nANSWER: A\n")

    def test_validation_failure_does_not_write_partial_result(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            output = Path(directory) / "aiken.txt"
            source.write_text("1. Dobre?\nA) Tak\nB) Nie\nANSWER: A\n2. Złe?\nA) Tak\nB) Nie", encoding="utf-8")
            output.write_text("Poprzedni wynik", encoding="utf-8")
            app = self.make_controller(source)
            with patch("tkinter.filedialog.asksaveasfilename", return_value=str(output)) as save_dialog:
                app.process_file()
                save_dialog.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "Poprzedni wynik")
            self.assertIn("Pytanie 2", app.set_report.call_args.args[1])

    def test_export_cannot_overwrite_source(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            original = "Pytanie?\nA) Tak\nB) Nie\nANSWER: A"
            source.write_text(original, encoding="utf-8")
            app = self.make_controller(source)
            with patch("tkinter.filedialog.asksaveasfilename", return_value=str(source)), patch("tkinter.messagebox.showinfo") as success:
                app.process_file()
                success.assert_not_called()
            self.assertEqual(source.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
