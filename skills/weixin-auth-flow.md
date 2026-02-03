# WeChat Authentication Flow Skill

Use this skill when `weixin_spider` encounters anti-bot verification (环境异常).

## Trigger Conditions

When `crawl_weixin_article` returns error containing:
- "环境异常"
- "完成验证"  
- "WeChat anti-bot verification detected"

## Authentication Flow

### Step 1: Navigate to Article (cursor-ide-browser)

```
Call: cursor-ide-browser → browser_navigate
Args: {"url": "<blocked WeChat article URL>"}
```

### Step 2: Take Snapshot

```
Call: cursor-ide-browser → browser_snapshot
```

Look for verification elements:
- Slider/CAPTCHA in the snapshot
- "去验证" button

### Step 3: Complete Verification

**If slider verification:**
1. Find slider handle element (e.g., `@e5`)
2. Find slider track end position
3. Use `browser_drag` or `browser_click` + drag to slide

```
Call: cursor-ide-browser → browser_click
Args: {"ref": "@slider_button"}  // or "去验证" button
```

Wait for verification to complete:
```
Call: cursor-ide-browser → browser_wait  
Args: {"timeout": 5000}
```

### Step 4: Verify Success

```
Call: cursor-ide-browser → browser_snapshot
```

Check for:
- Article title (h1.rich_media_title)
- Content area (#js_content)
- NO verification elements

### Step 5: Export Cookies

```
Call: cursor-ide-browser → browser_cookies
Args: {"action": "get"}
```

Save the returned cookies JSON.

### Step 6: Load Cookies into Spider

```
Call: weixin_spider → load_browser_cookies
Args: {"cookies_json": "<cookies from step 5>"}
```

### Step 7: Retry Crawl

```
Call: weixin_spider → crawl_weixin_article
Args: {"url": "<original URL>"}
```

## Example Conversation

**User:** 帮我分析这篇文章 https://mp.weixin.qq.com/s/xxx

**AI:** [Calls crawl_weixin_article] → Gets anti-bot error

**AI:** WeChat需要验证，我来帮你完成...
[Calls browser_navigate to URL]
[Calls browser_snapshot - sees verification page]
[Calls browser_click on verification button]
[Waits and takes snapshot again]
[Calls browser_cookies to export]
[Calls load_browser_cookies with exported cookies]
[Calls crawl_weixin_article again] → Success!

**AI:** 文章已获取，以下是分析...

## Cookie Lifetime

WeChat cookies typically last 24-48 hours. If verification reappears:
1. Clear old state: `rm /tmp/weixin_spider_state.json`
2. Re-run this authentication flow

## Notes

- This flow requires `cursor-ide-browser` MCP (Mac Cursor with display)
- On headless VPC, user must complete verification on Mac first
- Cookies are stored in `/tmp/weixin_spider_state.json`
