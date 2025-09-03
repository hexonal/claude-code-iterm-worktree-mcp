"""
FastMCP 2.0 工作树服务器主模块
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict, List

from fastmcp import FastMCP
from .core import WorktreeManager
from .communication import SessionCommunicator, AutoMergeHandler
from .session_manager import ClaudeSessionManager, SessionIdDetector
from .models import (
    CreateWorktreeRequest, 
    CloseWorktreeRequest, 
    SwitchToWorktreeRequest, 
    OpenWorktreeRequest,
    NotifyCompleteRequest,
    WorktreeStatus,
    SessionIdResponse,
    WorktreeConfig
)

# 初始化 FastMCP 服务器
mcp = FastMCP("iTerm2 Worktree MCP Server")

# 全局管理器实例
worktree_manager = WorktreeManager()
session_communicator = SessionCommunicator()
auto_merge_handler = AutoMergeHandler()
claude_session_manager = ClaudeSessionManager()
config = WorktreeConfig()


@mcp.tool()
async def create_worktree(request: CreateWorktreeRequest) -> Dict[str, Any]:
    """创建git工作树并通过iTerm自动化启动开发"""
    if not worktree_manager.is_iterm:
        return {"error": "此工具只能在 iTerm 环境中使用"}
    
    # 步骤0: 验证
    valid, validation_msg = worktree_manager.validate_worktree_creation(
        request.branch_name, 
        request.worktree_folder
    )
    if not valid:
        return {"error": f"验证失败: {validation_msg}"}
    
    # 步骤1: 创建工作树
    success, worktree_msg = worktree_manager.create_worktree(
        request.branch_name, 
        request.worktree_folder
    )
    if not success:
        return {"error": worktree_msg}
    
    # 步骤2: 记录会话映射
    session_response = claude_session_manager.get_current_session_id()
    if session_response.success and session_response.session_id:
        # 获取当前标签页信息
        try:
            import iterm2
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            current_tab = app.current_window.current_tab if app.current_window else None
            current_tab_id = current_tab.tab_id if current_tab else None
        except:
            current_tab_id = None
        
        # 创建会话映射
        from .models import WorktreeSessionMapping
        mapping = WorktreeSessionMapping(
            worktree_name=request.worktree_folder,
            creator_session_id=session_response.session_id,
            created_at=str(int(time.time())),
            creator_tab_id=current_tab_id,
            creator_working_dir=os.getcwd()
        )
        
        # 保存映射关系
        worktree_manager.save_worktree_session_mapping(mapping)
        
        # 在主会话工作目录创建会话标识文件
        try:
            session_file = os.path.join(os.getcwd(), ".claude_session_id")
            with open(session_file, 'w') as f:
                f.write(session_response.session_id)
        except:
            pass  # 如果无法创建文件，继续执行
    
    # 步骤3-6: iTerm自动化
    success, iterm_msg = await worktree_manager.automate_iterm(
        request.worktree_folder,
        request.description,
        request.start_claude,
        request.open_location,
        request.switch_back
    )
    
    if not success:
        return {
            "success": True,
            "message": f"工作树创建成功，但 iTerm 自动化失败: {iterm_msg}",
            "worktree_folder": request.worktree_folder,
            "branch_name": request.branch_name
        }
    
    return {
        "success": True,
        "message": f"成功创建工作树 '{request.worktree_folder}'，分支 '{request.branch_name}' 并启动开发会话",
        "worktree_folder": request.worktree_folder,
        "branch_name": request.branch_name
    }


@mcp.tool()
async def close_worktree(request: CloseWorktreeRequest) -> Dict[str, Any]:
    """在检查工作树已清理并推送后关闭工作树"""
    if not worktree_manager.is_iterm:
        return {"error": "此工具只能在 iTerm 环境中使用"}
    
    # 步骤1: 验证工作树可以关闭
    valid, validation_msg = worktree_manager.validate_worktree_closure(request.worktree_name)
    if not valid:
        return {"error": f"无法关闭工作树: {validation_msg}"}
    
    # 步骤2: 检查分支是否有提交并获取分支名称
    has_commits, branch_name_or_error = worktree_manager.check_branch_has_commits(request.worktree_name)
    branch_to_delete = None
    if isinstance(branch_name_or_error, str) and not has_commits:
        branch_to_delete = branch_name_or_error
    
    # 步骤3: 通过工作树路径动态查找标签页ID
    parent_dir = os.path.dirname(os.getcwd())
    worktree_path = os.path.join(parent_dir, request.worktree_name)
    tab_id = await worktree_manager.find_tab_by_path(worktree_path)
    
    # 步骤4: 移除工作树
    try:
        import subprocess
        subprocess.run(
            ["git", "worktree", "remove", worktree_path],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        return {"error": f"移除工作树失败: {e.stderr}"}
    
    # 步骤5: 如果分支没有提交则删除分支
    branch_deleted = False
    if branch_to_delete:
        success, delete_msg = worktree_manager.delete_branch(branch_to_delete)
        branch_deleted = success
    
    # 步骤6: 如果iTerm标签页存在则关闭它
    tab_closed = False
    if tab_id:
        success, tab_msg = await worktree_manager.close_iterm_tab(tab_id)
        tab_closed = success
    
    # 步骤7: 清理会话映射
    worktree_manager.cleanup_session_mapping(request.worktree_name)
    
    # 构建成功消息
    message = f"成功关闭工作树 '{request.worktree_name}'"
    if branch_deleted:
        message += f" 并删除分支 '{branch_to_delete}'"
    if tab_closed:
        message += " 并关闭 iTerm 标签页"
    elif tab_id:
        message += " (iTerm 标签页无法关闭)"
    
    return {
        "success": True,
        "message": message,
        "branch_deleted": branch_deleted,
        "tab_closed": tab_closed
    }


@mcp.tool()
async def active_worktrees() -> Dict[str, Any]:
    """列出此MCP服务器管理的所有活动工作树"""
    # 获取所有git工作树
    git_worktrees = worktree_manager.get_all_git_worktrees()
    
    if not git_worktrees:
        return {"worktrees": [], "message": "没有找到 git 工作树"}
    
    # 动态检查每个工作树的标签页状态并构建响应
    enhanced_worktrees = []
    for git_worktree in git_worktrees:
        # 通过路径动态查找所有iTerm2标签页
        matching_tabs = await worktree_manager.find_all_tabs_by_path(git_worktree.path)
        
        # 获取创建会话信息
        creator_mapping = worktree_manager.get_worktree_creator_session(git_worktree.folder)
        creator_session_id = creator_mapping.creator_session_id if creator_mapping else None
        
        # 更新工作树状态，包含标签页信息和创建会话
        enhanced_worktree = WorktreeStatus(
            folder=git_worktree.folder,
            branch=git_worktree.branch,
            path=git_worktree.path,
            status=git_worktree.status,
            tabs=[tab.dict() for tab in matching_tabs],
            creator_session_id=creator_session_id
        )
        enhanced_worktrees.append(enhanced_worktree.dict())
    
    return {
        "worktrees": enhanced_worktrees,
        "total_count": len(enhanced_worktrees)
    }


@mcp.tool()
async def switch_to_worktree(request: SwitchToWorktreeRequest) -> Dict[str, Any]:
    """在iTerm2中切换到工作树标签页"""
    if not worktree_manager.is_iterm:
        return {"error": "此工具只能在 iTerm 环境中使用"}
    
    try:
        import iterm2
        connection = await iterm2.Connection.async_create()
        app = await iterm2.async_get_app(connection)
        
        target_tab_id = None
        
        if request.tab_id:
            # 提供了标签页ID - 验证其存在
            tab_exists = await worktree_manager.check_iterm_tab_exists(request.tab_id)
            if not tab_exists:
                return {"error": f"标签页 {request.tab_id} 未找到"}
            target_tab_id = request.tab_id
        else:
            # 未提供标签页ID - 通过工作树路径查找
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, request.worktree_name)
            
            # 检查工作树是否存在
            if not os.path.exists(worktree_path):
                return {"error": f"工作树 '{request.worktree_name}' 不存在于 {worktree_path}"}
            
            # 通过工作树路径查找标签页
            target_tab_id = await worktree_manager.find_tab_by_path(worktree_path)
            if not target_tab_id:
                return {"error": f"未找到工作树 '{request.worktree_name}' 的 iTerm 标签页"}
        
        # 查找并切换到目标标签页
        for window in app.windows:
            for tab in window.tabs:
                if tab.tab_id == target_tab_id:
                    await tab.async_select()
                    return {
                        "success": True,
                        "message": f"已切换到工作树 '{request.worktree_name}' 标签页 {target_tab_id}"
                    }
        
        return {"error": f"无法切换到标签页 {target_tab_id}"}
        
    except Exception as e:
        return {"error": f"切换到工作树失败: {str(e)}"}


@mcp.tool()
async def open_worktree(request: OpenWorktreeRequest) -> Dict[str, Any]:
    """在新的iTerm2标签页中打开现有工作树"""
    if not worktree_manager.is_iterm:
        return {"error": "此工具只能在 iTerm 环境中使用"}
    
    # 检查工作树是否存在
    parent_dir = os.path.dirname(os.getcwd())
    worktree_path = os.path.join(parent_dir, request.worktree_name)
    
    if not os.path.exists(worktree_path):
        return {"error": f"工作树 '{request.worktree_name}' 不存在于 {worktree_path}"}
    
    # 检查工作树是否已在任何标签页中打开（仅针对new_tab和new_window）
    if request.open_location in ["new_tab", "new_window"]:
        existing_tabs = await worktree_manager.find_all_tabs_by_path(worktree_path)
        
        if existing_tabs and not request.force:
            # 工作树已打开且未设置强制选项
            tab_info_parts = []
            for tab in existing_tabs:
                this_window_indicator = " (thisWindow)" if tab.this_window else ""
                tab_info_parts.append(f"Tab: {tab.tab_id}{this_window_indicator}")
            
            tab_info = ", ".join(tab_info_parts)
            return {
                "error": f"工作树 '{request.worktree_name}' 已在 {tab_info} 中打开。使用 force=true 强制在新{request.open_location.replace('_', ' ')}中打开。"
            }
    
    # 在指定位置打开工作树
    success, automation_msg = await worktree_manager.automate_iterm(
        request.worktree_name,
        f"继续开发工作树 {request.worktree_name}",
        False,  # 不自动启动 Claude
        request.open_location,
        request.switch_back
    )
    
    if not success:
        return {"error": f"打开工作树失败: {automation_msg}"}
    
    force_message = " (强制)" if request.force and request.open_location in ["new_tab", "new_window"] else ""
    location_display = request.open_location.replace('_', ' ')
    
    return {
        "success": True,
        "message": f"已在{location_display}中打开工作树 '{request.worktree_name}'{force_message}"
    }


@mcp.tool()
async def notify_task_complete(request: NotifyCompleteRequest) -> Dict[str, Any]:
    """通知主会话任务已完成（新功能：跨会话通信）"""
    if not worktree_manager.is_iterm:
        return {"error": "此工具只能在 iTerm 环境中使用"}
    
    if request.auto_merge:
        # 执行自动分析和合并
        result = await auto_merge_handler.handle_task_complete_notification(
            request.worktree_name,
            request.task_summary
        )
        return result
    else:
        # 仅发送通知
        success, msg = await session_communicator.notify_task_complete(
            request.worktree_name,
            request.task_summary
        )
        return {"success": success, "message": msg}


@mcp.tool()
async def analyze_worktree_changes(worktree_name: str) -> Dict[str, Any]:
    """分析工作树的代码变更（新功能：智能分析）"""
    from .communication import SmartMergeAnalyzer
    analyzer = SmartMergeAnalyzer()
    return analyzer.analyze_worktree_changes(worktree_name)




def main():
    """主MCP服务器循环"""
    # 只有在iTerm环境中才提供完整功能
    if not worktree_manager.is_iterm:
        print("警告: 此 MCP 服务器需要在 iTerm 环境中运行以提供完整功能", file=sys.stderr)
        # 在非iTerm环境中仍然可以提供基本的git工作树管理功能
    
    # 启动 FastMCP 服务器
    mcp.run()


if __name__ == "__main__":
    main()