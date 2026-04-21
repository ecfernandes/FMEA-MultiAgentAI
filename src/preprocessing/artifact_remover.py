"""
Artifact Remover Module
Advanced text cleaning and artifact removal for FMEA documents.

This module provides comprehensive cleaning functions to remove:
- Email signatures and disclaimers
- Document headers and footers
- Page numbers
- Legal disclaimers
- Boilerplate text
- Watermarks
- Noise characters
- Repeated content
"""

import re
from typing import List, Dict, Set, Tuple
import hashlib


class ArtifactRemover:
    """
    Advanced artifact removal from documents.
    Cleans noise, headers, footers, signatures, and other non-content text.
    """
    
    def __init__(self, aggressive: bool = False):
        """
        Initialize artifact remover.
        
        Args:
            aggressive: If True, applies more aggressive cleaning (may remove valid content)
        """
        self.aggressive = aggressive
        
        # Common email signature patterns (multilingual)
        self.signature_patterns = [
            r'--+',  # Signature separator
            r'_{3,}',  # Underscore separator
            r'Sent from my .*',
            r'Enviado do meu .*',
            r'Envoy[ée] de mon .*',
            r'Get Outlook for .*',
            r'This email and any attachments.*confidential.*',
            r'Este e-?mail.*confidencial.*',
            r'Ce message.*confidentiel.*',
        ]
        
        # Disclaimer patterns
        self.disclaimer_patterns = [
            r'CONFIDENTIAL.*?proprietary',
            r'CONFIDENCIAL.*?propriet[áa]rio',
            r'This message.*intended.*recipient.*',
            r'Esta mensagem.*destinat[áa]rio.*',
            r'Copyright.*All rights reserved',
            r'Direitos autorais.*reservados',
            r'Printed on \d+',
            r'Impresso em \d+',
            r'Page \d+ of \d+',
            r'P[áa]gina \d+ de \d+',
        ]
        
        # Header/footer patterns
        self.header_footer_patterns = [
            r'^Page \d+$',
            r'^P[áa]gina \d+$',
            r'^\d+$',  # Lone page numbers
            r'^[A-Z\s]+\d{4}-\d{2}-\d{2}$',  # Document headers with dates
            r'^Confidential.*$',
            r'^Draft.*$',
            r'^DRAFT.*$',
            r'^Internal Use Only.*$',
            r'^Uso Interno.*$',
        ]
        
        # Common boilerplate phrases (to detect repeated content)
        self.boilerplate_phrases = [
            'please do not reply to this email',
            'this is an automated message',
            'unsubscribe',
            'privacy policy',
            'terms of service',
            'click here',
        ]
    
    def remove_email_signatures(self, text: str) -> str:
        """
        Remove email signatures from text.
        
        Email signatures typically start with:
        - Horizontal lines (----, ____)
        - Common phrases like "Sent from", "Best regards"
        - Contact information blocks
        
        Args:
            text: Input text
            
        Returns:
            Text without email signatures
        """
        lines = text.split('\n')
        cleaned_lines = []
        in_signature = False
        signature_start_idx = len(lines)
        
        # Detect signature start
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for signature separators
            if re.match(r'^[-_]{3,}$', line_stripped):
                in_signature = True
                signature_start_idx = idx
                break
            
            # Check for common signature patterns
            for pattern in self.signature_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    in_signature = True
                    signature_start_idx = idx
                    break
            
            if in_signature:
                break
        
        # Keep only lines before signature
        cleaned_lines = lines[:signature_start_idx]
        
        return '\n'.join(cleaned_lines)
    
    def remove_disclaimers(self, text: str) -> str:
        """
        Remove legal disclaimers and confidentiality notices.
        
        Args:
            text: Input text
            
        Returns:
            Text without disclaimers
        """
        for pattern in self.disclaimer_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text
    
    def remove_headers_footers(self, text: str) -> str:
        """
        Remove document headers and footers.
        
        Headers/footers typically appear at:
        - Beginning or end of pages
        - Contain page numbers, dates, document titles
        - Are repeated across multiple pages
        
        Args:
            text: Input text
            
        Returns:
            Text without headers/footers
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                cleaned_lines.append(line)
                continue
            
            # Check if line matches header/footer patterns
            is_header_footer = False
            for pattern in self.header_footer_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_header_footer = True
                    break
            
            # Skip page numbers (standalone numbers)
            if line_stripped.isdigit() and len(line_stripped) <= 4:
                is_header_footer = True
            
            # Keep line if not header/footer
            if not is_header_footer:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_page_numbers(self, text: str) -> str:
        """
        Remove standalone page numbers.
        
        Args:
            text: Input text
            
        Returns:
            Text without page numbers
        """
        # Remove patterns like "Page 1", "Page 1 of 10", etc.
        text = re.sub(r'\bPage\s+\d+(\s+of\s+\d+)?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bP[áa]gina\s+\d+(\s+de\s+\d+)?\b', '', text, flags=re.IGNORECASE)
        
        # Remove standalone numbers that look like page numbers
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # If line is just a number (1-4 digits), skip it
            if stripped.isdigit() and len(stripped) <= 4:
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_watermarks(self, text: str) -> str:
        """
        Remove common watermark text.
        
        Watermarks often contain:
        - DRAFT, CONFIDENTIAL, COPY
        - Repeated throughout document
        
        Args:
            text: Input text
            
        Returns:
            Text without watermarks
        """
        watermark_patterns = [
            r'\bDRAFT\b',
            r'\bCONFIDENTIAL\b',
            r'\bCONFIDENCIAL\b',
            r'\bINTERNAL\s+USE\s+ONLY\b',
            r'\bUSO\s+INTERNO\b',
            r'\bCOPY\b',
            r'\bC[OÓ]PIA\b',
            r'\bPRELIMINARY\b',
            r'\bPRELIMINAR\b',
        ]
        
        for pattern in watermark_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def remove_table_of_contents(self, text: str) -> str:
        """
        Remove table of contents sections.
        
        TOC typically contains:
        - Lists with page numbers
        - Dots connecting titles and numbers
        - Common headers like "Contents", "Index"
        
        Args:
            text: Input text
            
        Returns:
            Text without TOC
        """
        # Look for TOC section headers
        toc_headers = [
            r'^\s*table\s+of\s+contents\s*$',
            r'^\s*contents\s*$',
            r'^\s*[íi]ndice\s*$',
            r'^\s*sum[áa]rio\s*$',
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        in_toc = False
        toc_line_count = 0
        
        for line in lines:
            line_lower = line.strip().lower()
            
            # Check if entering TOC
            for pattern in toc_headers:
                if re.match(pattern, line_lower):
                    in_toc = True
                    toc_line_count = 0
                    break
            
            # If in TOC, look for patterns indicating TOC content
            if in_toc:
                toc_line_count += 1
                
                # TOC lines usually have dots and page numbers
                if re.search(r'\.{3,}.*\d+$', line):
                    continue  # Skip TOC line
                
                # Exit TOC after empty line or max lines
                if not line.strip() or toc_line_count > 50:
                    in_toc = False
                    if not line.strip():
                        continue
            
            if not in_toc:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def detect_and_remove_boilerplate(self, text: str, threshold: float = 0.7) -> str:
        """
        Detect and remove repeated boilerplate text.
        
        Boilerplate is text that appears multiple times (e.g., disclaimers, 
        standard paragraphs).
        
        Args:
            text: Input text
            threshold: Similarity threshold for considering text as boilerplate
            
        Returns:
            Text without boilerplate
        """
        paragraphs = text.split('\n\n')
        
        # Count paragraph occurrences
        para_counts: Dict[str, int] = {}
        para_hashes: Dict[str, str] = {}
        
        for para in paragraphs:
            para_stripped = para.strip()
            if len(para_stripped) < 30:  # Skip very short paragraphs
                continue
            
            # Create hash for exact matching
            para_hash = hashlib.md5(para_stripped.encode()).hexdigest()
            para_hashes[para_hash] = para_stripped
            para_counts[para_hash] = para_counts.get(para_hash, 0) + 1
        
        # Identify boilerplate (appears more than once)
        boilerplate_hashes = {h for h, count in para_counts.items() if count > 1}
        
        # Remove boilerplate
        cleaned_paragraphs = []
        seen_hashes: Set[str] = set()
        
        for para in paragraphs:
            para_stripped = para.strip()
            if len(para_stripped) < 30:
                cleaned_paragraphs.append(para)
                continue
            
            para_hash = hashlib.md5(para_stripped.encode()).hexdigest()
            
            # If boilerplate, keep only first occurrence
            if para_hash in boilerplate_hashes:
                if para_hash not in seen_hashes:
                    cleaned_paragraphs.append(para)
                    seen_hashes.add(para_hash)
                # Skip subsequent occurrences
            else:
                cleaned_paragraphs.append(para)
        
        return '\n\n'.join(cleaned_paragraphs)
    
    def remove_noise_characters(self, text: str) -> str:
        """
        Remove noise characters and control codes.
        
        Args:
            text: Input text
            
        Returns:
            Text without noise characters
        """
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove other control characters (except newlines, tabs)
        text = re.sub(r'[\x01-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove zero-width characters
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)
        
        # Remove excessive special characters
        text = re.sub(r'[^\w\s\-.,;:!?()\[\]{}\'\"/@#$%&*+=<>|\\`~\n\t]', ' ', text)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace (advanced version).
        
        - Convert multiple spaces to single space
        - Remove trailing spaces
        - Normalize blank lines
        - Convert tabs to spaces
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Convert tabs to spaces
        text = text.replace('\t', '    ')
        
        # Remove trailing whitespace from each line
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        
        # Remove multiple spaces
        text = '\n'.join(lines)
        text = re.sub(r' {2,}', ' ', text)
        
        # Normalize blank lines (max 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from entire text
        text = text.strip()
        
        return text
    
    def remove_urls(self, text: str) -> str:
        """
        Remove URLs from text.
        
        Args:
            text: Input text
            
        Returns:
            Text without URLs
        """
        # Remove http(s) URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove www URLs
        text = re.sub(r'www\.\S+', '', text)
        
        # Remove email addresses (optional)
        if self.aggressive:
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        return text
    
    def clean(self, text: str, 
              remove_signatures: bool = True,
              remove_disclaimers: bool = True,
              remove_headers_footers: bool = True,
              remove_page_numbers: bool = True,
              remove_watermarks: bool = True,
              remove_toc: bool = True,
              remove_boilerplate: bool = True,
              remove_noise: bool = True,
              remove_urls: bool = False,
              normalize_ws: bool = True) -> str:
        """
        Apply all cleaning operations.
        
        Args:
            text: Input text
            remove_signatures: Remove email signatures
            remove_disclaimers: Remove legal disclaimers
            remove_headers_footers: Remove document headers/footers
            remove_page_numbers: Remove page numbers
            remove_watermarks: Remove watermark text
            remove_toc: Remove table of contents
            remove_boilerplate: Remove repeated boilerplate text
            remove_noise: Remove noise characters
            remove_urls: Remove URLs
            normalize_ws: Normalize whitespace
            
        Returns:
            Cleaned text
        """
        # Apply cleaning in order
        if remove_noise:
            text = self.remove_noise_characters(text)
        
        if remove_signatures:
            text = self.remove_email_signatures(text)
        
        if remove_disclaimers:
            text = self.remove_disclaimers(text)
        
        if remove_headers_footers:
            text = self.remove_headers_footers(text)
        
        if remove_page_numbers:
            text = self.remove_page_numbers(text)
        
        if remove_watermarks:
            text = self.remove_watermarks(text)
        
        if remove_toc:
            text = self.remove_table_of_contents(text)
        
        if remove_boilerplate:
            text = self.detect_and_remove_boilerplate(text)
        
        if remove_urls:
            text = self.remove_urls(text)
        
        if normalize_ws:
            text = self.normalize_whitespace(text)
        
        return text
    
    def get_cleaning_stats(self, original_text: str, cleaned_text: str) -> Dict[str, any]:
        """
        Get statistics about cleaning operation.
        
        Args:
            original_text: Original text before cleaning
            cleaned_text: Cleaned text
            
        Returns:
            Dictionary with cleaning statistics
        """
        original_lines = original_text.split('\n')
        cleaned_lines = cleaned_text.split('\n')
        
        return {
            'original_length': len(original_text),
            'cleaned_length': len(cleaned_text),
            'removed_chars': len(original_text) - len(cleaned_text),
            'reduction_percentage': round((1 - len(cleaned_text) / len(original_text)) * 100, 2) if len(original_text) > 0 else 0,
            'original_lines': len(original_lines),
            'cleaned_lines': len(cleaned_lines),
            'removed_lines': len(original_lines) - len(cleaned_lines),
        }


# Convenience functions for quick usage
def quick_clean(text: str, aggressive: bool = False) -> str:
    """
    Quick clean using default settings.
    
    Args:
        text: Input text
        aggressive: Use aggressive cleaning
        
    Returns:
        Cleaned text
    """
    remover = ArtifactRemover(aggressive=aggressive)
    return remover.clean(text)


def clean_email(text: str) -> str:
    """
    Clean email text (emphasis on signatures and disclaimers).
    
    Args:
        text: Email text
        
    Returns:
        Cleaned email text
    """
    remover = ArtifactRemover()
    return remover.clean(
        text,
        remove_signatures=True,
        remove_disclaimers=True,
        remove_urls=True
    )


def clean_document(text: str) -> str:
    """
    Clean formal document (emphasis on headers/footers, page numbers).
    
    Args:
        text: Document text
        
    Returns:
        Cleaned document text
    """
    remover = ArtifactRemover()
    return remover.clean(
        text,
        remove_headers_footers=True,
        remove_page_numbers=True,
        remove_watermarks=True,
        remove_toc=True
    )
