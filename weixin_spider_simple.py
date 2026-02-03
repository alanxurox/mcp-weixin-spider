#!/usr/bin/env python3
"""
WeChat Article Spider - Core Crawler Logic
Uses Selenium with Chrome headless browser to crawl WeChat public account articles.

Features:
- Extracts article title, author, publish date, content (HTML and text)
- Downloads embedded images with proper naming
- Handles WeChat's dynamic content loading
- Singleton pattern for browser management
"""

import os
import re
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, urljoin

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ArticleContent:
    """Data class for article content."""
    url: str
    title: str = ""
    author: str = ""
    account_name: str = ""  # 公众号名称
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


class WeixinSpider:
    """
    Thread-safe Singleton WeChat Article Spider using Chrome headless browser.
    
    Usage:
        spider = WeixinSpider.get_instance()
        article = spider.crawl(url)
        
    Or with context manager:
        with WeixinSpider.get_instance() as spider:
            article = spider.crawl(url)
    """
    
    _instance: Optional['WeixinSpider'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __init__(self):
        """Initialize instance variables. Browser initialized lazily."""
        self._driver: Optional[webdriver.Chrome] = None
        self._initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> 'WeixinSpider':
        """
        Get thread-safe singleton instance of WeixinSpider.
        Uses double-checked locking pattern.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check inside lock
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._init_browser()
        return cls._instance
    
    def __enter__(self) -> 'WeixinSpider':
        """Context manager entry."""
        if not self._initialized:
            self._init_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - don't close for singleton, just return."""
        # For singleton, we don't close on exit to allow reuse
        return False
    
    # Configuration constants
    PAGE_LOAD_TIMEOUT = 30
    DYNAMIC_CONTENT_WAIT = 2
    MAX_KEY_PHRASE_LENGTH = 100
    READING_SPEED_CPM = 200  # Characters per minute
    
    def _init_browser(self):
        """Initialize Chrome browser with headless options."""
        if self._initialized:
            return
            
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Disable images for faster loading (optional)
        # options.add_argument("--blink-settings=imagesEnabled=false")
        
        try:
            service = Service(ChromeDriverManager().install())
            self._driver = webdriver.Chrome(service=service, options=options)
            self._driver.set_page_load_timeout(self.PAGE_LOAD_TIMEOUT)
            self._initialized = True
            logger.info("Chrome browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome browser: {e}")
            raise
    
    def crawl(
        self, 
        url: str, 
        download_images: bool = True,
        output_dir: Optional[str] = None,
        wait_time: int = 10
    ) -> ArticleContent:
        """
        Crawl a WeChat article.
        
        Args:
            url: WeChat article URL (mp.weixin.qq.com)
            download_images: Whether to download embedded images
            output_dir: Directory to save images (default: ./downloads/{article_hash}/)
            wait_time: Seconds to wait for page load
            
        Returns:
            ArticleContent object with extracted data
        """
        if not self._is_valid_weixin_url(url):
            raise ValueError(f"Invalid WeChat article URL: {url}")
        
        article = ArticleContent(url=url)
        
        try:
            logger.info(f"Crawling: {url}")
            self._driver.get(url)
            
            # Wait for content to load
            WebDriverWait(self._driver, wait_time).until(
                EC.presence_of_element_located((By.ID, "js_content"))
            )
            
            # Additional wait for dynamic content
            time.sleep(self.DYNAMIC_CONTENT_WAIT)
            
            # Extract article metadata
            article.title = self._extract_title()
            article.author = self._extract_author()
            article.account_name = self._extract_account_name()
            article.publish_date = self._extract_publish_date()
            
            # Extract content
            article.content_html = self._extract_content_html()
            article.content_text = self._extract_content_text()
            article.word_count = len(article.content_text)
            
            # Download images if requested
            if download_images:
                article.images = self._extract_and_download_images(
                    url, output_dir
                )
            else:
                article.images = self._extract_image_urls()
            
            logger.info(f"Successfully crawled: {article.title}")
            return article
            
        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            raise
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            raise
    
    def _is_valid_weixin_url(self, url: str) -> bool:
        """Check if URL is a valid WeChat article URL."""
        parsed = urlparse(url)
        return parsed.netloc in ['mp.weixin.qq.com', 'weixin.qq.com']
    
    def _extract_title(self) -> str:
        """Extract article title."""
        try:
            # Try multiple selectors
            selectors = [
                "h1.rich_media_title",
                "#activity-name",
                "h1",
            ]
            for selector in selectors:
                try:
                    elem = self._driver.find_element(By.CSS_SELECTOR, selector)
                    title = elem.text.strip()
                    if title:
                        return title
                except NoSuchElementException:
                    continue
            return ""
        except Exception as e:
            logger.warning(f"Failed to extract title: {e}")
            return ""
    
    def _extract_author(self) -> str:
        """Extract article author."""
        try:
            selectors = [
                "span.rich_media_meta.rich_media_meta_text",
                "#js_name",
                ".profile_nickname",
            ]
            for selector in selectors:
                try:
                    elem = self._driver.find_element(By.CSS_SELECTOR, selector)
                    author = elem.text.strip()
                    if author:
                        return author
                except NoSuchElementException:
                    continue
            return ""
        except Exception as e:
            logger.warning(f"Failed to extract author: {e}")
            return ""
    
    def _extract_account_name(self) -> str:
        """Extract public account name."""
        try:
            selectors = [
                "#js_name",
                ".profile_nickname",
                "a.weui-wa-hotarea",
            ]
            for selector in selectors:
                try:
                    elem = self._driver.find_element(By.CSS_SELECTOR, selector)
                    name = elem.text.strip()
                    if name:
                        return name
                except NoSuchElementException:
                    continue
            return ""
        except Exception as e:
            logger.warning(f"Failed to extract account name: {e}")
            return ""
    
    def _extract_publish_date(self) -> str:
        """Extract publish date."""
        try:
            selectors = [
                "#publish_time",
                "em.rich_media_meta.rich_media_meta_text",
                ".rich_media_meta_list em",
            ]
            for selector in selectors:
                try:
                    elem = self._driver.find_element(By.CSS_SELECTOR, selector)
                    date = elem.text.strip()
                    if date:
                        return date
                except NoSuchElementException:
                    continue
            return ""
        except Exception as e:
            logger.warning(f"Failed to extract publish date: {e}")
            return ""
    
    def _extract_content_html(self) -> str:
        """Extract article content as HTML."""
        try:
            content_elem = self._driver.find_element(By.ID, "js_content")
            return content_elem.get_attribute("innerHTML")
        except Exception as e:
            logger.warning(f"Failed to extract HTML content: {e}")
            return ""
    
    def _extract_content_text(self) -> str:
        """Extract article content as plain text."""
        try:
            content_elem = self._driver.find_element(By.ID, "js_content")
            return content_elem.text.strip()
        except Exception as e:
            logger.warning(f"Failed to extract text content: {e}")
            return ""
    
    def _extract_image_urls(self) -> List[Dict[str, str]]:
        """Extract image URLs without downloading."""
        images = []
        try:
            content_elem = self._driver.find_element(By.ID, "js_content")
            img_elements = content_elem.find_elements(By.TAG_NAME, "img")
            
            for i, img in enumerate(img_elements):
                # WeChat uses data-src for lazy loading
                src = img.get_attribute("data-src") or img.get_attribute("src")
                if src and not src.startswith("data:"):
                    images.append({
                        "index": i,
                        "url": src,
                        "alt": img.get_attribute("alt") or "",
                    })
            
            return images
        except Exception as e:
            logger.warning(f"Failed to extract image URLs: {e}")
            return images
    
    def _extract_and_download_images(
        self, 
        article_url: str,
        output_dir: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Extract and download images."""
        images = self._extract_image_urls()
        if not images:
            return images
        
        # Create output directory
        if output_dir is None:
            url_hash = hashlib.md5(article_url.encode()).hexdigest()[:8]
            output_dir = f"./downloads/{url_hash}"
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        for img in images:
            try:
                response = requests.get(img["url"], timeout=30)
                if response.status_code == 200:
                    # Determine file extension
                    content_type = response.headers.get("content-type", "")
                    if "jpeg" in content_type or "jpg" in content_type:
                        ext = ".jpg"
                    elif "png" in content_type:
                        ext = ".png"
                    elif "gif" in content_type:
                        ext = ".gif"
                    elif "webp" in content_type:
                        ext = ".webp"
                    else:
                        ext = ".jpg"  # default
                    
                    filename = f"image_{img['index']:03d}{ext}"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    
                    img["local_path"] = filepath
                    logger.debug(f"Downloaded: {filename}")
                    
            except Exception as e:
                logger.warning(f"Failed to download image {img['index']}: {e}")
        
        return images
    
    def analyze_article(self, article: ArticleContent) -> Dict[str, Any]:
        """
        Analyze article content for basic statistics.
        
        Returns dict with:
        - paragraph_count
        - image_count
        - estimated_read_time (minutes)
        - key_phrases (if any bold/highlighted text)
        """
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
        
        # Estimate read time (average Chinese characters per minute)
        analysis["estimated_read_time_minutes"] = round(
            article.word_count / self.READING_SPEED_CPM, 1
        )
        
        # Extract key phrases (bold/strong text)
        if article.content_html:
            strong_matches = re.findall(
                r'<strong[^>]*>(.*?)</strong>', 
                article.content_html, 
                re.DOTALL
            )
            # Clean HTML tags from matches
            key_phrases = []
            for match in strong_matches:
                clean = re.sub(r'<[^>]+>', '', match).strip()
                if clean and len(clean) < self.MAX_KEY_PHRASE_LENGTH:
                    key_phrases.append(clean)
            analysis["key_phrases"] = key_phrases[:10]  # Top 10
        
        return analysis
    
    def summarize_article(self, article: ArticleContent) -> Dict[str, Any]:
        """
        Generate a brief summary of the article.
        
        Returns dict with:
        - title
        - account_name
        - publish_date
        - word_count
        - first_300_chars (opening content)
        - image_count
        """
        summary = {
            "title": article.title,
            "account_name": article.account_name,
            "author": article.author,
            "publish_date": article.publish_date,
            "word_count": article.word_count,
            "image_count": len(article.images),
            "first_300_chars": article.content_text[:300] + "..." if len(article.content_text) > 300 else article.content_text,
            "url": article.url,
        }
        return summary
    
    def close(self):
        """Close the browser and reset singleton."""
        with self._lock:
            if self._driver:
                try:
                    self._driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                self._driver = None
                self._initialized = False
            WeixinSpider._instance = None
            logger.info("Browser closed")
    
    def __del__(self):
        """Cleanup on deletion - best effort, not guaranteed."""
        try:
            if self._driver:
                self._driver.quit()
        except Exception:
            pass  # Ignore errors during cleanup


# Convenience functions for direct usage
def crawl_weixin_article(
    url: str,
    download_images: bool = True,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to crawl a WeChat article.
    
    Args:
        url: WeChat article URL
        download_images: Whether to download images
        output_dir: Directory for downloaded images
        
    Returns:
        Dictionary with article content
    """
    spider = WeixinSpider.get_instance()
    article = spider.crawl(url, download_images, output_dir)
    return article.to_dict()


def analyze_weixin_article(url: str) -> Dict[str, Any]:
    """
    Crawl and analyze a WeChat article.
    
    Returns combined content and analysis.
    """
    spider = WeixinSpider.get_instance()
    article = spider.crawl(url, download_images=False)
    analysis = spider.analyze_article(article)
    
    return {
        "content": article.to_dict(),
        "analysis": analysis,
    }


def summarize_weixin_article(url: str) -> Dict[str, Any]:
    """
    Get a brief summary of a WeChat article.
    """
    spider = WeixinSpider.get_instance()
    article = spider.crawl(url, download_images=False)
    return spider.summarize_article(article)


if __name__ == "__main__":
    # Test with a sample URL
    import json
    
    test_url = input("Enter WeChat article URL: ").strip()
    if test_url:
        result = crawl_weixin_article(test_url, download_images=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
