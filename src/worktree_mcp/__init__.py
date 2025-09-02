"""
iTerm2 工作树 MCP 服务器

一个为 Claude Code 提供 git 工作树管理自动化和 iTerm2 集成的模型上下文协议 (MCP) 服务器。
"""

__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .server import main

__all__ = ["main"]