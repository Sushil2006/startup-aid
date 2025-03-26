import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text("text") for page in doc)
    return text

# Example usage
if __name__ == "__main__":
    pdf_path = "qp.pdf"
    extracted_text = extract_text_from_pdf(pdf_path)
    print(extracted_text)
