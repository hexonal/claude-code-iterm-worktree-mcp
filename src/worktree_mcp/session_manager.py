"""
Claude 会话管理器 - 简化版本，仅使用环境变量
"""

import os
from typing import Optional
from .models import SessionIdResponse, WorktreeConfig


class ClaudeSessionManager:
    """Claude 会话管理器 - 仅通过环境变量配置"""
    
    def __init__(self):
        self.config = WorktreeConfig()
    
    def get_current_session_id(self) -> SessionIdResponse:
        """获取当前 Claude 会话的 session ID"""
        
        # 简单检查：如果环境变量设置了且非空，就使用
        if self.config.claude_session_id and self.config.claude_session_id.strip():
            return SessionIdResponse(
                session_id=self.config.claude_session_id.strip(),
                source="environment_variable",
                success=True,
                message="从环境变量 WORKTREE_MCP_CLAUDE_SESSION_ID 获取"
            )
        
        # 没有设置或为空，直接返回失败
        return SessionIdResponse(
            session_id=None,
            source="none",
            success=False,
            message="未设置会话ID。请在环境变量 WORKTREE_MCP_CLAUDE_SESSION_ID 中配置"
        )
    
    def build_claude_command(self, description: str, worktree_folder: str) -> str:
        """构建增强的 Claude 命令"""
        cmd_parts = ["claude"]
        
        # 添加权限跳过参数 (提前放置)
        if self.config.claude_skip_permissions:
            cmd_parts.append("--dangerously-skip-permissions")
        
        # 添加会话恢复支持 (放在权限参数后面)
        if self.config.claude_enable_session_sharing:
            session_response = self.get_current_session_id()
            if session_response.success and session_response.session_id:
                cmd_parts.extend(["-r", session_response.session_id])
        
        # 添加MCP配置文件支持 (提前放置)
        if self.config.claude_mcp_config_path:
            cmd_parts.extend(["--mcp-config", self.config.claude_mcp_config_path])
        
        # 添加任务描述
        escaped_description = description.replace('"', '\\"')
        cmd_parts.append(f'"{escaped_description}"')
        
        # 添加禁用的工具列表
        disallowed_tools = [
            "mcp__worktree__createWorktree",
            "mcp__worktree__closeWorktree", 
            "mcp__worktree__activeWorktrees",
            "mcp__worktree__switchToWorktree",
            "mcp__worktree__openWorktree"
        ]
        cmd_parts.append(f"--disallowedTools {','.join(disallowed_tools)}")
        
        # 添加额外参数
        if self.config.claude_additional_args:
            cmd_parts.append(self.config.claude_additional_args)
        
        return " ".join(cmd_parts)


class SessionIdDetector:
    """会话 ID 检测器 - 保留作为备选方案，但不再使用"""
    
    @staticmethod
    def detect_from_environment_context() -> Optional[str]:
        """从环境上下文检测会话信息 - 已弃用"""
        return None