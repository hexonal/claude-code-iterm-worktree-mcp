# 使用示例 / Usage Examples

🌐 **Language / 语言**: [English](#english) | [中文](#中文)

## English

### Traditional Workflow Example

```bash
# 1. Create a feature worktree
createWorktree(
    feature_name="user-authentication",
    branch_name="feature/user-auth", 
    worktree_folder="myapp-feat-user-auth",
    description="Implement JWT-based user authentication system",
    start_claude=true
)

# 2. Switch between worktrees  
switchToWorktree(worktree_name="myapp-feat-user-auth")

# 3. Monitor all active worktrees
activeWorktrees()

# 4. Close when done
closeWorktree(worktree_name="myapp-feat-user-auth")
```

### 🆕 New: Intelligent Coordination Workflow

```bash
# Main Session: Create and delegate
createWorktree(
    feature_name="payment-integration",
    branch_name="feature/payment-system",
    worktree_folder="myapp-feat-payment", 
    description="Integrate Stripe payment processing with error handling",
    start_claude=true  # Launches sub-session Claude
)

# Sub-Session: Work independently, then notify when done
# (In the worktree tab, after completing development)
notifyTaskComplete(
    worktree_name="myapp-feat-payment",
    task_summary="Completed Stripe integration with tests and error handling",
    auto_merge=true  # Enable automatic merge analysis
)

# Main Session: Automatic response
# - Analyzes code changes and test results
# - Executes smart merge if quality gates pass
# - Automatically closes worktree and cleans up
```

### Manual Analysis Workflow

```bash
# Analyze changes before merging
analyzeWorktreeChanges(worktree_name="myapp-feat-payment")

# Returns detailed analysis:
# - Code change statistics
# - Test results
# - Code quality checks  
# - Merge recommendation
```

### Session Management Workflow

```bash
# Get current Claude session ID for configuration
getCurrentSessionId()

# Returns session information:
# - session_id: Current session identifier
# - source: How the session ID was detected
# - success: Whether detection was successful
# - message: Status description

# Use session ID to enable session sharing
# (Set WORKTREE_MCP_CLAUDE_SESSION_ID environment variable)
```

---

## 中文

### 传统工作流程示例

```bash
# 1. 创建功能工作树
createWorktree(
    feature_name="用户认证",
    branch_name="feature/user-auth",
    worktree_folder="myapp-feat-user-auth", 
    description="实现基于JWT的用户认证系统",
    start_claude=true
)

# 2. 在工作树间切换
switchToWorktree(worktree_name="myapp-feat-user-auth")

# 3. 监控所有活动工作树
activeWorktrees()

# 4. 完成后关闭
closeWorktree(worktree_name="myapp-feat-user-auth")
```

### 🆕 新功能：智能协调工作流程

```bash
# 主会话：创建并分配任务
createWorktree(
    feature_name="支付集成",
    branch_name="feature/payment-system",
    worktree_folder="myapp-feat-payment",
    description="集成Stripe支付处理和错误处理机制", 
    start_claude=true  # 启动子会话Claude
)

# 子会话：独立工作，完成后通知
# （在工作树标签页中，完成开发后）
notifyTaskComplete(
    worktree_name="myapp-feat-payment",
    task_summary="完成Stripe集成，包含测试和错误处理",
    auto_merge=true  # 启用自动合并分析
)

# 主会话：自动响应
# - 分析代码变更和测试结果
# - 如果质量门禁通过则执行智能合并
# - 自动关闭工作树并清理
```

### 手动分析工作流程

```bash
# 合并前分析变更
analyzeWorktreeChanges(worktree_name="myapp-feat-payment")

# 返回详细分析：
# - 代码变更统计
# - 测试结果
# - 代码质量检查
# - 合并建议
```

### 会话管理工作流程

```bash
# 获取当前 Claude 会话 ID 用于配置
getCurrentSessionId()

# 返回会话信息：
# - session_id: 当前会话标识符
# - source: 会话 ID 检测来源
# - success: 检测是否成功
# - message: 状态描述

# 使用会话 ID 启用会话共享
# （设置 WORKTREE_MCP_CLAUDE_SESSION_ID 环境变量）
```