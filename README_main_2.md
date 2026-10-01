# Konwerter AIKEN — wersja 2

Uruchomienie (Python 3.10 lub nowszy):

```powershell
python -m pip install docx2python
python main_2.py
```

Wybierz DOCX lub TXT w UTF-8, ustaw sposób oznaczania poprawnej odpowiedzi
i kliknij „Konwertuj i zapisz”. Program pokaże wynik albo listę błędów
z numerami pytań i wierszy. Miejsce zapisu wybierasz po walidacji.
Oryginalny `main.py` pozostaje dostępny.

## Format wejściowy

```text
1. Jaka jest stolica Polski?
a) Warszawa
b) Kraków
ANSWER: A

Pytanie 2:
Ile to 2 + 2?
A. 3
B. 4
ODPOWIEDŹ: B
```

- Numeracja pytań jest opcjonalna. Obsługiwane są prefiksy `1.`, `2)`,
  `Pytanie 1:`, `Question 2)` i `Zadanie 3.`.
- Odpowiedzi mają kolejne etykiety A–Z, kropkę lub nawias i spację.
  Małe litery są akceptowane i normalizowane wyłącznie w etykietach.
- Pytanie i odpowiedzi mogą mieć kilka wierszy; eksport scala je spacjami.
- Jawny klucz `ANSWER: B` lub `ODPOWIEDŹ: B` ma pierwszeństwo przed
  formatowaniem. Akceptowany jest również starszy zapis `ANSWER:B)`.
- DOCX może oznaczać poprawną odpowiedź pogrubieniem (domyślnie),
  podkreśleniem albo kursywą. Cała treść jednej odpowiedzi, wraz z jej
  kontynuacją, musi mieć wybrane formatowanie. Sama wyróżniona litera
  albo pojedyncze słowo nie stanowią klucza.
- TXT jest odczytywany dosłownie i wymaga jawnego klucza. Tagi HTML
  zapisane w TXT nie są interpretowane jako formatowanie.
- Brak klucza, wiele wyróżnionych odpowiedzi bez jawnego klucza,
  powtórzone etykiety, puste odpowiedzi i niepełne pytania zatrzymują
  eksport całego dokumentu. Program nie zgaduje poprawnej odpowiedzi.

## Granice rozpoznawania

Nowe pytanie rozpoznawane jest po numeracji, treści po kluczu `ANSWER`
lub powtórzeniu `A)`. Dla pytań bez numeracji tekst pomiędzy ostatnią
odpowiedzią a następnym `A)` staje się treścią kolejnego pytania.
Jeśli ostatnia odpowiedź ma kontynuację, a następne pytanie nie ma numeru,
dodaj `ANSWER` przed następnym pytaniem albo ponumeruj pytania.
Pozwala to uniknąć niejednoznacznego podziału tekstu.

W DOCX program czyta treść główną, również tabele, bez nagłówków i stopek
stron. Dokument powinien zawierać pytania i odpowiedzi w kolejności
czytania; kolumny z osobnym kluczem i złożone układy tabel wymagają
uporządkowania. Obrazy i odwołania do przypisów wykryte jako znaczniki
biblioteki zatrzymują eksport, ponieważ AIKEN obsługuje pytania tekstowe.
Odczyt stylów dziedziczonych w Word zależy od ekstrakcji `docx2python`;
w razie braku wykrytego wyróżnienia użyj jawnego klucza.

Wynik to UTF-8, jeden wiersz treści pytania, osobny wiersz każdej
odpowiedzi, klucz `ANSWER: X` oraz pusta linia między pytaniami.

## Sprawdzenie

```powershell
python -m unittest -v test_main_2
```

Testy parsera nie wymagają DOCX ani uruchomienia okna programu.
