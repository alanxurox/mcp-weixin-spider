# MCP WeChat Spider 🕷️

**English** | [中文](README_CN.md)

**No more copy-paste! Let AI directly read WeChat articles via MCP**

An MCP (Model Context Protocol) server that enables AI assistants to directly crawl and analyze WeChat public account articles - no more copy-paste!

## Problem Solved

Have you ever wanted AI to analyze a WeChat article, only to find it can't access the content? The traditional workflow requires:
1. Open WeChat article
2. Copy all text manually
3. Paste into AI chat
4. Lose images and formatting

**This MCP server solves that.** Just give the AI a WeChat URL, and it can:
- Extract full article content (text + HTML)
- Download embedded images
- Analyze article statistics
- Compare multiple articles
- Batch process competitor accounts

## Quick Start

### 1. Install Dependencies

```bash
cd mcp-weixin
pip install -r requirements.txt
```

Or with uv:
```bash
uv pip install -r requirements.txt
```

### 2. Choose Backend

| Backend | Pros | Cons |
|---------|------|------|
| **agent-browser** | Lighter, no Chrome driver needed | Fewer features, needs agent-browser installed |
| **selenium** | Full featured, image downloads | Heavier, needs Chrome/ChromeDriver |

Set via `CRAWLER_BACKEND` env var: `"agentbrowser"` or `"selenium"` (default).

### 3. Configure in Cursor/Claude

Add to your MCP settings (Cursor: Settings → MCP, or `~/.cursor/mcp.json`):

**Option A: agent-browser backend (recommended - lighter weight)**
```json
{
  "mcpServers": {
    "weixin_spider": {
      "command": "python",
      "args": ["/path/to/mcp-weixin/src/mcp_weixin_spider/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-weixin",
        "CRAWLER_BACKEND": "agentbrowser",
        "AGENT_BROWSER_BIN": "/path/to/agent-browser/bin/agent-browser",
        "WAIT_TIME": "10"
      }
    }
  }
}
```

**Option B: Selenium backend (full features)**
```json
{
  "mcpServers": {
    "weixin_spider": {
      "command": "python",
      "args": ["/path/to/mcp-weixin/src/mcp_weixin_spider/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-weixin",
        "CRAWLER_BACKEND": "selenium",
        "DOWNLOAD_IMAGES": "true",
        "WAIT_TIME": "10"
      }
    }
  }
}
```

### 3. Use in AI Chat

Once configured, you can ask your AI:

```
帮我分析这篇公众号文章: https://mp.weixin.qq.com/s/...
```

The AI will use the MCP tools to crawl and analyze the article directly!

## Available Tools

| Tool | Description |
|------|-------------|
| `crawl_weixin_article` | 爬取文章内容和图片 - Full article extraction |
| `analyze_weixin_article` | 分析文章统计数据 - Statistics and key phrases |
| `summarize_weixin_article` | 获取文章摘要 - Quick summary |
| `batch_crawl_articles` | 批量爬取多篇文章 - Process multiple URLs |
| `compare_articles` | 对比分析多篇文章 - Competitive analysis |

## Architecture

```
mcp-weixin/
├── src/mcp_weixin_spider/
│   ├── server.py          # FastMCP server (main entry point)
│   ├── client.py           # MCP client for testing
│   └── __init__.py
├── weixin_spider_simple.py # Core crawler (Selenium/Chrome)
├── pyproject.toml          # Project config
├── requirements.txt        # Dependencies
└── README.md
```

### How It Works

```
┌─────────────┐     MCP Protocol    ┌──────────────┐
│   AI/LLM    │ ◄─────────────────► │  MCP Server  │
│ (Claude/    │    stdio transport  │  (FastMCP)   │
│  Cursor)    │                     └──────┬───────┘
└─────────────┘                            │
                                           ▼
                               ┌───────────────────┐
                               │   Chrome Driver   │
                               │   (Headless)      │
                               └─────────┬─────────┘
                                         │
                                         ▼
                               ┌───────────────────┐
                               │  mp.weixin.qq.com │
                               │   (Articles)      │
                               └───────────────────┘
```

