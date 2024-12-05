"""
URL utility functions.
"""
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Optional


class UrlUtils:
    """URL utility functions."""

    @staticmethod
    def extract_article_id(url: str) -> Optional[str]:
        """Extract article ID from URL."""
        if not url:
            return None

        # Extract article ID from various URL patterns
        patterns = [
            r'article/(\d+)/(\d+)',  # Standard news article pattern
            r'aid=(\d+)',            # Query parameter pattern
            r'/(\d+)$'               # URL ending with ID pattern
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    # @staticmethod
    # def normalize_url(url: str) -> str:
    #     """Normalize URL by removing unnecessary parameters and fragments."""
    #     if not url:
    #         return ""

    #     parsed = urlparse(url)

    #     # Get query parameters
    #     params = parse_qs(parsed.query, keep_blank_values=True)

    #     # Remove unnecessary parameters
    #     unnecessary_params = ['utm_source', 'utm_medium', 'utm_campaign']
    #     for param in unnecessary_params:
    #         params.pop(param, None)

    #     # Reconstruct URL
    #     return urlunparse((
    #         parsed.scheme,
    #         parsed.netloc,
    #         parsed.path,
    #         parsed.params,
    #         urlencode(params, doseq=True),
    #         ''  # Remove fragment
    #     ))

    @staticmethod
    def add_query_params(url: str, params: Dict[str, str]) -> str:
        """Add query parameters to URL."""
        if not url:
            return ""

        parsed = urlparse(url)

        # Get existing query parameters
        existing_params = parse_qs(parsed.query, keep_blank_values=True)

        # Update with new parameters
        existing_params.update(params)

        # Reconstruct URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(existing_params, doseq=True),
            parsed.fragment
        ))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        if not url:
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    # async def _remove_html_tags(self, text: str) -> str:
    #     """Remove HTML tags from text using BeautifulSoup."""
    #     soup = BeautifulSoup(text, 'html.parser')
    #     return soup.get_text(separator=' ', strip=True)

    def extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return ""

