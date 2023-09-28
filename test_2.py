from docx2python import docx2python
from tkinter import Tk, Button, filedialog, Label

def extract_questions(file_path):
    # Use docx2python to get the text with formatting
    with docx2python(file_path, html=True) as docx_content:
        text_with_formatting = docx_content.text
    result_label.config(text=text_with_formatting)

def open_file_dialog():
    file_path = filedialog.askopenfilename()
    if file_path:
        extract_questions(file_path)

def clear_result():
    result_label.config(text="")

# Create the main Tkinter window
root = Tk()
root.title("Word Document Extractor")

# Create a button to open the file dialog
open_button = Button(root, text="Open Word Document", command=open_file_dialog)
open_button.pack(pady=10)

# Create a button to clear the result
clear_button = Button(root, text="Clear Result", command=clear_result)
clear_button.pack(pady=10)

# Create a label for displaying the result
result_label = Label(root, text="")
result_label.pack()

# Start the Tkinter event loop
root.mainloop()
