# Konwerter Pytania-Odpowiedzi z Pliku Word do Formatu Aiken

## Opis Programu

Program konwertuje pytania i odpowiedzi z pliku Word do formatu Aiken, który jest używany w niektórych systemach do przeprowadzania quizów. W rezultacie otrzymasz plik tekstowy, który można łatwo zaimportować do systemu do przeprowadzania testów.

## Struktura Pliku Word

1. **Pytania:**
   - Pytania powinny być sformatowane jako numerowane listy.
   - Odpowiedzi do pytań powinny być sformatowane jako podpunkty (A, B, C).

2. **Oznaczenia HTML:**
   - Jeśli plik Word zawiera oznaczenia HTML, takie jak `<u>`, `<i>`, `<b>`, program uwzględni te formatowania.

3. **Obrazy:**
   - Obrazy mogą być dołączone do pytań, ale program je zignoruje.

## Jak Używać Programu

1. Zainstaluj biblioteke `docx2python`.

```shell
pip install docx2python
```

2. Uruchom skrypt `main.py`.

```shell
python main.py
```

3. Wybierz plik Word, który chcesz skonwertować.
4. Program przetworzy plik i utworzy plik tekstowy w formacie Aiken.
5. Sprawdź wynikowy plik `final_text.txt` dla pytań i odpowiedzi w formacie Aiken.

## Uwagi

- Jeśli plik zawiera oznaczenia HTML, program je uwzględni w odpowiedziach.
- Program może zignorować obrazy lub inne elementy, które nie pasują do struktury pytania-odpowiedzi.

## Wynik

Wynikiem działania programu będzie plik tekstowy `final_text.txt` zawierający pytania i odpowiedzi w formacie Aiken, gotowy do importu do systemu do przeprowadzania testów.

---

**Autor:** Jubyness
**Kontakt:** <dev@jubyness.pl>
