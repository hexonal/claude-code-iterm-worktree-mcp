# iTerm2 Worktree MCP Server

🌐 **Language / 语言**: [English](README.md) | [中文](README_zh.md)

A Model Context Protocol (MCP) server that automates git worktree management with iTerm2 integration for Claude Code.

https://github.com/user-attachments/assets/16188878-8fe8-450c-b2a3-cfd617d74f43

## Installation

### Using uvx (Recommended)
```bash
# Ensure you have Python 3.10+
python --version

# Install with uvx
uvx --from git+https://github.com/your-username/iterm2-worktree-mcp.git worktree-mcp-server
```

### Using pip
```bash
# Ensure Python 3.10+
python --version

pip install git+https://github.com/your-username/iterm2-worktree-mcp.git
```

### Development Installation
```bash
git clone https://github.com/your-username/iterm2-worktree-mcp.git
cd iterm2-worktree-mcp

# Create virtual environment with Python 3.10+
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e .
```

## Configuration

### Claude Code Configuration

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "worktree": {
      "command": "uvx",
      "args": [
        "--from", 
        "git+https://github.com/your-username/iterm2-worktree-mcp.git",
        "worktree-mcp-server"
      ],
      "env": {
        "WORKTREE_MCP_CLAUDE_SKIP_PERMISSIONS": "false",
        "WORKTREE_MCP_CLAUDE_ENABLE_SESSION_SHARING": "true",
        "WORKTREE_MCP_CLAUDE_SESSION_ID": "",
        "WORKTREE_MCP_CLAUDE_MCP_CONFIG_PATH": "",
        "WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS": ""
      }
    }
  }
}
```

### Legacy Installation (Single File)
```bash
claude mcp add -s user worktree -- python3 path/to/worktree_mcp_server.py
```

### Environment Variables Configuration

Configure Claude command behavior with these environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `WORKTREE_MCP_CLAUDE_SKIP_PERMISSIONS` | Skip permission prompts | `false` | `true` |
| `WORKTREE_MCP_CLAUDE_ENABLE_SESSION_SHARING` | Enable session sharing | `true` | `true` |
| `WORKTREE_MCP_CLAUDE_SESSION_ID` | Claude session ID (auto-detected if empty) | Auto-detect | `claude-code-123456-abc` |
| `WORKTREE_MCP_CLAUDE_MCP_CONFIG_PATH` | MCP configuration file path | None | `~/.claude/mcp.json` |
| `WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS` | Additional Claude arguments | None | `--some-flag` |

```bash
# Export environment variables for shell usage
export WORKTREE_MCP_CLAUDE_SKIP_PERMISSIONS=true
export WORKTREE_MCP_CLAUDE_ENABLE_SESSION_SHARING=true
# WORKTREE_MCP_CLAUDE_SESSION_ID="" # Leave empty for auto-detection
# export WORKTREE_MCP_CLAUDE_MCP_CONFIG_PATH="~/.claude/worktree-mcp.json"
export WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS="--some-flag"
```

These settings affect how Claude is launched in new worktree sessions, enabling seamless integration between main and sub-sessions.

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
| `notifyTaskComplete` | 🆕 Notify main session of task completion with auto-merge | `worktree_name`, `task_summary`, `auto_merge?` |
| `analyzeWorktreeChanges` | 🆕 Analyze code changes and merge readiness | `worktree_name` |
| `getCurrentSessionId` | 🆕 Get current Claude session ID for resume functionality | None |

### 🆕 New: Intelligent Session Coordination

- **Cross-Session Communication**: Sub-sessions can notify main session of task completion
- **Automatic Code Analysis**: Smart analysis of code changes, tests, and quality checks
- **Auto-Merge Capability**: Intelligent merging based on analysis results
- **Multi-Session Workflow**: Distributed development with centralized coordination

## Workflow

### Traditional Workflow
1. **Create**: `createWorktree` - Specify feature name, branch name, and worktree folder - automatically creates the worktree and switches to a new iTerm2 tab
2. **Navigate**: `switchToWorktree` or `openWorktree` - Seamlessly move between worktrees
3. **Monitor**: `activeWorktrees` - See all worktrees and their active tabs  
4. **Develop**: Work in isolated worktree environments with full iTerm2 integration
5. **Close**: `closeWorktree` - Verify changes are committed and pushed, then safely remove the worktree

### 🆕 Intelligent Coordination Workflow
1. **Distribute**: Main session creates worktree and launches sub-session Claude
2. **Develop**: Sub-session works independently on assigned feature
3. **Notify**: Sub-session calls `notifyTaskComplete` when development is done
4. **Analyze**: Main session automatically analyzes code changes and quality
5. **Auto-Merge**: Smart merging based on test results and code quality
6. **Cleanup**: Automatic worktree closure and branch management

Perfect for distributed development with AI-powered coordination and automated quality gates.
