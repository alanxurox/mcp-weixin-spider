# MCP 微信公众号爬虫 🕷️

[English](README.md) | **中文**

**告别复制粘贴！用MCP让AI直接读取微信公众号文章**

一个 MCP (Model Context Protocol) 服务器，让 AI 助手能够直接抓取和分析微信公众号文章——不再需要复制粘贴！

## 解决的问题

你有没有遇到过这种场景：想让 AI 分析一篇微信公众号文章，却发现它根本无法访问？传统流程：
1. 打开微信文章
2. 手动复制全部文字
3. 粘贴到 AI 对话
4. 丢失图片和格式

**这个 MCP 服务器解决了这个问题。** 只需要给 AI 一个微信链接：
- 提取完整文章内容（文字 + HTML）
- 下载嵌入的图片
- 分析文章统计数据
- 对比多篇文章
- 批量处理竞品公众号

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/alanxurox/mcp-weixin-spider.git
cd mcp-weixin-spider
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 选择后端

| 后端 | 优点 | 缺点 |
|------|------|------|
| **agent-browser** | 轻量，无需 Chrome 驱动 | 功能较少，需安装 agent-browser |
| **selenium** | 功能完整，支持下载图片 | 较重，需要 Chrome/ChromeDriver |

通过 `CRAWLER_BACKEND` 环境变量设置：`"agentbrowser"` 或 `"selenium"`（默认）

### 3. 配置 Cursor/Claude

在 MCP 设置中添加（Cursor: 设置 → MCP，或 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "weixin_spider": {
      "command": "python",
      "args": ["/path/to/mcp-weixin-spider/src/mcp_weixin_spider/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-weixin-spider",
        "CRAWLER_BACKEND": "agentbrowser",
        "WAIT_TIME": "10"
      }
    }
  }
}
```

### 4. 在 AI 对话中使用

配置完成后，可以直接问 AI：

```
帮我分析这篇公众号文章: https://mp.weixin.qq.com/s/...
```

AI 会自动调用 MCP 工具抓取和分析文章！

## 可用工具

| 工具 | 描述 |
|------|------|
| `crawl_weixin_article` | 爬取文章内容和图片 |
| `analyze_weixin_article` | 分析文章统计数据 |
| `summarize_weixin_article` | 获取文章摘要 |
| `batch_crawl_articles` | 批量爬取多篇文章 |
| `compare_articles` | 对比分析多篇文章 |
| `load_browser_cookies` | 加载浏览器 cookies（用于验证流程） |

## 处理微信反爬虫验证

⚠️ **微信有完善的反爬虫机制：**

访问文章时可能出现"环境异常"验证页面。

### 解决方案：Cookie 认证流程

1. 使用 `cursor-ide-browser` 打开文章链接
2. 手动完成滑块验证
3. 导出浏览器 cookies
4. 调用 `load_browser_cookies` 加载 cookies
5. 重新调用 `crawl_weixin_article` 即可成功

详细流程见 `skills/weixin-auth-flow.md`

## 使用案例

### 1. 单篇文章分析
```
用户: 帮我总结这篇文章 https://mp.weixin.qq.com/s/xxx
AI: [调用 summarize_weixin_article] 这篇文章主要讲述了...
```

### 2. 竞品分析
```
用户: 对比分析这三个竞品公众号的最新文章
AI: [调用 compare_articles] 三篇文章的对比分析如下...
```

### 3. 批量内容监控
```
用户: 批量获取这10篇文章的摘要
AI: [调用 batch_crawl_articles] 已获取10篇文章...
```

## 项目结构

```
mcp-weixin-spider/
├── src/mcp_weixin_spider/
│   ├── server.py              # MCP 服务器（5个工具）
│   ├── client.py              # 交互式客户端
│   └── __init__.py
├── weixin_spider_simple.py    # Selenium 后端
├── weixin_spider_agentbrowser.py # agent-browser 后端
├── skills/
│   └── weixin-auth-flow.md    # 认证流程说明
├── configs/                   # Cursor/Claude 配置示例
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 环境变量

| 变量 | 默认值 | 描述 |
|------|--------|------|
| `CRAWLER_BACKEND` | `selenium` | 爬虫后端 (selenium/agentbrowser) |
| `DOWNLOAD_IMAGES` | `true` | 是否下载图片 |
| `WAIT_TIME` | `10` | 页面加载超时（秒） |
| `BROWSER_STATE_FILE` | - | 浏览器状态文件路径 |
| `AGENT_BROWSER_BIN` | - | agent-browser 二进制路径 |

## 限制

- **反爬虫验证**：首次访问需要完成验证
- **Cookie 有效期**：一般 24-48 小时
- **登录文章**：需要微信登录的文章暂不支持
- **动态内容**：复杂交互内容可能无法完全渲染

## 贡献

欢迎 PR！请：
1. 使用 `black` 格式化代码
2. 为新功能添加测试
3. 更新 README

## 许可

MIT

## 致谢

灵感来自 [精神抖擞王大鹏的微信文章](https://mp.weixin.qq.com/s/BpekvlYUpODK9GExn0FhoQ) 关于 MCP + 爬虫整合的分享。

基于：
- [MCP Python SDK](https://github.com/anthropics/mcp)
- [Selenium](https://www.selenium.dev/)
- [agent-browser](https://github.com/anthropics/agent-browser)
