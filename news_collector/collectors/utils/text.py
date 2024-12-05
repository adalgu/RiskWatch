"""
Text utility functions.
"""
import re
from typing import List, Optional
from bs4 import BeautifulSoup


class TextUtils:
    """Text utility functions."""

    @staticmethod
    def clean_html(html: str) -> str:
        """Remove HTML tags and clean text."""
        if not html:
            return ""

        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading/trailing space
        lines = (line.strip() for line in text.splitlines())

        # Break multi-headlines into a line each
        chunks = (phrase.strip()
                  for line in lines for phrase in line.split("  "))

        # Drop blank lines
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text.strip()

    @staticmethod
    def extract_numbers(text: str) -> List[int]:
        """Extract numbers from text."""
        return [int(num) for num in re.findall(r'\d+', text)]

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace in text."""
        if not text:
            return ""
        return ' '.join(text.split())

    @staticmethod
    def remove_special_chars(text: str, keep_chars: Optional[str] = None) -> str:
        """Remove special characters from text."""
        if not text:
            return ""

        pattern = r'[^a-zA-Z0-9\s'
        if keep_chars:
            pattern += keep_chars
        pattern += ']'

        return re.sub(pattern, '', text)
