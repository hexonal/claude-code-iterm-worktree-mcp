"""
工作树 MCP 服务器的数据模型
"""

import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class CreateWorktreeRequest(BaseModel):
    """创建工作树请求模型"""
    feature_name: str = Field(..., description="要开发的功能名称 (例如: 'add-auth')")
    branch_name: str = Field(..., description="要使用的分支名称 (例如: 'feature/add-auth')")
    worktree_folder: str = Field(..., description="工作树文件夹名称 (例如: 'project-name-feat-add-auth')")
    description: str = Field(..., description="要执行的任务描述")
    start_claude: bool = Field(
        default=False, 
        description="是否自动使用任务描述启动Claude (默认: false)。仅当您希望Claude使用特定命令启动时才设置为true。"
    )
    open_location: Literal["new_tab", "new_window", "new_pane_right", "new_pane_below"] = Field(
        default="new_tab",
        description="工作树打开位置 (默认: new_tab)。选项: new_tab (新标签页), new_window (新窗口), new_pane_right (垂直分割,右侧新窗格), new_pane_below (水平分割,下方新窗格)"
    )
    switch_back: bool = Field(
        default=False,
        description="打开工作树后是否切换回原标签页/窗口 (默认: false)。仅适用于new_tab和new_window位置。"
    )


class CloseWorktreeRequest(BaseModel):
    """关闭工作树请求模型"""
    worktree_name: str = Field(..., description="要关闭的工作树文件夹名称")


class SwitchToWorktreeRequest(BaseModel):
    """切换到工作树请求模型"""
    worktree_name: str = Field(..., description="要切换到的工作树文件夹名称")
    tab_id: Optional[str] = Field(
        default=None, 
        description="可选的特定标签页ID。如果未提供，将通过工作树路径查找标签页"
    )


class OpenWorktreeRequest(BaseModel):
    """打开工作树请求模型"""
    worktree_name: str = Field(..., description="要打开的工作树文件夹名称")
    force: bool = Field(
        default=False,
        description="即使工作树已在其他地方打开也强制在新标签页中打开 (默认: false)"
    )
    open_location: Literal["new_tab", "new_window", "new_pane_right", "new_pane_below"] = Field(
        default="new_tab",
        description="工作树打开位置 (默认: new_tab)。选项: new_tab (新标签页), new_window (新窗口), new_pane_right (垂直分割,右侧新窗格), new_pane_below (水平分割,下方新窗格)"
    )
    switch_back: bool = Field(
        default=False,
        description="打开工作树后是否切换回原标签页/窗口 (默认: false)。仅适用于new_tab和new_window位置。"
    )


class NotifyCompleteRequest(BaseModel):
    """任务完成通知请求模型"""
    worktree_name: str = Field(..., description="完成任务的工作树文件夹名称")
    task_summary: str = Field(..., description="任务完成摘要")
    auto_merge: bool = Field(default=True, description="是否自动尝试合并 (默认: true)")


class WorktreeStatus(BaseModel):
    """工作树状态模型"""
    folder: str = Field(..., description="工作树文件夹名称")
    branch: str = Field(..., description="分支名称")
    path: str = Field(..., description="工作树路径")
    status: Literal["active", "developing", "ready", "merged"] = Field(..., description="工作树状态")
    tabs: list[dict] = Field(default_factory=list, description="关联的iTerm2标签页信息")
    creator_session_id: Optional[str] = Field(default=None, description="创建此工作树的主会话ID")


class TabInfo(BaseModel):
    """标签页信息模型"""
    tab_id: str = Field(..., description="标签页ID")
    window_id: str = Field(..., description="窗口ID") 
    this_window: bool = Field(..., description="是否在当前窗口")
    exists: bool = Field(..., description="标签页是否存在")


class WorktreeConfig(BaseSettings):
    """工作树 MCP 服务器配置"""
    claude_skip_permissions: bool = Field(
        default=False,
        description="是否跳过 Claude 权限检查 (对应 --dangerously-skip-permissions)"
    )
    claude_enable_session_sharing: bool = Field(
        default=False,
        description="是否启用会话共享 (使用 --resume 参数)"
    )
    claude_session_id: Optional[str] = Field(
        default=None,
        description="当前 Claude 会话 ID (用于 --resume)"
    )
    claude_additional_args: str = Field(
        default="",
        description="Claude 命令的额外参数"
    )
    claude_mcp_config_path: Optional[str] = Field(
        default=None,
        description="MCP 配置文件路径 (用于 --mcp-config 参数)"
    )
    
    class Config:
        env_prefix = "WORKTREE_MCP_"
        case_sensitive = False


class SessionIdResponse(BaseModel):
    """会话 ID 响应模型"""
    session_id: Optional[str] = Field(..., description="当前会话 ID")
    source: str = Field(..., description="ID 来源方式")
    success: bool = Field(..., description="是否成功获取")
    message: str = Field(..., description="状态消息")


class WorktreeSessionMapping(BaseModel):
    """工作树会话映射模型"""
    worktree_name: str = Field(..., description="工作树名称")
    creator_session_id: str = Field(..., description="创建此工作树的主会话ID")
    created_at: str = Field(..., description="创建时间戳")
    creator_tab_id: Optional[str] = Field(default=None, description="创建会话的iTerm标签页ID")
    creator_working_dir: str = Field(..., description="创建会话的工作目录")