"""
Claude 会话管理和 Session ID 检测（简化版）
"""

import os
import json
import subprocess
from typing import Optional, Dict, Any
from .models import SessionIdResponse, WorktreeConfig


class ClaudeSessionManager:
    """Claude 会话管理器 - 专注于当前 MCP 会话的精准检测"""
    
    def __init__(self):
        self.config = WorktreeConfig()
        # 在初始化时立即检测并缓存当前会话信息
        self._current_session_info = self._detect_current_session_immediately()
    
    def get_current_session_id(self) -> SessionIdResponse:
        """获取当前 Claude 会话的 session ID"""
        
        # 优先使用环境变量设置
        if self.config.claude_session_id:
            return SessionIdResponse(
                session_id=self.config.claude_session_id,
                source="environment_variable",
                success=True,
                message="从环境变量 WORKTREE_MCP_CLAUDE_SESSION_ID 获取"
            )
        
        # 使用初始化时检测到的会话信息
        if self._current_session_info:
            return SessionIdResponse(
                session_id=self._current_session_info["session_id"],
                source=self._current_session_info["source"],
                success=True,
                message=self._current_session_info["message"]
            )
        
        return SessionIdResponse(
            session_id=None,
            source="none",
            success=False,
            message="无法检测到当前 Claude 会话 ID。请设置环境变量 WORKTREE_MCP_CLAUDE_SESSION_ID"
        )
    
    def _detect_current_session_immediately(self) -> Optional[Dict[str, str]]:
        """在 MCP 服务器启动时立即检测当前会话信息 - 最准确的方法"""
        try:
            # 方法1: 直接搜索所有包含当前会话快照的进程
            result = subprocess.run(
                ["ps", "-eo", "pid,args"],
                capture_output=True,
                text=True
            )
            
            import re
            # 查找所有快照进程，优先当前会话
            snapshot_processes = []
            for line in result.stdout.split('\n'):
                if '.claude/shell-snapshots/snapshot-' in line:
                    match = re.search(r'snapshot-[^-]+-(\d+)-([a-zA-Z0-9]+)\.sh', line)
                    if match:
                        timestamp, session_suffix = match.groups()
                        session_id = f"claude-code-{timestamp}-{session_suffix}"
                        # 获取PID
                        pid_match = re.match(r'\s*(\d+)', line)
                        if pid_match:
                            pid = pid_match.group(1)
                            snapshot_processes.append({
                                "session_id": session_id,
                                "pid": pid,
                                "timestamp": timestamp,
                                "line": line.strip()
                            })
            
            if snapshot_processes:
                # 按时间戳排序，取最新的
                latest_session = max(snapshot_processes, key=lambda x: int(x["timestamp"]))
                return {
                    "session_id": latest_session["session_id"],
                    "source": "shell_snapshots_scan",
                    "message": f"从快照进程扫描获取最新会话：{latest_session['session_id']}"
                }
            
            # 方法2: 环境变量检测
            env_session = self._detect_from_environment()
            if env_session:
                return env_session
                
            return None
        except Exception as e:
            # 添加错误日志以便调试
            try:
                import logging
                logging.debug(f"Session detection failed: {e}")
            except:
                pass
            return None
    
    def _detect_from_environment(self) -> Optional[Dict[str, str]]:
        """从环境变量检测会话信息"""
        try:
            # 检查常见的Claude环境变量
            claude_vars = [
                "CLAUDE_SESSION_ID",
                "CLAUDE_CODE_SESSION",
                "MCP_SESSION_ID"
            ]
            
            for var in claude_vars:
                value = os.environ.get(var)
                if value and len(value) > 10:  # 基本长度检查
                    return {
                        "session_id": value,
                        "source": f"environment_variable_{var}",
                        "message": f"从环境变量 {var} 获取：{value}"
                    }
            
            return None
        except:
            return None
    
    def build_claude_command(self, description: str, worktree_folder: str) -> str:
        """构建增强的 Claude 命令"""
        cmd_parts = ["claude"]
        
        # 添加会话恢复支持
        if self.config.claude_enable_session_sharing:
            session_response = self.get_current_session_id()
            if session_response.success and session_response.session_id:
                cmd_parts.extend(["--resume", session_response.session_id])
        
        # 添加任务描述
        escaped_description = description.replace('"', '\\"')
        cmd_parts.append(f'"{escaped_description}"')
        
        # 添加权限跳过参数
        if self.config.claude_skip_permissions:
            cmd_parts.append("--dangerously-skip-permissions")
        
        # 添加禁用的工具列表
        disallowed_tools = [
            "mcp__worktree__createWorktree",
            "mcp__worktree__closeWorktree", 
            "mcp__worktree__activeWorktrees",
            "mcp__worktree__switchToWorktree",
            "mcp__worktree__openWorktree"
        ]
        cmd_parts.append(f"--disallowedTools {','.join(disallowed_tools)}")
        
        # 添加MCP配置文件支持
        if self.config.claude_mcp_config_path:
            cmd_parts.extend(["--mcp-config", f'"{self.config.claude_mcp_config_path}"'])
        
        # 添加额外参数
        if self.config.claude_additional_args:
            cmd_parts.append(self.config.claude_additional_args)
        
        return " ".join(cmd_parts)


class SessionIdDetector:
    """会话 ID 检测器 - 保留作为备选方案"""
    
    @staticmethod
    def detect_from_environment_context() -> Optional[str]:
        """从环境上下文检测会话信息"""
        try:
            # 检查是否在 Claude Code 环境中
            claude_env_vars = {
                "CLAUDE_CONTEXT": os.getenv("CLAUDE_CONTEXT"),
                "CLAUDE_SESSION": os.getenv("CLAUDE_SESSION"),
                "MCP_SESSION_CONTEXT": os.getenv("MCP_SESSION_CONTEXT"),
                "ANTHROPIC_SESSION_CONTEXT": os.getenv("ANTHROPIC_SESSION_CONTEXT")
            }
            
            for var_name, var_value in claude_env_vars.items():
                if var_value:
                    # 尝试解析 JSON 格式的上下文
                    try:
                        context = json.loads(var_value)
                        if isinstance(context, dict):
                            session_id = context.get("session_id") or context.get("sessionId")
                            if session_id:
                                return session_id
                    except json.JSONDecodeError:
                        # 如果不是 JSON，可能直接是 session ID
                        if len(var_value) > 5 and var_value.replace('-', '').replace('_', '').isalnum():
                            return var_value
            
            return None
        except:
            return None