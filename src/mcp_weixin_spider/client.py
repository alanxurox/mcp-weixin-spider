#!/usr/bin/env python3
"""
MCP Client for WeChat Spider

A standard MCP client implementation for interacting with the WeChat Spider MCP server.
This client can be used for testing the server or as a reference implementation.

Usage:
    python client.py /path/to/server.py
"""

import os
import sys
import json
import asyncio
import logging
from typing import Optional, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPWeixinClient:
    """
    MCP Client for WeChat Spider.
    
    Connects to the MCP server and provides methods to interact with
    WeChat article crawling tools.
    """
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.available_tools: list = []
    
    async def connect_to_server(self, server_script_path: str):
        """
        Connect to the MCP server.
        
        Args:
            server_script_path: Path to the server.py script
        """
        # Step 1: Configure server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env={
                **os.environ,
                "DOWNLOAD_IMAGES": "true",
                "WAIT_TIME": "10"
            }
        )
        
        logger.info(f"Connecting to server: {server_script_path}")
        
        # Step 2: Establish connection via stdio
        async with stdio_client(server_params) as (read, write):
            # Step 3: Create session
            async with ClientSession(read, write) as session:
                self.session = session
                await self._initialize_session()
                
                # Run interactive session
                await self.interactive_session()
    
    async def _initialize_session(self):
        """Initialize the session and list available tools."""
        # Initialize the connection
        await self.session.initialize()
        
        # List available tools
        tools_response = await self.session.list_tools()
        self.available_tools = tools_response.tools
        
        logger.info(f"Connected! Available tools: {[t.name for t in self.available_tools]}")
    
    async def crawl_article(
        self, 
        url: str, 
        download_images: bool = True
    ) -> dict:
        """
        Crawl a WeChat article.
        
        Args:
            url: WeChat article URL
            download_images: Whether to download images
            
        Returns:
            Dictionary with article content
        """
        result = await self.session.call_tool(
            "crawl_weixin_article",
            {
                "url": url,
                "download_images": download_images
            }
        )
        
        return json.loads(result.content[0].text)
    
    async def analyze_article(self, url: str) -> dict:
        """
        Analyze a WeChat article.
        
        Args:
            url: WeChat article URL
            
        Returns:
            Dictionary with content and analysis
        """
        result = await self.session.call_tool(
            "analyze_weixin_article",
            {"url": url}
        )
        
        return json.loads(result.content[0].text)
    
    async def summarize_article(self, url: str) -> dict:
        """
        Get article summary.
        
        Args:
            url: WeChat article URL
            
        Returns:
            Dictionary with summary
        """
        result = await self.session.call_tool(
            "summarize_weixin_article",
            {"url": url}
        )
        
        return json.loads(result.content[0].text)
    
    async def batch_crawl(self, urls: list[str]) -> dict:
        """
        Batch crawl multiple articles.
        
        Args:
            urls: List of WeChat article URLs
            
        Returns:
            Dictionary with results
        """
        result = await self.session.call_tool(
            "batch_crawl_articles",
            {"urls": urls, "download_images": False}
        )
        
        return json.loads(result.content[0].text)
    
    async def compare_articles(self, urls: list[str]) -> dict:
        """
        Compare multiple articles.
        
        Args:
            urls: List of 2-5 WeChat article URLs
            
        Returns:
            Dictionary with comparison data
        """
        result = await self.session.call_tool(
            "compare_articles",
            {"urls": urls}
        )
        
        return json.loads(result.content[0].text)
    
    async def interactive_session(self):
        """Run an interactive session with the MCP server."""
        print("\n" + "="*60)
        print("MCP WeChat Spider Client - Interactive Mode")
        print("="*60)
        print("\nAvailable commands:")
        print("  crawl <url>     - Crawl article content")
        print("  analyze <url>   - Analyze article with stats")
        print("  summary <url>   - Get brief summary")
        print("  batch           - Batch crawl (enter URLs, empty line to finish)")
        print("  compare         - Compare articles (2-5 URLs)")
        print("  tools           - List available tools")
        print("  help            - Show this help")
        print("  quit            - Exit")
        print()
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if command in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                
                elif command == "tools":
                    print("\nAvailable tools:")
                    for tool in self.available_tools:
                        print(f"  - {tool.name}: {tool.description[:60]}...")
                
                elif command == "help":
                    print("\nCommands: crawl, analyze, summary, batch, compare, tools, help, quit")
                
                elif command == "crawl":
                    if not arg:
                        print("Usage: crawl <url>")
                        continue
                    print(f"\nCrawling: {arg}")
                    result = await self.crawl_article(arg)
                    self._pretty_print(result)
                
                elif command == "analyze":
                    if not arg:
                        print("Usage: analyze <url>")
                        continue
                    print(f"\nAnalyzing: {arg}")
                    result = await self.analyze_article(arg)
                    self._pretty_print(result)
                
                elif command in ["summary", "summarize"]:
                    if not arg:
                        print("Usage: summary <url>")
                        continue
                    print(f"\nSummarizing: {arg}")
                    result = await self.summarize_article(arg)
                    self._pretty_print(result)
                
                elif command == "batch":
                    print("Enter URLs (one per line, empty line to finish):")
                    urls = []
                    while True:
                        url = input("  ").strip()
                        if not url:
                            break
                        urls.append(url)
                    
                    if urls:
                        print(f"\nBatch crawling {len(urls)} articles...")
                        result = await self.batch_crawl(urls)
                        self._pretty_print(result)
                    else:
                        print("No URLs provided")
                
                elif command == "compare":
                    print("Enter 2-5 URLs to compare (empty line to finish):")
                    urls = []
                    while len(urls) < 5:
                        url = input("  ").strip()
                        if not url:
                            break
                        urls.append(url)
                    
                    if len(urls) >= 2:
                        print(f"\nComparing {len(urls)} articles...")
                        result = await self.compare_articles(urls)
                        self._pretty_print(result)
                    else:
                        print("Need at least 2 URLs to compare")
                
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _pretty_print(self, data: dict):
        """Pretty print JSON data."""
        if "error" in data:
            print(f"\n❌ Error: {data['error']}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Default to server.py in same directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "server.py")
    else:
        server_path = sys.argv[1]
    
    if not os.path.exists(server_path):
        print(f"Error: Server script not found: {server_path}")
        sys.exit(1)
    
    client = MCPWeixinClient()
    await client.connect_to_server(server_path)


if __name__ == "__main__":
    asyncio.run(main())
