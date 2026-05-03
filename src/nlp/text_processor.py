"""
Text Processing Module.
Utility functions for document extraction and preprocessing.
Includes advanced artifact removal capabilities.
"""

from PyPDF2 import PdfReader
from docx import Document
import re
from typing import List, Dict, Optional, Tuple
from collections import Counter


def extract_text_from_pdf(file) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file: File object (uploaded via FastAPI or any file-like source)
    
    Returns:
        str: Extracted text.
    """
    text = ""
    try:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")
    return text


def extract_text_from_txt(file) -> str:
    """
    Extract text from a TXT file.
    
    Args:
        file: File object.
    
    Returns:
        str: Extracted text.
    """
    try:
        text = str(file.read(), "utf-8")
    except Exception as e:
        raise Exception(f"Error reading TXT: {str(e)}")
    return text


def extract_text_from_docx(file) -> str:
    """
    Extract text from a DOCX file.
    
    Args:
        file: File object.
    
    Returns:
        str: Extracted text.
    """
    text = ""
    try:
        doc = Document(file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")
    return text


def extract_text_multi_format(files: List) -> str:
    """
    Extract text from multiple files of different formats.
    
    Args:
        files: List of uploaded files.
    
    Returns:
        str: Consolidated text from all files.
    """
    consolidated_text = ""
    
    for file in files:
        file_type = file.type
        
        try:
            if file_type == "application/pdf":
                consolidated_text += f"\n\n=== FILE: {file.name} ===\n\n"
                consolidated_text += extract_text_from_pdf(file)
            
            elif file_type == "text/plain":
                consolidated_text += f"\n\n=== FILE: {file.name} ===\n\n"
                consolidated_text += extract_text_from_txt(file)
            
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                consolidated_text += f"\n\n=== FILE: {file.name} ===\n\n"
                consolidated_text += extract_text_from_docx(file)
            
            else:
                print(f"Unsupported format: {file.name} ({file_type})")
        
        except Exception as e:
            print(f"Error processing {file.name}: {str(e)}")
            continue
    
    return consolidated_text


def remove_email_signatures(text: str) -> str:
    """
    Remove email signatures from text.
    Detects and removes common signature patterns in multiple languages.
    
    Args:
        text: Input text containing potential email signatures
        
    Returns:
        Text with signatures removed
    """
    # Common signature markers (multilingual)
    signature_markers = [
        r'--+\s*\n',  # Standard signature separator --
        r'_{3,}\s*\n',  # Underscores ___
        r'Best regards,?\s*\n',
        r'Kind regards,?\s*\n',
        r'Sincerely,?\s*\n',
        r'Regards,?\s*\n',
        r'Thanks,?\s*\n',
        r'Thank you,?\s*\n',
        r'Sent from my',  # Mobile signatures
        r'Enviado do meu',  # Portuguese mobile
        r'Envoyé de mon',  # French mobile
        r'Atenciosamente,?\s*\n',  # Portuguese formal
        r'Cordialmente,?\s*\n',  # Portuguese/French cordial
        r'Cordialement,?\s*\n',  # French formal
        r'Abraços,?\s*\n',  # Portuguese informal
    ]
    
    # Try to find signature start
    lines = text.split('\n')
    signature_start = len(lines)
    
    for i, line in enumerate(lines):
        for marker in signature_markers:
            if re.search(marker, line, re.IGNORECASE):
                signature_start = min(signature_start, i)
                break
    
    # If signature found, remove from that point onwards
    if signature_start < len(lines):
        # Keep text before signature
        cleaned_lines = lines[:signature_start]
        return '\n'.join(cleaned_lines)
    
    return text


def remove_disclaimers(text: str) -> str:
    """
    Remove legal disclaimers and confidentiality notices.
    
    Args:
        text: Input text
        
    Returns:
        Text with disclaimers removed
    """
    # Common disclaimer patterns (multilingual)
    disclaimer_patterns = [
        r'(?i)CONFIDENTIAL[ITY]?\s+NOTICE.*?(?=\n\n|\Z)',
        r'(?i)CONFIDENCIAL.*?(?=\n\n|\Z)',
        r'(?i)This\s+(?:e-?mail|message|communication).*?confidential.*?(?=\n\n|\Z)',
        r'(?i)Este\s+(?:e-?mail|mensaje|mensaje).*?confidencial.*?(?=\n\n|\Z)',
        r'(?i)Ce\s+(?:courriel|message).*?confidentiel.*?(?=\n\n|\Z)',
        r'(?i)DISCLAIMER:.*?(?=\n\n|\Z)',
        r'(?i)AVISO\s+LEGAL:.*?(?=\n\n|\Z)',
        r'(?i)The\s+information\s+contained\s+in\s+this.*?(?=\n\n|\Z)',
        r'(?i)A\s+informacao\s+contida\s+neste.*?(?=\n\n|\Z)',
        r'(?i)If\s+you\s+(?:are\s+not\s+the\s+intended|have\s+received\s+this\s+in\s+error).*?(?=\n\n|\Z)',
        r'(?i)Please\s+consider\s+the\s+environment.*?(?=\n\n|\Z)',
        r'(?i)Think\s+before\s+you\s+print.*?(?=\n\n|\Z)',
    ]
    
    cleaned_text = text
    for pattern in disclaimer_patterns:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
    
    return cleaned_text


def remove_headers_footers(text: str) -> str:
    """
    Remove document headers and footers.
    Detects repeated text at beginning/end of pages.
    
    Args:
        text: Input text
        
    Returns:
        Text with headers/footers removed
    """
    lines = text.split('\n')
    
    if len(lines) < 10:
        return text
    
    # Detect page breaks (common patterns)
    page_break_pattern = r'(?:Page\s+\d+|Página\s+\d+|\f|\x0c)'
    
    # Split into pages if page breaks exist
    pages = re.split(page_break_pattern, text)
    
    if len(pages) > 1:
        # Find common first/last lines across pages
        first_lines = [p.split('\n')[0] if p.strip() else '' for p in pages]
        last_lines = [p.split('\n')[-1] if p.strip() else '' for p in pages]
        
        # Count occurrences
        first_counter = Counter([line.strip() for line in first_lines if line.strip()])
        last_counter = Counter([line.strip() for line in last_lines if line.strip()])
        
        # If a line appears in >50% of pages, it's likely a header/footer
        threshold = len(pages) * 0.5
        
        common_headers = {line for line, count in first_counter.items() if count > threshold}
        common_footers = {line for line, count in last_counter.items() if count > threshold}
        
        # Remove common headers/footers
        cleaned_pages = []
        for page in pages:
            page_lines = page.split('\n')
            
            # Remove header
            if page_lines and page_lines[0].strip() in common_headers:
                page_lines = page_lines[1:]
            
            # Remove footer
            if page_lines and page_lines[-1].strip() in common_footers:
                page_lines = page_lines[:-1]
            
            cleaned_pages.append('\n'.join(page_lines))
        
        return '\n\n'.join(cleaned_pages)
    
    return text


def remove_page_numbers(text: str) -> str:
    """
    Remove standalone page numbers.
    
    Args:
        text: Input text
        
    Returns:
        Text with page numbers removed
    """
    # Patterns for page numbers
    patterns = [
        r'^\s*\d+\s*$',  # Standalone number on a line
        r'^\s*-\s*\d+\s*-\s*$',  # -3-
        r'^\s*Page\s+\d+\s*$',  # Page 3
        r'^\s*Página\s+\d+\s*$',  # Página 3
        r'^\s*P[áa]gina\s+\d+\s*$',  # Página 3 (with accent)
        r'^\s*\d+\s+of\s+\d+\s*$',  # 3 of 10
        r'^\s*\d+\s+de\s+\d+\s*$',  # 3 de 10
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        is_page_number = False
        for pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                is_page_number = True
                break
        
        if not is_page_number:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def remove_boilerplate(text: str, min_repetitions: int = 3) -> str:
    """
    Remove repeated boilerplate text.
    Detects and removes text blocks that appear multiple times.
    
    Args:
        text: Input text
        min_repetitions: Minimum number of repetitions to consider as boilerplate
        
    Returns:
        Text with boilerplate removed
    """
    # Split into sentences or short paragraphs
    blocks = re.split(r'\n\n+', text)
    
    if len(blocks) < 5:
        return text
    
    # Count block occurrences (normalized)
    block_counter = Counter()
    normalized_blocks = {}
    
    for block in blocks:
        # Normalize: lowercase, remove extra whitespace
        normalized = ' '.join(block.lower().split())
        if len(normalized) > 20:  # Ignore very short blocks
            block_counter[normalized] += 1
            if normalized not in normalized_blocks:
                normalized_blocks[normalized] = block
    
    # Identify boilerplate (appears >= min_repetitions times)
    boilerplate_blocks = {norm for norm, count in block_counter.items() 
                         if count >= min_repetitions}
    
    # Remove boilerplate, keeping first occurrence
    seen_boilerplate = set()
    cleaned_blocks = []
    
    for block in blocks:
        normalized = ' '.join(block.lower().split())
        
        if normalized in boilerplate_blocks:
            # Keep first occurrence only
            if normalized not in seen_boilerplate:
                cleaned_blocks.append(block)
                seen_boilerplate.add(normalized)
        else:
            cleaned_blocks.append(block)
    
    return '\n\n'.join(cleaned_blocks)


def remove_special_noise(text: str) -> str:
    """
    Remove special characters and noise that don't add value.
    
    Args:
        text: Input text
        
    Returns:
        Text with noise removed
    """
    # Remove null bytes and control characters (except common ones)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    
    # Remove excessive punctuation
    text = re.sub(r'[!]{3,}', '!', text)
    text = re.sub(r'[?]{3,}', '?', text)
    text = re.sub(r'[.]{4,}', '...', text)
    
    # Remove excessive dashes/underscores (but keep reasonable ones)
    text = re.sub(r'-{4,}', '---', text)
    text = re.sub(r'_{4,}', '___', text)
    text = re.sub(r'={4,}', '===', text)
    
    # Remove zero-width characters
    text = text.replace('\u200b', '')  # Zero-width space
    text = text.replace('\ufeff', '')  # Byte order mark
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")
    
    # Remove multiple spaces (but preserve single spaces)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Normalize line breaks (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def remove_artifacts(text: str,
                    remove_signatures: bool = True,
                    remove_disclaimers: bool = True,
                    remove_headers_footers: bool = True,
                    remove_page_numbers: bool = True,
                    remove_boilerplate: bool = True,
                    remove_noise: bool = True) -> str:
    """
    Comprehensive artifact removal with configurable options.
    Applies all cleaning steps in optimal order.
    
    Args:
        text: Raw input text
        remove_signatures: Remove email signatures
        remove_disclaimers: Remove legal disclaimers
        remove_headers_footers: Remove document headers/footers
        remove_page_numbers: Remove page numbers
        remove_boilerplate: Remove repeated boilerplate text
        remove_noise: Remove special characters and noise
        
    Returns:
        Cleaned text with artifacts removed
    """
    if not text or not text.strip():
        return ""
    
    cleaned = text
    
    # Order matters - remove in this sequence for best results
    if remove_signatures:
        cleaned = remove_email_signatures(cleaned)
    
    if remove_disclaimers:
        cleaned = remove_disclaimers(cleaned)
    
    if remove_headers_footers:
        cleaned = remove_headers_footers(cleaned)
    
    if remove_page_numbers:
        cleaned = remove_page_numbers(cleaned)
    
    if remove_boilerplate:
        cleaned = remove_boilerplate(cleaned)
    
    if remove_noise:
        cleaned = remove_special_noise(cleaned)
    
    # Final normalization
    cleaned = cleaned.strip()
    
    return cleaned


def clean_text(text: str, deep_clean: bool = False) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Raw text.
        deep_clean: Apply comprehensive artifact removal (slower but more thorough)
    
    Returns:
        str: Cleaned text.
    """
    if deep_clean:
        # Apply comprehensive artifact removal
        return remove_artifacts(text)
    
    # Basic cleaning (fast, original implementation)
    # Remove multiple whitespaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove problematic special characters
    text = text.replace('\x00', '')
    
    # Remove repeated blank lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks for processing.
    Useful when working with Vector Stores.
    
    Args:
        text: Full text.
        chunk_size: Chunk size in characters.
        overlap: Overlap between chunks.
    
    Returns:
        List[str]: List of chunks.
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def extract_metadata(text: str) -> Dict:
    """
    Extract basic metadata from text.
    
    Args:
        text: Text for analysis.
    
    Returns:
        Dict: Metadata dictionary.
    """
    # Count words
    words = text.split()
    
    # Detect possible dates (simple regex)
    dates_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    dates = re.findall(dates_pattern, text)
    
    # Detect emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    metadata = {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": text.count('\n'),
        "dates_found": len(dates),
        "emails_found": len(emails),
        "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0
    }
    
    return metadata
