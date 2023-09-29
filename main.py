import tkinter as tk
from tkinter import filedialog, messagebox
from docx2python import docx2python
import os
import re

def group_text_by_numbers(text):
     # Find numbers like '1)', '2)', etc.
    numbers_pattern = re.compile(r'(\d+\))')
    numbers_matches = numbers_pattern.findall(text)

    #Check if the qustion paragraph is a lisl number
    if not numbers_matches:
        messagebox.showinfo("Info", "No numbered questions found in the text. Cannot process!")
        if os.path.exists("processed_text.txt"):
            os.remove("processed_text.txt")
        return None

    # Initialize a list to store grouped text
    grouped_text = []

    # Iterate through number matches
    for number_match in numbers_matches:
        # Use regex to find the text block starting with the number
        pattern = re.compile(f'{re.escape(number_match)}(.*?)(\d+\)|\Z)', re.DOTALL)
        match = pattern.search(text)

        if match:
            # Append the matched text block to the grouped_text list
            grouped_text.append(match.group(1))

    return grouped_text

def extract_and_group_questions(file_path, output_number=1):
     # Open the Word document
    with docx2python(file_path, html=True) as docx_content:
        text_with_formatting = docx_content.text

    # Remove empty paragraphs
    lines = [line.strip() for line in text_with_formatting.split('\n') if line.strip()]

    # Change answer choices format to uppercase (A), B), C))
    lines = [re.sub(r'(?<![A-Za-z0-9])a\)', 'A)', line) for line in lines]
    lines = [re.sub(r'(?<![A-Za-z0-9])b\)', 'B)', line) for line in lines]
    lines = [re.sub(r'(?<![A-Za-z0-9])c\)', 'C)', line) for line in lines]

    # Save processed text to a file
    processed_file_path = "processed_text.txt"
    with open(processed_file_path, "w", encoding="utf-8") as processed_file:
        processed_file.write('\n'.join(lines))

    # Read processed text from the file
    with open(processed_file_path, "r", encoding="utf-8") as processed_file:
        processed_contents = processed_file.read()

    # Group text by numbers
    grouped_text_blocks = group_text_by_numbers(processed_contents)
    # print(grouped_text_blocks)
    # Initialize a list to store lines with "ANSWER" prefixes
    lines_with_answers = []

    # Iterate through groups and add "ANSWER" prefixes
    for group in grouped_text_blocks:
        lines_with_answers.append(group)
        # Find matches for answer choices in <span> tags within the group
        answer_pattern = re.compile(r'([A-Z]\))\s*<(span|u|i|b).*?>.*?<\/(span|u|i|b)>')
        answer_matches = answer_pattern.findall(group)

        # # Iterate through matches and add the prefix "ANSWER: "
        # for i, answer_option in enumerate(span_matches):
        #     formatted_answer = f"ANSWER: {answer_option}"
        #     lines_with_answers.append(formatted_answer)

        # Iterate through matches and add the prefix "ANSWER: "
        for answer_match in answer_matches:
            answer_option = answer_match[0]
            formatted_answer = f"ANSWER:{answer_option}"
            lines_with_answers.append(formatted_answer)

    

     # Remove <span>, <u>, <i>, or <b> tags
    lines_with_answers = [re.sub(r'<(span|u|i|b).*?>|<\/(span|u|i|b)>', '', line) for line in lines_with_answers]
    # Remove HTML tags and style attributes from the lines with answers
    lines_with_answers = [re.sub(r'<.*?>', '', line) for line in lines_with_answers]
    lines_with_answers = [re.sub(r'style=".*?"', '', line) for line in lines_with_answers]
    # Remove ---images tag
    lines_with_answers = [re.sub(r'-.*','', line ) for line in lines_with_answers]
    
    if os.path.exists("processed_text.txt"):
        os.remove("processed_text.txt")

    # Construct the final output file name with a number
    final_output_file_name = f"final_text_{output_number}.txt"

     # Check if the file already exists
    if os.path.exists(final_output_file_name):
        # # Ask for confirmation to overwrite
        # user_input = input(f"The file {final_output_file_name} already exists. Overwrite? (Y/N): ").lower()
        # if user_input != 'y':
        #     messagebox.showwarning("Warning", "Operation aborted.")
        #     return
        # Ask the user if they want to overwrite the file
        user_response = messagebox.askyesno("File Exists", f"{final_output_file_name} already exists. Do you want to overwrite it?")
        if not user_response:
            messagebox.showinfo("Info", "No changes made.")
            return False

    # Save the final text to a file
    with open(final_output_file_name, "w", encoding="utf-8") as final_output_file:
        final_output_file.write('\n'.join(lines_with_answers))
        print(f"File saved as {final_output_file_name}")

    return True

class Application:
    def __init__(self, master):
        self.master = master
        self.master.title("Question Extractor by Jubyness v.0.1.0")
        self.master.geometry("480x200")

        self.label = tk.Label(self.master, text="Select a Word document:")
        self.label.pack(pady=10)

        self.button = tk.Button(self.master, text="Browse", command=self.browse_file)
        self.button.pack(pady=10)

        self.process_button = tk.Button(self.master, text="Process File", command=self.process_file)
        self.process_button.pack(pady=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Word Documents", "*.docx")])
        self.label.config(text=f"Selected File: {file_path}")
        self.file_path = file_path

    def process_file(self):
        if hasattr(self, 'file_path'):
            success = extract_and_group_questions(self.file_path)
            if success:
                tk.messagebox.showinfo("Success", "File processed successfully!")
            else:
                tk.messagebox.showwarning("Warning", "Processing aborted.")
        else:
            tk.messagebox.showwarning("Warning", "Please select a file before processing.")

if __name__ == "__main__":
    root = tk.Tk()
    app = Application(root)
    root.mainloop()