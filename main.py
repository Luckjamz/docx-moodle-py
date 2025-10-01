import tkinter as tk
from tkinter import filedialog, messagebox
from docx2python import docx2python
import os
import re

# --- Wzorce ---

# Akceptuj A) lub A. jako wiersz opcji
OPTION_LABEL = re.compile(r'^\s*([A-D])[\)\.]\s+', re.IGNORECASE)
HAS_HTML_TAG = re.compile(r'</?(span|b|i|u)\b', re.IGNORECASE)

# "Pytanie 1:", "Question 2)", "Zadanie 3." w osobnej linii
TITLE_ONLY_RE = re.compile(
    r'^\s*(?:pytanie|question|zadanie|q(?:uestion)?)?\s*\d+\s*[\.\)]\s*:?\s*$',
    re.IGNORECASE
)

# Prefiksy numeracji/tytułów na początku linii pytania
PREFIX_NUMBERING_RE = re.compile(
    r'^\s*(?:pytanie|question|zadanie|q(?:uestion)?)?\s*\d+\s*[\.\)]\s*:?\s*',
    re.IGNORECASE
)

ONLY_SYMBOLS_RE = re.compile(r'^[\W_]+$')

# Tytuły dokumentów w stylu: "13.13.d – 2 pytania", "13.d - 2 pytania"
DOC_TITLE_RE = re.compile(
    r'^\s*[\w\.\-]+\s*[–-]\s*\d+\s+pytani\w*\s*$',
    re.IGNORECASE
)

# --- Pomocnicze ---


def normalize_choice_labels(line: str) -> str:
    """Ujednolica etykiety opcji: a)/a. -> A) itd."""
    # najpierw kropki -> nawiasy
    line = re.sub(r'(?<![A-Za-z0-9])([a-d])\.',
                  lambda m: f"{m.group(1).upper()})", line, flags=re.IGNORECASE)
    # potem małe litery z nawiasem -> wielkie
    line = re.sub(r'(?<![A-Za-z0-9])a\)', 'A)', line, flags=re.IGNORECASE)
    line = re.sub(r'(?<![A-Za-z0-9])b\)', 'B)', line, flags=re.IGNORECASE)
    line = re.sub(r'(?<![A-Za-z0-9])c\)', 'C)', line, flags=re.IGNORECASE)
    line = re.sub(r'(?<![A-Za-z0-9])d\)', 'D)', line, flags=re.IGNORECASE)
    return line


def is_numbered_start(line: str) -> bool:
    return bool(re.match(r'^\s*\d+\s*[\.\)]\s*', line))


def is_option_line(line: str):
    m = OPTION_LABEL.match(line)
    if m:
        return True, m.group(1).upper()
    return False, None


def strip_html(line: str) -> str:
    line = re.sub(r'style=".*?"', '', line)
    line = re.sub(r'<[^>]+>', '', line)
    return line


def is_garbage_title(line: str) -> bool:
    txt = line.strip()
    if not txt:
        return True
    if ONLY_SYMBOLS_RE.match(txt):
        return True
    if DOC_TITLE_RE.match(txt):   # <<< kluczowe: tytuł jak w Twoim pliku
        return True
    if re.match(r'^(test|quiz|exam|egzamin|tytuł|tytul|title)\b', txt, re.IGNORECASE):
        return True
    return False


def looks_like_title_only(line: str, next_line: str | None) -> bool:
    txt = line.strip()
    if is_garbage_title(txt):
        return True
    if TITLE_ONLY_RE.match(txt):
        return True
    if txt.endswith(':') and (next_line is not None) and not OPTION_LABEL.match(next_line.strip()):
        return True
    return False


def remove_numbering_and_title_prefixes(line: str) -> str:
    # usuń "Pytanie 1:" / "Question 2)" / "1." / "2)"
    line = PREFIX_NUMBERING_RE.sub('', line)
    # ewentualne pozostałości
    line = re.sub(r'^\s*[\.\)]\s*', '', line)
    return line.lstrip()


def block_has_at_least_two_options(block_lines):
    seen = set()
    for ln in block_lines:
        is_opt, lab = is_option_line(ln)
        if is_opt:
            seen.add(lab)
    return len(seen) >= 2


def find_correct_options_in_block(block_lines):
    correct = []
    for ln in block_lines:
        is_opt, lab = is_option_line(ln)
        if is_opt and HAS_HTML_TAG.search(ln):
            correct.append(lab)
    return correct


def split_into_question_blocks(lines):
    """Heurystyka podziału na pytania."""
    blocks, cur = [], []

    def flush_if_valid():
        nonlocal cur
        if cur and block_has_at_least_two_options(cur):
            blocks.append(cur)
        cur = []

    for line in lines:
        line = normalize_choice_labels(line)
        is_opt, lab = is_option_line(line)

        if is_numbered_start(line) and cur and block_has_at_least_two_options(cur):
            flush_if_valid()

        if is_opt and lab == 'A' and cur and block_has_at_least_two_options(cur):
            flush_if_valid()

        cur.append(line)

    flush_if_valid()
    return blocks

