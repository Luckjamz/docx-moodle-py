from docx2python import docx2python
from docx import Document
import re

def extract_questions(file_path):
    # Use docx2python to get the text with formatting
    with docx2python(file_path, html=True) as docx_content:
        text_with_formatting = docx_content.text
    print(text_with_formatting)


# Provide the path to the Word file
word_file_path = "plik.docx"

# Call the extraction function
extract_questions(word_file_path)