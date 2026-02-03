#!/usr/bin/env python3
"""
MCP Server for WeChat Article Spider

This server exposes WeChat article crawling capabilities as MCP tools,
allowing AI assistants to directly access WeChat public account articles.

Tools provided:
- crawl_weixin_article: Crawl article content and images
- analyze_weixin_article: Analyze article with statistics
- summarize_weixin_article: Get brief article summary

Usage:
    python server.py
    
Configure in Cursor/Claude:
    {
        "mcpServers": {
            "weixin_spider": {
                "command": "python",
                "args": ["/path/to/server.py"],
                "env": {
                    "DOWNLOAD_IMAGES": "true",
                    "WAIT_TIME": "10"
                }
            }
        }
    }
"""

import os
import sys
import re
import json
import logging
from typing import Optional

# Add parent directory to PYTHONPATH for weixin_spider_simple import
# This should be set in MCP config: "PYTHONPATH": "/path/to/mcp-weixin"
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP application
app = FastMCP("mcp-weixin-spider")

# Environment configuration
DOWNLOAD_IMAGES = os.getenv("DOWNLOAD_IMAGES", "true").lower() == "true"
WAIT_TIME = int(os.getenv("WAIT_TIME", "10"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./downloads")


def sanitize_path(name: str) -> str:
    """
    Sanitize path component to prevent directory traversal attacks.
    Removes path separators and dangerous characters.
    """
    # Remove path separators and parent directory references
    sanitized = re.sub(r'[./\\]', '_', name)
    # Remove any remaining dangerous characters
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', sanitized)
    # Limit length
    return sanitized[:100] if sanitized else "unnamed"


def get_spider():
    """Lazy import and get spider instance."""
    from weixin_spider_simple import WeixinSpider
    return WeixinSpider.get_instance()


@app.tool()
def crawl_weixin_article(
    url: str, 
    download_images: bool = True, 
    custom_filename: Optional[str] = None
) -> str:
    """
    爬取微信公众号文章内容和图片。
    
    Crawl a WeChat public account article, extracting title, content, 
    author, publish date, and optionally downloading embedded images.
    
    Args:
        url: 微信公众号文章链接 (WeChat article URL, must be mp.weixin.qq.com)
        download_images: 是否下载文章中的图片 (Whether to download images, default True)
        custom_filename: 自定义输出目录名 (Custom output directory name)
        
    Returns:
        JSON string with article content including:
        - title: 文章标题
        - author: 作者
        - account_name: 公众号名称
        - publish_date: 发布日期
        - content_text: 文章纯文本内容
        - content_html: 文章HTML内容
        - images: 图片列表 (with URLs and local paths if downloaded)
        - word_count: 字数统计
        
    Example:
        crawl_weixin_article("https://mp.weixin.qq.com/s/...")
    """
    try:
        spider = get_spider()
        
        # Determine output directory (sanitize to prevent path traversal)
        output_dir = None
        if download_images and custom_filename:
            safe_filename = sanitize_path(custom_filename)
            output_dir = os.path.join(OUTPUT_DIR, safe_filename)
        
        article = spider.crawl(
            url=url,
            download_images=download_images and DOWNLOAD_IMAGES,
            output_dir=output_dir,
            wait_time=WAIT_TIME
        )
        
        result = article.to_dict()
        logger.info(f"Successfully crawled: {result.get('title', 'Unknown')}")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except ValueError as e:
        error_msg = {"error": str(e), "type": "ValueError"}
        return json.dumps(error_msg, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error crawling article: {e}")
        error_msg = {"error": str(e), "type": type(e).__name__}
        return json.dumps(error_msg, ensure_ascii=False)


@app.tool()
def analyze_weixin_article(url: str) -> str:
    """
    爬取并分析微信公众号文章，返回统计数据。
    
    Crawl and analyze a WeChat article, returning statistics such as
    word count, paragraph count, reading time estimate, and key phrases.
    
    Args:
        url: 微信公众号文章链接 (WeChat article URL)
        
    Returns:
        JSON string with:
        - content: 文章内容 (article content)
        - analysis: 分析结果 (analysis results)
            - word_count: 字数
            - char_count: 字符数
            - paragraph_count: 段落数
            - image_count: 图片数量
            - estimated_read_time_minutes: 预计阅读时间（分钟）
            - key_phrases: 关键词/强调内容
            
    Example:
        analyze_weixin_article("https://mp.weixin.qq.com/s/...")
    """
    try:
        spider = get_spider()
        
        # Crawl without downloading images for faster analysis
        article = spider.crawl(
            url=url,
            download_images=False,
            wait_time=WAIT_TIME
        )
        
        analysis = spider.analyze_article(article)
        
        result = {
            "content": article.to_dict(),
            "analysis": analysis
        }
        
        logger.info(f"Analyzed article: {article.title}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error analyzing article: {e}")
        error_msg = {"error": str(e), "type": type(e).__name__}
        return json.dumps(error_msg, ensure_ascii=False)


@app.tool()
def summarize_weixin_article(url: str) -> str:
    """
    获取微信公众号文章的简要摘要。
    
    Get a brief summary of a WeChat article including title, author,
    publish date, word count, and opening content preview.
    
    Args:
        url: 微信公众号文章链接 (WeChat article URL)
        
    Returns:
        JSON string with summary:
        - title: 文章标题
        - account_name: 公众号名称
        - author: 作者
        - publish_date: 发布日期
        - word_count: 字数
        - image_count: 图片数量
        - first_300_chars: 开头300字预览
        - url: 原文链接
        
    Example:
        summarize_weixin_article("https://mp.weixin.qq.com/s/...")
    """
    try:
        spider = get_spider()
        
        article = spider.crawl(
            url=url,
            download_images=False,
            wait_time=WAIT_TIME
        )
        
        summary = spider.summarize_article(article)
        
        logger.info(f"Summarized article: {article.title}")
        return json.dumps(summary, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error summarizing article: {e}")
        error_msg = {"error": str(e), "type": type(e).__name__}
        return json.dumps(error_msg, ensure_ascii=False)


@app.tool()
def batch_crawl_articles(urls: list[str], download_images: bool = False) -> str:
    """
    批量爬取多篇微信公众号文章。
    
    Batch crawl multiple WeChat articles. Returns summaries for each article
    to keep response size manageable.
    
    Args:
        urls: 微信文章链接列表 (List of WeChat article URLs)
        download_images: 是否下载图片 (Whether to download images, default False for batch)
        
    Returns:
        JSON string with list of article summaries and any errors.
        
    Example:
        batch_crawl_articles([
            "https://mp.weixin.qq.com/s/article1",
            "https://mp.weixin.qq.com/s/article2"
        ])
    """
    try:
        spider = get_spider()
        results = []
        errors = []
        
        for i, url in enumerate(urls):
            try:
                logger.info(f"Crawling article {i+1}/{len(urls)}: {url[:50]}...")
                article = spider.crawl(
                    url=url,
                    download_images=download_images,
                    wait_time=WAIT_TIME
                )
                summary = spider.summarize_article(article)
                results.append(summary)
                
            except Exception as e:
                errors.append({
                    "url": url,
                    "error": str(e)
                })
                logger.warning(f"Failed to crawl {url}: {e}")
        
        output = {
            "total": len(urls),
            "success": len(results),
            "failed": len(errors),
            "articles": results,
            "errors": errors if errors else None
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error in batch crawl: {e}")
        error_msg = {"error": str(e), "type": type(e).__name__}
        return json.dumps(error_msg, ensure_ascii=False)


@app.tool()
def compare_articles(urls: list[str]) -> str:
    """
    对比分析多篇微信公众号文章。
    
    Compare multiple WeChat articles, showing statistics side by side.
    Useful for competitive analysis of public accounts.
    
    Args:
        urls: 微信文章链接列表 (List of 2-5 WeChat article URLs to compare)
        
    Returns:
        JSON string with comparison data:
        - articles: List of article summaries
        - comparison: Side-by-side stats (word count, image count, read time)
        
    Example:
        compare_articles([
            "https://mp.weixin.qq.com/s/competitor1_article",
            "https://mp.weixin.qq.com/s/competitor2_article"
        ])
    """
    try:
        if len(urls) < 2:
            return json.dumps({"error": "Need at least 2 URLs to compare"})
        if len(urls) > 5:
            return json.dumps({"error": "Maximum 5 URLs for comparison"})
        
        spider = get_spider()
        articles_data = []
        
        for url in urls:
            try:
                article = spider.crawl(url, download_images=False, wait_time=WAIT_TIME)
                analysis = spider.analyze_article(article)
                summary = spider.summarize_article(article)
                
                articles_data.append({
                    "summary": summary,
                    "analysis": analysis
                })
            except Exception as e:
                articles_data.append({
                    "url": url,
                    "error": str(e)
                })
        
        # Build comparison table
        comparison = {
            "by_word_count": sorted(
                [a for a in articles_data if "summary" in a],
                key=lambda x: x["analysis"]["word_count"],
                reverse=True
            ),
            "by_image_count": sorted(
                [a for a in articles_data if "summary" in a],
                key=lambda x: x["analysis"]["image_count"],
                reverse=True
            ),
            "stats": {
                "total_articles": len(urls),
                "successfully_analyzed": len([a for a in articles_data if "summary" in a]),
                "avg_word_count": sum(
                    a["analysis"]["word_count"] 
                    for a in articles_data if "analysis" in a
                ) / max(len([a for a in articles_data if "analysis" in a]), 1),
            }
        }
        
        result = {
            "articles": articles_data,
            "comparison": comparison
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Error comparing articles: {e}")
        error_msg = {"error": str(e), "type": type(e).__name__}
        return json.dumps(error_msg, ensure_ascii=False)


def main():
    """Run the MCP server."""
    logger.info("Starting MCP WeChat Spider Server...")
    logger.info(f"Config: DOWNLOAD_IMAGES={DOWNLOAD_IMAGES}, WAIT_TIME={WAIT_TIME}s")
    app.run()


if __name__ == "__main__":
    main()
