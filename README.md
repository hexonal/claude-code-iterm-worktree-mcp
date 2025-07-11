# iTerm2 Worktree MCP Server

A Model Context Protocol (MCP) server that automates git worktree management with iTerm2 integration for Claude Code.

## Installation

Add to Claude Code:

```bash
claude mcp add -s user worktree -- python3 path/to/worktree_mcp_server.py
```

## Features

- **Create Worktree**: Creates a new git worktree with a feature branch and opens it in a new iTerm2 tab
- **Close Worktree**: Safely closes worktrees after verifying they're clean and pushed
- **List Active**: Shows all currently managed worktrees

## Workflow

1. **Create**: Specify feature name, branch name, and worktree folder - automatically creates the worktree and switches to a new iTerm2 tab
2. **Develop**: Work in the isolated worktree environment 
3. **Close**: Verify changes are committed and pushed, then safely remove the worktree

Perfect for feature development with isolated git environments and seamless iTerm2 integration.