"""Konwersja DOCX/TXT do AIKEN. Uruchom GUI: python main_2.py.

Jawny klucz ANSWER: B ma pierwszeństwo przed formatowaniem. Dla DOCX
domyślnym oznaczeniem jest pogrubienie całej treści poprawnej odpowiedzi.
Parser i eksport są niezależne od GUI oraz biblioteki docx2python.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Iterable


OPTION_RE = re.compile(r"^\s*([A-Z])[.)](?:\s+(.*)|$)", re.IGNORECASE)
NUMBER_RE = re.compile(
    r"^\s*(?:(?:pytanie|question|zadanie|q)\s*\d+\s*[.):]|\d+[.)](?=\s|$))\s*",
    re.IGNORECASE,
)
KEY_START_RE = re.compile(
    r"^(?:ANSWER|ODPOWIEDŹ|ODPOWIEDZ)\s*:", re.IGNORECASE)
KEY_RE = re.compile(
    r"^(?:ANSWER|ODPOWIEDŹ|ODPOWIEDZ)\s*:\s*([A-Z])[.)]?\s*$", re.IGNORECASE
)
DOCUMENT_TITLE_RE = re.compile(
    r"^[\w.\-]+\s*[–—-]\s*\d+\s+pytani\w*\s*$", re.IGNORECASE
)
SIMPLE_TITLE_RE = re.compile(
    r"^(?:test|quiz|exam|egzamin|tytuł|tytul|title)\s*:?$", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
STYLE_TAGS = {"bold": {"b", "strong"}, "underline": {
    "u"}, "italic": {"i", "em"}, "none": set()}
HTML_TAGS = {"b", "strong", "u", "i", "em", "span", "s", "sup", "sub", "a", "br", "p",
             "h1", "h2", "h3", "h4", "h5", "h6"}
UNSUPPORTED_RE = re.compile(
    r"----(?:image|footnote|endnote)[^-]*----", re.IGNORECASE)


def one_line(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


@dataclass(frozen=True)
class SourceLine:
    text: str
    number: int
    # One flag per character, so bold labels alone cannot mark an answer.
    marks: tuple[bool, ...] = ()

    def fully_marked(self, start: int = 0) -> bool:
        if len(self.marks) != len(self.text):
            return False
        flags = [self.marks[i] for i in range(
            start, len(self.text)) if not self.text[i].isspace()]
        return bool(flags) and all(flags)


class FormattedTextParser(HTMLParser):
    """Decode known formatting tags without deleting literal comparisons."""

    def __init__(self, style: str):
        super().__init__(convert_charrefs=True)
        self.style_tags = STYLE_TAGS[style]
        self.active: dict[str, int] = {}
        self.parts: list[str] = []
        self.marks: list[bool] = []

    def handle_data(self, data: str) -> None:
        marked = any(self.active.get(tag, 0) for tag in self.style_tags)
        self.parts.append(data)
        self.marks.extend([marked] * len(data))

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in HTML_TAGS:
            self.handle_data(self.get_starttag_text())
        elif tag == "br":
            self.handle_data("\n")
        else:
            self.active[tag] = self.active.get(tag, 0) + 1

    def handle_endtag(self, tag: str) -> None:
        if tag not in HTML_TAGS:
            self.handle_data(f"</{tag}>")
        else:
            self.active[tag] = max(0, self.active.get(tag, 0) - 1)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)


def source_lines(text: str, correct_style: str = "bold", *, html: bool = False) -> list[SourceLine]:
    """TXT is literal text; HTML is decoded only for DOCX/formatted input."""
    if correct_style not in STYLE_TAGS:
        raise ValueError(
            f"Nieznany sposób oznaczenia odpowiedzi: {correct_style}")
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if html:
        parser = FormattedTextParser(correct_style)
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)
        marks = parser.marks
    else:
        # Plain text has no formatting; avoid a per-character allocation.
        marks = []
    result = []
    offset = 0
    for number, raw in enumerate(text.split("\n"), 1):
        left = len(raw) - len(raw.lstrip())
        clean = raw.strip()
        result.append(SourceLine(clean, number, tuple(
            marks[offset + left:offset + left + len(clean)])))
        offset += len(raw) + 1
    return result


@dataclass(frozen=True)
class Question:
    text: str
    options: tuple[tuple[str, str], ...]
    correct_answer: str


class ConversionError(ValueError):
    def __init__(self, issues: Iterable[str]):
        self.issues = tuple(issues)
        super().__init__("\n".join(self.issues))


@dataclass
class _Option:
    label: str
    parts: list[str]
    marked: bool


@dataclass
class _Buffer:
    line: int
    prompt: list[str] = field(default_factory=list)
    options: list[_Option] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Delay assigning text after an option until the next label/key is known.
    trailing: list[SourceLine] = field(default_factory=list)

    def attach_trailing(self) -> None:
        if self.trailing and self.options:
            option = self.options[-1]
            for line in self.trailing:
                option.parts.append(line.text)
                option.marked = option.marked and line.fully_marked()
            self.trailing.clear()


def parse_questions(lines: Iterable[SourceLine]) -> list[Question]:
    """Single-pass parser; never silently drops incomplete question blocks.

    Repeated A) transfers pending text to the next unnumbered question.
    A last answer continuation followed by an unnumbered question is ambiguous:
    use a numbered question or an explicit ANSWER line to separate them.
    """
    questions: list[Question] = []
    issues: list[str] = []
    current: _Buffer | None = None
    block_number = 0

    def finish() -> None:
        nonlocal current, block_number
        if current is None:
            return
        current.attach_trailing()
        block_number += 1
        errors = list(current.errors)
        prompt = one_line(" ".join(current.prompt))
        options = tuple((opt.label, one_line(" ".join(opt.parts)))
                        for opt in current.options)
        labels = [label for label, _ in options]
        if not prompt:
            errors.append("brak treści pytania")
        if len(options) < 2:
            errors.append("wymagane co najmniej dwie odpowiedzi")
        if len(labels) != len(set(labels)):
            errors.append("powtórzone etykiety odpowiedzi")
        if labels != [chr(ord("A") + i) for i in range(len(labels))]:
            errors.append(
                "odpowiedzi muszą mieć kolejne etykiety A, B, C, ...")
        if any(not text for _, text in options):
            errors.append("pusta treść odpowiedzi")
        if current.keys:
            if len(current.keys) != 1:
                errors.append("wymagany dokładnie jeden wiersz ANSWER")
            correct = current.keys[0]
            if correct not in labels:
                errors.append(
                    f"klucz {correct} nie wskazuje istniejącej odpowiedzi")
        else:
            marked = [opt.label for opt in current.options if opt.marked]
            correct = marked[0] if len(marked) == 1 else ""
            if not marked:
                errors.append(
                    "brak klucza ANSWER lub jednoznacznie oznaczonej odpowiedzi")
            elif len(marked) > 1:
                errors.append(
                    "oznaczono kilka poprawnych odpowiedzi; AIKEN wymaga jednej")
        if errors:
            prefix = f"Pytanie {block_number} (wiersz {current.line})"
            issues.extend(f"{prefix}: {error}." for error in errors)
        else:
            questions.append(Question(prompt, options, correct))
        current = None

    for line in lines:
        text = line.text
        if not text:
            continue
        option_match = OPTION_RE.match(text)
        number_match = NUMBER_RE.match(text)
        key_start = KEY_START_RE.match(text)

        if key_start:
            if current is None:
                current = _Buffer(line.number)
            current.attach_trailing()
            key_match = KEY_RE.fullmatch(text)
            if key_match:
                current.keys.append(key_match.group(1).upper())
            else:
                current.errors.append(
                    f"nieprawidłowy klucz w wierszu {line.number}; użyj ANSWER: B")
            continue

        if option_match:
            label = option_match.group(1).upper()
            if current and current.options and label == "A":
                # Text between the previous last option and A) is the new prompt.
                pending = current.trailing
                current.trailing = []
                finish()
                current = _Buffer(
                    pending[0].number if pending else line.number)
                current.prompt.extend(item.text for item in pending)
            if current is None:
                current = _Buffer(line.number)
            current.attach_trailing()
            if current.keys:
                current.errors.append(
                    f"odpowiedź {label} występuje po kluczu ANSWER")
            current.options.append(_Option(
                label, [option_match.group(2) or ""],
                line.fully_marked(option_match.start(
                    2)) if option_match.group(2) else False,
            ))
        elif number_match:
            if current and (current.options or current.prompt or current.keys):
                finish()
            if current is None:
                current = _Buffer(line.number)
            remainder = text[number_match.end():]
            if remainder:
                current.prompt.append(remainder)
        else:
            if current and current.keys:
                finish()
            if current is None and (DOCUMENT_TITLE_RE.fullmatch(text) or SIMPLE_TITLE_RE.fullmatch(text)):
                continue
            if current is None:
                current = _Buffer(line.number)
            if current.options:
                current.trailing.append(line)
            else:
                current.prompt.append(text)

        if current and UNSUPPORTED_RE.search(text):
            current.errors.append(
                f"obraz lub przypis w wierszu {line.number}; AIKEN obsługuje tylko tekst")

    finish()
    if issues:
        raise ConversionError(issues)
    if not questions:
        raise ConversionError(["Nie wykryto pytań z odpowiedziami."])
    return questions


def render_aiken(questions: Iterable[Question]) -> str:
    blocks = []
    for question in questions:
        lines = [question.text]
        lines.extend(f"{label}) {text}" for label, text in question.options)
        lines.append(f"ANSWER: {question.correct_answer}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def convert_text(text: str, correct_style: str = "bold", *, html: bool = False) -> str:
    return render_aiken(parse_questions(source_lines(text, correct_style, html=html)))


def read_source(file_path: str | Path) -> tuple[str, bool]:
    path = Path(file_path)
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8-sig"), False
    if path.suffix.lower() != ".docx":
        raise ValueError("Wybierz plik .docx lub .txt zapisany w UTF-8.")
    try:
        from docx2python import docx2python
    except ImportError as exc:
        raise RuntimeError(
            "Brak biblioteki docx2python. Zainstaluj: python -m pip install docx2python") from exc
    # Only body: page headers/footers and footnote text cannot become questions.
    # Keep paragraphs and avoid duplicating the content of merged table cells.
    with docx2python(path, html=True, duplicate_merged_cells=False) as document:
        paragraphs = (
            paragraph for table in document.body for row in table for cell in row for paragraph in cell)
        return "\n".join(paragraphs), True


class Application:
    def __init__(self, master):
        import tkinter as tk
        from tkinter import ttk

        self.master = master
        self.file_path: Path | None = None
        master.title("Question Extractor by Jubyness v2.0.0")
        master.geometry("690x520")
        master.minsize(590, 420)
        frame = ttk.Frame(master, padding=12)
        frame.pack(fill="both", expand=True)
        self.file_label = ttk.Label(
            frame, text="Wybierz plik DOCX lub TXT (UTF-8).", wraplength=640)
        self.file_label.pack(anchor="w", pady=(0, 8))
        ttk.Button(frame, text="Wybierz plik",
                   command=self.browse_file).pack(anchor="w")
        settings = ttk.Frame(frame)
        settings.pack(fill="x", pady=12)
        ttk.Label(settings, text="Numer pliku wynikowego:").grid(
            row=0, column=0, sticky="w")
        self.out_num_var = tk.StringVar(value="1")
        ttk.Entry(settings, textvariable=self.out_num_var, width=8).grid(
            row=0, column=1, sticky="w", padx=8)
        ttk.Label(settings, text="Oznaczenie poprawnej odpowiedzi w DOCX:").grid(
            row=1, column=0, sticky="w", pady=8)
        self.styles = {"Pogrubienie": "bold", "Podkreślenie": "underline",
                       "Kursywa": "italic", "Tylko klucz ANSWER": "none"}
        self.style_var = tk.StringVar(value="Pogrubienie")
        ttk.Combobox(settings, textvariable=self.style_var, values=list(
            self.styles), state="readonly", width=23).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(frame, text="Klucz ANSWER: B ma pierwszeństwo. Formatowanie musi obejmować całą treść odpowiedzi.",
                  wraplength=640).pack(anchor="w", pady=(0, 8))
        ttk.Button(frame, text="Konwertuj i zapisz",
                   command=self.process_file).pack(anchor="w", pady=(0, 10))
        self.status = ttk.Label(frame, text="", wraplength=640)
        self.status.pack(anchor="w", pady=(0, 6))
        report_frame = ttk.Frame(frame)
        report_frame.pack(fill="both", expand=True)
        self.report = tk.Text(report_frame, wrap="word",
                              height=10, state="disabled")
        scrollbar = ttk.Scrollbar(report_frame, command=self.report.yview)
        self.report.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.report.pack(fill="both", expand=True)

    def set_report(self, status: str, details: str = "") -> None:
        self.status.configure(text=status)
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", details)
        self.report.configure(state="disabled")

    def browse_file(self) -> None:
        from tkinter import filedialog

        selected = filedialog.askopenfilename(filetypes=[(
            "Word i tekst", "*.docx *.txt"), ("Word", "*.docx"), ("Tekst UTF-8", "*.txt")])
        if selected:
            self.file_path = Path(selected)
            self.file_label.configure(text=str(self.file_path))
            self.set_report("")

    def process_file(self) -> None:
        from tkinter import filedialog, messagebox

        if self.file_path is None:
            self.set_report("Najpierw wybierz plik DOCX lub TXT.")
            return
        try:
            number = int(self.out_num_var.get())
            if number < 1:
                raise ValueError
        except ValueError:
            self.set_report(
                "Numer pliku wynikowego musi być dodatnią liczbą całkowitą.")
            return
        try:
            raw, is_html = read_source(self.file_path)
            questions = parse_questions(source_lines(
                raw, self.styles[self.style_var.get()], html=is_html))
            output = render_aiken(questions)
        except ConversionError as exc:
            self.set_report(
                "Nie zapisano pliku. Popraw wskazane pytania i spróbuj ponownie.", str(exc))
            return
        except Exception as exc:
            self.set_report(
                "Nie udało się odczytać lub przetworzyć pliku.", str(exc))
            return

        self.set_report(
            f"Sprawdzono {len(questions)} pytań. Wybierz miejsce zapisu.", output)
        selected = filedialog.asksaveasfilename(
            title="Zapisz pytania w formacie AIKEN", initialdir=str(self.file_path.parent),
            initialfile=f"final_text_{number}.txt", defaultextension=".txt",
            filetypes=[("Tekst AIKEN", "*.txt")], confirmoverwrite=True,
        )
        if not selected:
            self.set_report("Anulowano zapis.", output)
            return
        destination = Path(selected)
        if destination.resolve() == self.file_path.resolve():
            self.set_report(
                "Wybierz inny plik wynikowy, aby zachować dokument źródłowy.", output)
            return
        try:
            destination.write_text(output, encoding="utf-8")
        except OSError as exc:
            self.set_report("Nie udało się zapisać pliku.", str(exc))
            return
        self.set_report(
            f"Zapisano {len(questions)} pytań: {destination}", output)
        messagebox.showinfo(
            "Zapisano", f"Zapisano {len(questions)} pytań w formacie AIKEN.\n{destination}")


if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    Application(root)
    root.mainloop()
