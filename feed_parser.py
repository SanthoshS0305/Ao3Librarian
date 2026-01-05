"""RSS/Atom feed parser for AO3 feeds."""
import feedparser
import aiohttp
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime
from html import unescape
from urllib.parse import unquote
import re

logger = logging.getLogger(__name__)


class FeedParser:
    """Parser for AO3 Atom feeds."""
    
    @staticmethod
    def extract_tag_names(html_content: str) -> Set[str]:
        """Extract tag names from HTML summary content."""
        tag_names = set()
        # Pattern to match AO3 tag URLs and extract tag names
        # Matches: https://archiveofourown.org/tags/TagName or .../tags/TagName/works
        pattern = r'href="https://archiveofourown\.org/tags/([^"/]+)'
        matches = re.findall(pattern, html_content)
        for match in matches:
            # URL decode the tag name
            tag_name = unquote(match)
            tag_names.add(tag_name)
        return tag_names
    
    @staticmethod
    def construct_feed_url(tag_id: str) -> str:
        """Construct feed URL from tag_id."""
        return f"https://archiveofourown.org/tags/{tag_id}/feed.atom"
    
    @staticmethod
    def parse_entry(entry) -> Dict:
        """Parse a single Atom entry into a structured dict."""
        # Extract basic info
        entry_id = entry.get("id", "")
        title = unescape(entry.get("title", "Untitled"))
        link = entry.get("link", "")
        published = entry.get("published_parsed")
        updated = entry.get("updated_parsed")
        
        # Parse dates
        published_dt = None
        if published:
            published_dt = datetime(*published[:6])
        
        updated_dt = None
        if updated:
            updated_dt = datetime(*updated[:6])
        
        # Extract author
        author = "Unknown"
        if "author" in entry:
            author = entry["author"]
        elif "authors" in entry and entry["authors"]:
            author = entry["authors"][0]
        
        # Extract summary and parse tags (extract tag names, not URLs)
        summary_html = entry.get("summary", "")
        tag_names = FeedParser.extract_tag_names(summary_html)
        
        # Extract metadata from summary HTML
        metadata = FeedParser._extract_metadata(summary_html)
        
        return {
            "id": entry_id,
            "title": title,
            "link": link,
            "author": author,
            "published": published_dt,
            "updated": updated_dt,
            "summary_html": summary_html,
            "tag_names": tag_names,  # Changed from tag_urls to tag_names
            **metadata
        }
    
    @staticmethod
    def _extract_metadata(html_content: str) -> Dict:
        """Extract metadata like word count, chapters, rating from HTML summary."""
        metadata = {
            "words": None,
            "chapters": None,
            "language": None,
            "rating": None,
            "warnings": [],
            "categories": [],
            "characters": [],
            "relationships": [],
            "additional_tags": []
        }
        
        # Extract word count
        words_match = re.search(r'Words:\s*(\d+)', html_content)
        if words_match:
            metadata["words"] = int(words_match.group(1))
        
        # Extract chapters
        chapters_match = re.search(r'Chapters:\s*(\d+)/(\d+|\?)', html_content)
        if chapters_match:
            metadata["chapters"] = chapters_match.group(0)
        
        # Extract language
        lang_match = re.search(r'Language:\s*([^<]+)', html_content)
        if lang_match:
            metadata["language"] = lang_match.group(1).strip()
        
        # Extract rating
        rating_match = re.search(r'Rating:\s*<a[^>]*>([^<]+)</a>', html_content)
        if rating_match:
            metadata["rating"] = rating_match.group(1)
        
        # Extract warnings
        warnings_match = re.search(r'Warnings:\s*(.*?)(?:Categories:|Characters:|Relationships:|Additional Tags:|</li>)', html_content, re.DOTALL)
        if warnings_match:
            warnings_text = warnings_match.group(1)
            warnings_links = re.findall(r'<a[^>]*>([^<]+)</a>', warnings_text)
            metadata["warnings"] = warnings_links
        
        # Extract categories
        categories_match = re.search(r'Categories:\s*(.*?)(?:Characters:|Relationships:|Additional Tags:|</li>)', html_content, re.DOTALL)
        if categories_match:
            categories_text = categories_match.group(1)
            categories_links = re.findall(r'<a[^>]*>([^<]+)</a>', categories_text)
            metadata["categories"] = categories_links
        
        # Extract characters
        characters_match = re.search(r'Characters:\s*(.*?)(?:Relationships:|Additional Tags:|</li>)', html_content, re.DOTALL)
        if characters_match:
            characters_text = characters_match.group(1)
            characters_links = re.findall(r'<a[^>]*>([^<]+)</a>', characters_text)
            metadata["characters"] = characters_links
        
        # Extract relationships
        relationships_match = re.search(r'Relationships:\s*(.*?)(?:Additional Tags:|</li>)', html_content, re.DOTALL)
        if relationships_match:
            relationships_text = relationships_match.group(1)
            relationships_links = re.findall(r'<a[^>]*>([^<]+)</a>', relationships_text)
            metadata["relationships"] = relationships_links
        
        # Extract additional tags
        tags_match = re.search(r'Additional Tags:\s*(.*?)(?:</li>|</ul>)', html_content, re.DOTALL)
        if tags_match:
            tags_text = tags_match.group(1)
            tags_links = re.findall(r'<a[^>]*>([^<]+)</a>', tags_text)
            metadata["additional_tags"] = tags_links
        
        return metadata
    
    @staticmethod
    async def fetch_and_parse(feed_url: str) -> Optional[Dict]:
        """Fetch and parse an Atom feed."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch feed {feed_url}: HTTP {response.status}")
                        return None
                    
                    content = await response.text()
                    parsed = feedparser.parse(content)
                    
                    if parsed.bozo:
                        logger.warning(f"Feed parsing warning for {feed_url}: {parsed.bozo_exception}")
                    
                    return {
                        "feed": parsed.feed,
                        "entries": [FeedParser.parse_entry(entry) for entry in parsed.entries],
                        "updated": parsed.feed.get("updated_parsed"),
                        "title": parsed.feed.get("title", "Unknown Feed")
                    }
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return None
    
    @staticmethod
    def filter_entries_by_tags(entries: List[Dict], excluded_tag_names: Set[str]) -> List[Dict]:
        """Filter entries that contain any excluded tag names (case-insensitive)."""
        if not excluded_tag_names:
            return entries
        
        # Normalize excluded tag names to lowercase for case-insensitive matching
        excluded_lower = {name.lower() for name in excluded_tag_names}
        
        filtered = []
        for entry in entries:
            entry_tag_names = entry.get("tag_names", set())
            # Normalize entry tag names to lowercase for comparison
            entry_tag_lower = {name.lower() for name in entry_tag_names}
            # Check if any excluded tag name matches any entry tag name
            if not excluded_lower.intersection(entry_tag_lower):
                filtered.append(entry)
        
        return filtered
    
    @staticmethod
    def get_new_entries(entries: List[Dict], last_entry_id: Optional[str]) -> List[Dict]:
        """Get entries that are newer than the last seen entry."""
        if not last_entry_id:
            # No previous entry, return all entries sorted by updated date
            return sorted(entries, key=lambda x: x.get("updated") or x.get("published") or datetime.min, reverse=True)
        
        # Find the index of the last entry
        last_index = None
        for i, entry in enumerate(entries):
            if entry["id"] == last_entry_id:
                last_index = i
                break
        
        if last_index is None:
            # Last entry not found, return all entries
            return sorted(entries, key=lambda x: x.get("updated") or x.get("published") or datetime.min, reverse=True)
        
        # Return entries before the last one (newer entries)
        return entries[:last_index]


# Global parser instance
feed_parser = FeedParser()
