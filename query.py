#!/usr/bin/env python3
"""
Quick query script for WeChat articles.

Usage:
    python query.py <url>
    python query.py <url> --full
    python query.py <url> --analyze
"""

import sys
import json

sys.path.insert(0, '.')

from weixin_spider_agentbrowser import (
    crawl_weixin_article_ab,
    analyze_weixin_article_ab, 
    summarize_weixin_article_ab
)

def main():
    if len(sys.argv) < 2:
        print("Usage: python query.py <url> [--full|--analyze]")
        print()
        print("Examples:")
        print("  python query.py https://mp.weixin.qq.com/s/xxx")
        print("  python query.py https://mp.weixin.qq.com/s/xxx --full")
        print("  python query.py https://mp.weixin.qq.com/s/xxx --analyze")
        sys.exit(1)
    
    url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--summary"
    
    print(f"Crawling: {url}")
    print()
    
    if mode == "--full":
        result = crawl_weixin_article_ab(url)
    elif mode == "--analyze":
        result = analyze_weixin_article_ab(url)
    else:
        result = summarize_weixin_article_ab(url)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
