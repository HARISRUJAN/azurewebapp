"""
PDF Processing Service

This service handles extraction of text content from PDF documents.
Used for processing regulatory documents and frameworks stored as PDFs.

Key Features:
- Multi-page PDF text extraction
- Text cleaning and normalization
- Error handling for corrupted or unreadable PDFs
- Support for batch processing of PDF directories
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
import pypdf


class PDFService:
    """
    Service for extracting and processing text from PDF documents.
    
    This service provides methods to:
    - Extract full text from PDF files
    - Process multiple PDFs from a directory
    - Clean and normalize extracted text
    - Handle errors gracefully
    """
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract all text content from a PDF file.
        
        This method reads through all pages of the PDF and concatenates
        the text content. Handles errors gracefully for corrupted PDFs.
        
        Args:
            pdf_path: Path to the PDF file (absolute or relative)
            
        Returns:
            Extracted text content as a single string
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: For PDF reading errors (corrupted files, etc.)
        """
        # Validate file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Read PDF and extract text from all pages
        text_parts = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                # Extract text from each page
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():  # Only add non-empty pages
                            text_parts.append(page_text)
                    except Exception as e:
                        # Log page extraction error but continue with other pages
                        print(f"Warning: Error extracting text from page {page_num} of {pdf_path}: {e}")
                        continue
                
        except Exception as e:
            raise Exception(f"Error reading PDF file {pdf_path}: {str(e)}")
        
        # Combine all pages and clean text
        full_text = "\n\n".join(text_parts)
        cleaned_text = PDFService._clean_text(full_text)
        
        return cleaned_text
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean and normalize extracted PDF text.
        
        Removes excessive whitespace, normalizes line breaks, and handles
        common PDF extraction artifacts.
        
        Args:
            text: Raw extracted text from PDF
            
        Returns:
            Cleaned and normalized text
        """
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace (more than 2 consecutive spaces)
        import re
        text = re.sub(r' {3,}', ' ', text)
        
        # Remove excessive newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def process_pdf_directory(directory: str, file_pattern: str = "*.pdf") -> List[Dict[str, str]]:
        """
        Process all PDF files in a directory.
        
        Scans the specified directory for PDF files and extracts text from each.
        Returns a list of dictionaries with file information and extracted content.
        
        Args:
            directory: Path to directory containing PDFs
            file_pattern: Glob pattern for PDF files (default: "*.pdf")
            
        Returns:
            List of dictionaries, each containing:
            - 'file_path': Full path to the PDF file
            - 'filename': Name of the PDF file
            - 'text': Extracted text content
            - 'page_count': Number of pages in the PDF
        """
        pdf_files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find all PDF files matching the pattern
        for pdf_file in directory_path.glob(file_pattern):
            try:
                # Extract text
                text = PDFService.extract_text_from_pdf(str(pdf_file))
                
                # Get page count
                with open(pdf_file, 'rb') as file:
                    pdf_reader = pypdf.PdfReader(file)
                    page_count = len(pdf_reader.pages)
                
                pdf_files.append({
                    'file_path': str(pdf_file),
                    'filename': pdf_file.name,
                    'text': text,
                    'page_count': page_count
                })
                
            except Exception as e:
                print(f"Error processing PDF {pdf_file.name}: {e}")
                continue
        
        return pdf_files


# Global PDF service instance
pdf_service = PDFService()