1. **AI sends request** via MCP protocol
2. **MCP Server** receives and parses the request
3. **Chrome Driver** loads the WeChat article (headless)
4. **Content extracted** (title, author, text, images)
5. **Results returned** to AI as structured JSON

## Use Cases

### 1. Single Article Analysis
```
用户: 帮我总结这篇文章 https://mp.weixin.qq.com/s/xxx
AI: [calls summarize_weixin_article] 这篇文章主要讲述了...
```

### 2. Competitive Analysis
```
用户: 对比分析这三个竞品公众号的最新文章
AI: [calls compare_articles] 三篇文章的对比分析如下...
```

### 3. Batch Content Monitoring
```
用户: 批量获取这10篇文章的摘要
AI: [calls batch_crawl_articles] 已获取10篇文章...
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_IMAGES` | `true` | Download article images |
| `WAIT_TIME` | `10` | Page load timeout (seconds) |
| `OUTPUT_DIR` | `./downloads` | Image download directory |

### Chrome Requirements

The crawler uses Selenium with Chrome. On first run, it will automatically download the appropriate ChromeDriver via `webdriver-manager`.

For headless servers (like VPC), ensure Chrome is installed:

```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# Or install Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

## Testing

### Test with the built-in client:

```bash
python src/mcp_weixin_spider/client.py
```

This opens an interactive session where you can test all tools.

### Test the crawler directly:

```bash
python weixin_spider_simple.py
# Enter a WeChat article URL when prompted
```

## Extracted Data

Example output from `crawl_weixin_article`:

```json
{
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "告别复制粘贴！用MCP让AI直接读取微信公众号",
  "author": "精神抖擞王大鹏",
  "account_name": "精神抖擞王大鹏",
  "publish_date": "2025-07-02",
  "content_text": "你有没有遇到过这种场景...",
  "content_html": "<div>...</div>",
  "word_count": 1234,
  "images": [
    {
      "index": 0,
      "url": "https://mmbiz.qpic.cn/...",
      "local_path": "./downloads/abc123/image_000.jpg"
    }
  ],
  "crawl_timestamp": "2026-02-03T10:30:00"
}
```

## Limitations & Anti-Bot Protection

⚠️ **WeChat has sophisticated anti-bot detection:**

- **Verification pages**: WeChat shows "环境异常" (environment abnormal) for automated access
- **IP blocking**: Datacenter IPs are quickly blocked
- **Rate limiting**: Aggressive limits on request frequency

### Workarounds

**1. Use saved browser state (recommended):**
```bash
# Login manually in headed mode first
agent-browser --headed open https://mp.weixin.qq.com
# Complete any verification, then save state
agent-browser state save weixin-auth.json

# Later, load saved state
agent-browser state load weixin-auth.json
```

**2. Use residential proxy:**
```bash
agent-browser --proxy http://residential-proxy:port open <url>
```

**3. Rate limiting best practices:**
- Wait 10-30 seconds between requests
- Limit to 10-20 articles per hour
- Use random delays

### Other Limitations

- **Login required**: Some articles require WeChat login
- **Dynamic content**: Complex interactive content may not fully render
- **Image expiry**: Downloaded images are point-in-time snapshots

### References

- [WeChat Scraping Guide](https://scrapingrobot.com/blog/wechat-scraping/) - Residential proxies recommended
- [Anti-Bot Bypass Methods](https://scrapeops.io/web-scraping-playbook/how-to-bypass-antibots/)

## Contributing

PRs welcome! Please:
1. Use `black` for formatting
2. Add tests for new features
3. Update README for API changes

## License

MIT

## Credits

Inspired by [精神抖擞王大鹏's WeChat article](https://mp.weixin.qq.com/s/...) on MCP + crawler integration.

Built with:
- [MCP Python SDK](https://github.com/anthropics/mcp)
- [Selenium](https://www.selenium.dev/)
- [FastMCP](https://github.com/anthropics/mcp)
