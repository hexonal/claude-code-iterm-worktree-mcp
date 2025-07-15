# iTerm2 Worktree MCP Server

A Model Context Protocol (MCP) server that automates git worktree management with iTerm2 integration for Claude Code.

https://github.com/user-attachments/assets/16188878-8fe8-450c-b2a3-cfd617d74f43

## Installation

Add to Claude Code:

```bash
claude mcp add -s user worktree -- python3 path/to/worktree_mcp_server.py
```

## Features

### Core Worktree Management
- **Create Worktree**: Creates a new git worktree with a feature branch and opens it in a new iTerm2 tab
- **Close Worktree**: Safely closes worktrees after verifying they're clean and pushed
- **Open Worktree**: Opens an existing worktree in a new iTerm2 tab (with force option to override if already open)

### Navigation & Discovery  
- **Active Worktrees**: Lists all git worktrees and shows which iTerm2 tabs they're running in
- **Switch to Worktree**: Quickly switch to a worktree's iTerm2 tab by name or specific tab ID

### Smart Tab Detection
- **Dynamic Discovery**: No metadata files - finds tabs by analyzing their working directories in real-time
- **Multi-Tab Support**: Shows all tabs running the same worktree across different windows
- **Window Context**: Identifies which tabs are in the current window with `thisWindow` flag

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `createWorktree` | Create new worktree + branch, open in iTerm2 tab | `feature_name`, `branch_name`, `worktree_folder`, `description`, `start_claude?` |
| `closeWorktree` | Validate, close, and cleanup worktree | `worktree_name` |
| `activeWorktrees` | List all worktrees and their iTerm2 tabs | None |
| `switchToWorktree` | Switch to worktree's iTerm2 tab | `worktree_name`, `tab_id?` |
| `openWorktree` | Open existing worktree in new tab | `worktree_name`, `force?` |

## Workflow

1. **Create**: `createWorktree` - Specify feature name, branch name, and worktree folder - automatically creates the worktree and switches to a new iTerm2 tab
2. **Navigate**: `switchToWorktree` or `openWorktree` - Seamlessly move between worktrees
3. **Monitor**: `activeWorktrees` - See all worktrees and their active tabs  
4. **Develop**: Work in isolated worktree environments with full iTerm2 integration
5. **Close**: `closeWorktree` - Verify changes are committed and pushed, then safely remove the worktree

Perfect for feature development with isolated git environments and seamless iTerm2 integration.