# --- Główna logika ---


def extract_and_group_questions(file_path, output_number=1):
    with docx2python(file_path, html=True) as docx_content:
        raw_text = docx_content.text

    # linie niepuste
    lines = [ln.strip() for ln in raw_text.split('\n') if ln.strip()]
    if not lines:
        messagebox.showwarning(
            "Warning", "Dokument jest pusty po czyszczeniu.")
        return False

    # globalny filtr nagłówków/tytułów (np. "13.13.d – 2 pytania")
    lines = [ln for ln in lines if not is_garbage_title(ln)]
    if not lines:
        messagebox.showwarning(
            "Warning", "Po odfiltrowaniu nagłówków nie ma treści.")
        return False

    blocks = split_into_question_blocks(lines)
    if not blocks:
        messagebox.showinfo("Info", "Nie wykryto pytań z odpowiedziami.")
        return False

    output_lines = []

    for blk in blocks:
        # 1) HTML off
        cleaned = [strip_html(x) for x in blk]
        # UWAGA: NIE usuwamy już "-.*" (żeby nie uciąć fraz jak " - azotem.")

        # 2) Usuń linie-tytuły/śmieci z początku bloku
        idx = 0
        while idx < len(cleaned):
            nxt = cleaned[idx+1] if (idx + 1) < len(cleaned) else None
            if looks_like_title_only(cleaned[idx], nxt):
                idx += 1
            else:
                break
        cleaned = cleaned[idx:]
        if not cleaned:
            continue

        # 3) Usuń numerację z KAŻDEJ linii przed pierwszą opcją (A/B/C/D)
        first_opt = None
        for i, ln in enumerate(cleaned):
            if is_option_line(ln)[0]:
                first_opt = i
                break
        if first_opt is None:
            first_opt = len(cleaned)
        for i in range(first_opt):
            cleaned[i] = remove_numbering_and_title_prefixes(cleaned[i])

        # 4) Normalizuj prefiksy opcji w całym bloku (A. -> A))
        cleaned = [normalize_choice_labels(ln) for ln in cleaned]

        # 5) Zapis treści (pomijaj śmieci)
        for ln in cleaned:
            if ln and not is_garbage_title(ln) and not ONLY_SYMBOLS_RE.match(ln):
                output_lines.append(ln)

        # 6) ANSWER: X) (na podstawie formatowania oryginalnych linii)
        correct_labels = find_correct_options_in_block(blk)
        for lab in correct_labels:
            output_lines.append(f"ANSWER:{lab})")

    final_output_file_name = f"final_text_{output_number}.txt"
    if os.path.exists(final_output_file_name):
        user_response = messagebox.askyesno(
            "File Exists", f"{final_output_file_name} już istnieje. Nadpisać?"
        )
        if not user_response:
            messagebox.showinfo("Info", "Przerwano – bez zmian.")
            return False

    with open(final_output_file_name, "w", encoding="utf-8") as f:
        f.write('\n'.join(output_lines))

    print(f"File saved as {final_output_file_name}")
    return True

# --- GUI ---


class Application:
    def __init__(self, master):
        self.master = master
        self.master.title("Question Extractor by Jubyness v.0.6.0")
        self.master.geometry("540x230")
        self.file_path = None

        frm = tk.Frame(self.master)
        frm.pack(fill='both', expand=True, padx=12, pady=12)

        self.label = tk.Label(frm, text="Select a Word document:")
        self.label.pack(pady=(0, 8), anchor='w')

        self.button = tk.Button(frm, text="Browse", command=self.browse_file)
        self.button.pack(pady=(0, 12), anchor='w')

        num_frame = tk.Frame(frm)
        num_frame.pack(pady=(0, 12), anchor='w')

        num_label = tk.Label(num_frame, text="Output suffix number: ")
        num_label.pack(side='left')

        self.out_num_var = tk.StringVar(value="1")
        num_entry = tk.Entry(num_frame, textvariable=self.out_num_var, width=6)
        num_entry.pack(side='left')

        self.process_button = tk.Button(
            frm, text="Process File", command=self.process_file)
        self.process_button.pack(pady=4, anchor='w')

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Word Documents", "*.docx")])
        if file_path:
            self.file_path = file_path
            self.label.config(text=f"Selected File: {file_path}")

    def process_file(self):
        if not self.file_path:
            tk.messagebox.showwarning(
                "Warning", "Najpierw wybierz plik .docx.")
            return
        try:
            out_no = int(self.out_num_var.get())
        except ValueError:
            out_no = 1
        success = extract_and_group_questions(
            self.file_path, output_number=out_no)
        if success:
            tk.messagebox.showinfo(
                "Success", f"Zapisano: final_text_{out_no}.txt")
        else:
            tk.messagebox.showwarning(
                "Warning", "Przetwarzanie przerwane lub brak danych.")


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()
