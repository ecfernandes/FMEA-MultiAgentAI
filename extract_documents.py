"""Extract text from PDF and DOCX documents for research."""
import sys
try:
    import PyPDF2
    from docx import Document
except ImportError:
    print("ERROR: Required libraries not installed. Please run:")
    print("pip install PyPDF2 python-docx")
    sys.exit(1)

def extract_pdf_text(pdf_path):
    """Extract text from PDF file."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text.append(f"\n--- PAGE {page_num + 1} ---\n")
                text.append(page.extract_text())
            return ''.join(text)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_docx_text(docx_path):
    """Extract text from DOCX file."""
    try:
        doc = Document(docx_path)
        text = []
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

if __name__ == "__main__":
    base_path = r"c:\Users\Usuário\OneDrive\_2025_POST DOC_UTFPR_UTC\_Management Project _AI\PM_AI"
    
    # Extract PDF
    pdf_path = f"{base_path}\\Presentation_AI_Driven_Risk_Analysis_Redesign_An_Industry_50_Framework_for_FMEAv1.pdf"
    print("=" * 80)
    print("EXTRACTING PRESENTATION PDF")
    print("=" * 80)
    pdf_text = extract_pdf_text(pdf_path)
    print(pdf_text)
    
    print("\n\n")
    print("=" * 80)
    print("EXTRACTING MEETING MINUTES DOCX")
    print("=" * 80)
    
    # Extract DOCX
    docx_path = f"{base_path}\\Meeting_Minutes_2March26.docx"
    docx_text = extract_docx_text(docx_path)
    print(docx_text)
