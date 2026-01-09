from pypdf import PdfReader

def read_pdf(file_path):
    """
    Reads a PDF file and returns its text content.
    """
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def read_file(file_path):
    """
    Reads a file (PDF or text) and returns its content.
    """
    if file_path.endswith('.pdf'):
        return read_pdf(file_path)
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
