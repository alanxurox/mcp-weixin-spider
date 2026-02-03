#!/usr/bin/env python3
"""
WeChat Article Spider - Agent-Browser Backend
Uses agent-browser CLI (Playwright-based) instead of Selenium for lighter weight crawling.

Features:
- No Chrome driver installation needed
- Uses existing agent-browser installation
- Same interface as weixin_spider_simple.py
- Subprocess-based CLI calls with JSON output

Requires: agent-browser installed at /home/ubuntu/agent-browser/
"""

import os
import re
import json
import hashlib
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent-browser binary location
AGENT_BROWSER_BIN = os.getenv(
    "AGENT_BROWSER_BIN", 
    "/home/ubuntu/agent-browser/bin/agent-browser"
)

# Optional: Path to saved browser state (cookies, storage) to bypass anti-bot
BROWSER_STATE_FILE = os.getenv("BROWSER_STATE_FILE", "")


@dataclass
class ArticleContent:
    """Data class for article content."""
    url: str
    title: str = ""
    author: str = ""
    account_name: str = ""
    publish_date: str = ""
    content_html: str = ""
    content_text: str = ""
    images: List[Dict[str, str]] = field(default_factory=list)
    word_count: int = 0
    crawl_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "account_name": self.account_name,
            "publish_date": self.publish_date,
            "content_html": self.content_html,
            "content_text": self.content_text,
            "images": self.images,
            "word_count": self.word_count,
            "crawl_timestamp": self.crawl_timestamp,
        }


