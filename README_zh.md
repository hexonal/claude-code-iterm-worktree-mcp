# iTerm2 工作树 MCP 服务器

🌐 **Language / 语言**: [English](README.md) | [中文](README_zh.md)

一个为 Claude Code 提供 git 工作树管理自动化和 iTerm2 集成的模型上下文协议 (MCP) 服务器。

https://github.com/user-attachments/assets/16188878-8fe8-450c-b2a3-cfd617d74f43

## 安装

### 使用 uvx（推荐）
```bash
# 确保您有 Python 3.10+
python --version

# 使用 uvx 安装
uvx --from git+https://github.com/your-username/iterm2-worktree-mcp.git worktree-mcp-server
```

### 使用 pip
```bash
# 确保 Python 3.10+
python --version

pip install git+https://github.com/your-username/iterm2-worktree-mcp.git
```

### 开发环境安装
```bash
git clone https://github.com/your-username/iterm2-worktree-mcp.git
cd iterm2-worktree-mcp

# 使用 Python 3.10+ 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -e .
```

## 配置

### Claude Code 配置

添加到您的 Claude Code MCP 配置中：

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
        "WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS": ""
      }
    }
  }
}
```

### 传统安装方式（单文件）
```bash
claude mcp add -s user worktree -- python3 path/to/worktree_mcp_server.py
```

### 环境变量配置

通过以下环境变量配置 Claude 命令行为：

| 变量 | 描述 | 默认值 | 示例 |
|----------|-------------|---------|---------|  
| `WORKTREE_MCP_CLAUDE_SKIP_PERMISSIONS` | 跳过权限提示 | `false` | `true` |
| `WORKTREE_MCP_CLAUDE_ENABLE_SESSION_SHARING` | 启用会话共享 | `true` | `true` |
| `WORKTREE_MCP_CLAUDE_SESSION_ID` | 特定Claude会话ID | None | `claude-code-123456-abc` |
| `WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS` | 额外Claude参数 | None | `--some-flag` |

```bash
# Shell环境变量导出示例
export WORKTREE_MCP_CLAUDE_SKIP_PERMISSIONS=true
export WORKTREE_MCP_CLAUDE_ENABLE_SESSION_SHARING=true
export WORKTREE_MCP_CLAUDE_SESSION_ID=your-session-id
export WORKTREE_MCP_CLAUDE_ADDITIONAL_ARGS="--some-flag"
```

这些设置会影响在新工作树会话中启动 Claude 的方式，实现主会话和子会话之间的无缝集成。

## 功能特性

### 核心工作树管理
- **创建工作树**: 创建新的 git 工作树和功能分支，并在新的 iTerm2 标签页中打开
- **关闭工作树**: 在验证工作树干净且已推送后安全关闭工作树
- **打开工作树**: 在新的 iTerm2 标签页中打开现有工作树（可强制覆盖已打开的）

### 导航与发现  
- **活动工作树**: 列出所有 git 工作树并显示它们运行在哪些 iTerm2 标签页中
- **切换到工作树**: 通过名称或特定标签页 ID 快速切换到工作树的 iTerm2 标签页

### 智能标签页检测
- **动态发现**: 无需元数据文件 - 通过实时分析工作目录查找标签页
- **多标签页支持**: 显示跨不同窗口运行同一工作树的所有标签页
- **窗口上下文**: 使用 `thisWindow` 标志识别当前窗口中的标签页

## 可用工具

| 工具 | 描述 | 参数 |
|------|-------------|------------|
| `createWorktree` | 创建新工作树+分支，在 iTerm2 标签页中打开 | `feature_name`, `branch_name`, `worktree_folder`, `description`, `start_claude?` |
| `closeWorktree` | 验证、关闭和清理工作树 | `worktree_name` |
| `activeWorktrees` | 列出所有工作树及其 iTerm2 标签页 | 无 |
| `switchToWorktree` | 切换到工作树的 iTerm2 标签页 | `worktree_name`, `tab_id?` |
| `openWorktree` | 在新标签页中打开现有工作树 | `worktree_name`, `force?` |
| `notifyTaskComplete` | 🆕 通知主会话任务完成并支持自动合并 | `worktree_name`, `task_summary`, `auto_merge?` |
| `analyzeWorktreeChanges` | 🆕 分析代码变更和合并准备情况 | `worktree_name` |
| `getCurrentSessionId` | 🆕 获取当前 Claude 会话 ID 用于 resume 功能 | 无 |

### 🆕 新功能：智能会话协调

- **跨会话通信**: 子会话可以通知主会话任务完成状态
- **自动代码分析**: 智能分析代码变更、测试和质量检查
- **自动合并能力**: 基于分析结果的智能合并决策
- **多会话工作流**: 分布式开发，集中式协调管理

## 工作流程

### 传统工作流程
1. **创建**: `createWorktree` - 指定功能名称、分支名称和工作树文件夹 - 自动创建工作树并切换到新的 iTerm2 标签页
2. **导航**: `switchToWorktree` 或 `openWorktree` - 在工作树之间无缝移动
3. **监控**: `activeWorktrees` - 查看所有工作树及其活动标签页  
4. **开发**: 在隔离的工作树环境中工作，享受完整的 iTerm2 集成
5. **关闭**: `closeWorktree` - 验证更改已提交并推送，然后安全移除工作树

### 🆕 智能协调工作流程
1. **分配**: 主会话创建工作树并启动子会话 Claude
2. **开发**: 子会话独立完成指定功能的开发工作
3. **通知**: 子会话开发完成时调用 `notifyTaskComplete`
4. **分析**: 主会话自动分析代码变更和质量状况
5. **自动合并**: 基于测试结果和代码质量的智能合并
6. **清理**: 自动执行工作树关闭和分支管理

非常适合具有 AI 驱动协调和自动化质量门禁的分布式开发。