"""
MCP WeChat Spider - AI-powered WeChat article crawling via MCP protocol.

This package provides an MCP server that allows AI assistants to directly
access WeChat public account articles without copy-paste.

Components:
- server: FastMCP server with crawling tools
- client: MCP client for testing and standalone usage
"""

from .server import app

__version__ = "0.1.0"
__all__ = ["app"]