class WeixinSpiderAB:
    """
    WeChat Article Spider using agent-browser CLI.
    
    Lighter weight alternative to Selenium-based spider.
    Uses subprocess calls to agent-browser binary.
    
    Usage:
        spider = WeixinSpiderAB.get_instance()
        article = spider.crawl(url)
    """
    
    _instance: Optional['WeixinSpiderAB'] = None
    _lock: threading.Lock = threading.Lock()
    
    # Configuration constants
    PAGE_LOAD_TIMEOUT = 30000  # milliseconds for agent-browser
    MAX_KEY_PHRASE_LENGTH = 100
    READING_SPEED_CPM = 200
    
    def __init__(self):
        """Initialize instance."""
        self._session_name = "weixin_spider"
        self._initialized = False
        self._state_loaded = False
    
    @classmethod
    def get_instance(cls) -> 'WeixinSpiderAB':
        """Get thread-safe singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _run_cmd(self, *args, timeout: int = 60) -> tuple[bool, str]:
        """
        Run agent-browser command.
        
        Returns (success, output) tuple.
        """
        cmd = [AGENT_BROWSER_BIN, "--session", self._session_name, "--json"] + list(args)
        logger.debug(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                logger.warning(f"Command failed: {result.stderr}")
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {cmd}")
            return False, "Timeout"
        except Exception as e:
            logger.error(f"Command error: {e}")
            return False, str(e)
    
    def _parse_json(self, output: str) -> Any:
        """Parse JSON output from agent-browser."""
        try:
            parsed = json.loads(output)
            # agent-browser returns {success, data, error} wrapper
            if isinstance(parsed, dict) and "data" in parsed:
                return parsed["data"]
            return parsed
        except json.JSONDecodeError:
            # Sometimes output includes non-JSON lines
            for line in output.split('\n'):
                if line.strip().startswith('{') or line.strip().startswith('['):
                    try:
                        parsed = json.loads(line)
                        if isinstance(parsed, dict) and "data" in parsed:
                            return parsed["data"]
                        return parsed
                    except:
                        continue
            return output
    
    def crawl(
        self, 
        url: str, 
        download_images: bool = False,  # Not supported in AB version
        output_dir: Optional[str] = None,
        wait_time: int = 10
    ) -> ArticleContent:
        """
        Crawl a WeChat article using agent-browser.
        
        Args:
            url: WeChat article URL
            download_images: Not fully supported (extracts URLs only)
            output_dir: Ignored in agent-browser version
            wait_time: Seconds to wait for page load
            
        Returns:
            ArticleContent object
        """
        if not self._is_valid_weixin_url(url):
            raise ValueError(f"Invalid WeChat article URL: {url}")
        
        article = ArticleContent(url=url)
        
        try:
            logger.info(f"Crawling with agent-browser: {url}")
            
            # Load saved browser state if available (helps bypass anti-bot)
            if BROWSER_STATE_FILE and not self._state_loaded:
                if os.path.exists(BROWSER_STATE_FILE):
                    logger.info(f"Loading browser state from {BROWSER_STATE_FILE}")
                    self._run_cmd("state", "load", BROWSER_STATE_FILE)
                    self._state_loaded = True
            
            # Navigate to page
            success, output = self._run_cmd("open", url)
            if not success:
                raise RuntimeError(f"Failed to open URL: {output}")
            
            # Wait for content to load
            success, _ = self._run_cmd("wait", str(wait_time * 1000))
            
            # Wait for content element
            success, _ = self._run_cmd("wait", "#js_content", timeout=wait_time + 10)
            
            # Check for anti-bot verification page
            page_text = self._extract_text("body")
            if "环境异常" in page_text or "完成验证" in page_text:
                raise RuntimeError(
                    "WeChat anti-bot verification detected. "
                    "Try: 1) Use BROWSER_STATE_FILE with saved login state, "
                    "2) Use residential proxy, "
                    "3) Wait and retry later"
                )
            
            # Extract title
            article.title = self._extract_text("h1.rich_media_title")
            if not article.title:
                article.title = self._extract_text("#activity-name")
            
            # Extract author/account
            article.account_name = self._extract_text("#js_name")
            article.author = self._extract_text(".rich_media_meta_text")
            
            # Extract publish date
            article.publish_date = self._extract_text("#publish_time")
            
            # Extract content
            article.content_html = self._extract_html("#js_content")
            article.content_text = self._extract_text("#js_content")
            article.word_count = len(article.content_text)
            
            # Extract image URLs (no download in AB version)
            article.images = self._extract_image_urls()
            
            logger.info(f"Successfully crawled: {article.title}")
            return article
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            raise
    
    def _is_valid_weixin_url(self, url: str) -> bool:
        """Check if URL is valid WeChat article URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc in ['mp.weixin.qq.com', 'weixin.qq.com']
    
    def _extract_text(self, selector: str) -> str:
        """Extract text content using CSS selector."""
        success, output = self._run_cmd("get", "text", selector)
        if success:
            result = self._parse_json(output)
            if isinstance(result, dict) and "text" in result:
                return result["text"].strip()
            elif isinstance(result, str):
                return result.strip()
        return ""
    
    def _extract_html(self, selector: str) -> str:
        """Extract HTML content using CSS selector."""
        success, output = self._run_cmd("get", "html", selector)
        if success:
            result = self._parse_json(output)
            if isinstance(result, dict) and "html" in result:
                return result["html"]
            elif isinstance(result, str):
                return result
        return ""
    
    def _extract_image_urls(self) -> List[Dict[str, str]]:
        """Extract image URLs from page."""
        images = []
        
        # Get count of images
        success, output = self._run_cmd("get", "count", "#js_content img")
        if not success:
            return images
        
        result = self._parse_json(output)
        count = 0
        if isinstance(result, dict) and "count" in result:
            count = result["count"]
        elif isinstance(result, int):
            count = result
        
        # Extract each image src
        for i in range(min(count, 20)):  # Limit to 20 images
            selector = f"#js_content img:nth-child({i+1})"
            success, output = self._run_cmd("get", "attr", selector, "data-src")
            if success:
                result = self._parse_json(output)
                src = ""
                if isinstance(result, dict) and "value" in result:
                    src = result["value"]
                elif isinstance(result, str):
                    src = result
                
                if src and not src.startswith("data:"):
                    images.append({
                        "index": i,
                        "url": src,
                        "alt": "",
                    })
        
        return images
    
    def analyze_article(self, article: ArticleContent) -> Dict[str, Any]:
        """Analyze article content for statistics."""
        analysis = {
            "word_count": article.word_count,
            "char_count": len(article.content_text),
            "image_count": len(article.images),
            "paragraph_count": 0,
            "estimated_read_time_minutes": 0,
            "key_phrases": [],
        }
        
        # Count paragraphs
        if article.content_html:
            analysis["paragraph_count"] = len(
                re.findall(r'<p[^>]*>.*?</p>', article.content_html, re.DOTALL)
            )
        
        # Estimate read time
        analysis["estimated_read_time_minutes"] = round(
            article.word_count / self.READING_SPEED_CPM, 1
        )
        
        # Extract key phrases (bold text)
        if article.content_html:
            strong_matches = re.findall(
                r'<strong[^>]*>(.*?)</strong>', 
                article.content_html, 
                re.DOTALL
            )
            key_phrases = []
            for match in strong_matches:
                clean = re.sub(r'<[^>]+>', '', match).strip()
                if clean and len(clean) < self.MAX_KEY_PHRASE_LENGTH:
                    key_phrases.append(clean)
            analysis["key_phrases"] = key_phrases[:10]
        
        return analysis
    
    def summarize_article(self, article: ArticleContent) -> Dict[str, Any]:
        """Generate brief summary of article."""
        return {
            "title": article.title,
            "account_name": article.account_name,
            "author": article.author,
            "publish_date": article.publish_date,
            "word_count": article.word_count,
            "image_count": len(article.images),
            "first_300_chars": article.content_text[:300] + "..." if len(article.content_text) > 300 else article.content_text,
            "url": article.url,
        }
    
    def close(self):
        """Close browser session."""
        try:
            self._run_cmd("close", timeout=10)
            logger.info("Browser session closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        
        with self._lock:
            WeixinSpiderAB._instance = None


# Convenience functions
def crawl_weixin_article_ab(
    url: str,
    download_images: bool = False,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Crawl WeChat article using agent-browser."""
    spider = WeixinSpiderAB.get_instance()
    article = spider.crawl(url, download_images, output_dir)
    return article.to_dict()


def analyze_weixin_article_ab(url: str) -> Dict[str, Any]:
    """Crawl and analyze WeChat article."""
    spider = WeixinSpiderAB.get_instance()
    article = spider.crawl(url, download_images=False)
    analysis = spider.analyze_article(article)
    return {
        "content": article.to_dict(),
        "analysis": analysis,
    }


def summarize_weixin_article_ab(url: str) -> Dict[str, Any]:
    """Get brief summary of WeChat article."""
    spider = WeixinSpiderAB.get_instance()
    article = spider.crawl(url, download_images=False)
    return spider.summarize_article(article)


if __name__ == "__main__":
    # Test with sample URL
    test_url = input("Enter WeChat article URL: ").strip()
    if test_url:
        result = crawl_weixin_article_ab(test_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
