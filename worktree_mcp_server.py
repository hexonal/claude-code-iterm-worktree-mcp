#!/usr/bin/env python3

import asyncio
import json
import os
import subprocess
import sys
import time
import iterm2
from typing import Any, Dict, List, Optional


class WorktreeMCPServer:
    def __init__(self):
        # 检查是否在iTerm中运行
        self.is_iterm = self.detect_iterm()
        
        # 只有在iTerm中运行时才提供工具
        self.tools = self.get_tools() if self.is_iterm else []

    def detect_iterm(self) -> bool:
        """检测MCP服务器是否在iTerm中运行"""
        try:
            # 检查iTerm设置的环境变量
            term_program = os.environ.get('TERM_PROGRAM', '')
            if term_program != 'iTerm.app':
                return False
            
            # 检查iTerm是否正在运行
            result = subprocess.run(['pgrep', '-f', 'iTerm'], capture_output=True, text=True)
            if result.returncode != 0:
                print("Warning: iTerm.app not running", file=sys.stderr)
                return False
            
            # 检查是否已经有运行的事件循环
            try:
                # 如果已经在运行的事件循环中，跳过 iTerm API 测试，假设可用
                asyncio.get_running_loop()
                # 如果能到达这里，说明已经在事件循环中运行
                return True
            except RuntimeError:
                # 没有运行的事件循环，安全创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    connection = loop.run_until_complete(iterm2.Connection.async_create())
                    loop.run_until_complete(connection.async_close())
                    return True
                except Exception as conn_error:
                    print(f"Warning: iTerm API not available: {conn_error}", file=sys.stderr)
                    print("Hint: Enable iTerm Python API in Preferences > General > Magic", file=sys.stderr)
                    return False
                finally:
                    loop.close()
                
        except Exception as e:
            print(f"Warning: Could not detect iTerm: {e}", file=sys.stderr)
            return False

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [
            {
                "name": "createWorktree",
                "description": "创建git工作树并通过iTerm自动化启动开发",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "object",
                            "description": "创建工作树请求模型",
                            "properties": {
                                "feature_name": {
                                    "type": "string",
                                    "description": "要开发的功能名称 (例如: 'add-auth')"
                                },
                                "branch_name": {
                                    "type": "string", 
                                    "description": "要使用的分支名称 (例如: 'feature/add-auth')"
                                },
                                "worktree_folder": {
                                    "type": "string",
                                    "description": "工作树文件夹名称 (例如: 'project-name-feat-add-auth')"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "要执行的任务描述"
                                },
                                "start_claude": {
                                    "type": "boolean",
                                    "description": "是否自动使用任务描述启动Claude (默认: false)。仅当您希望Claude使用特定命令启动时才设置为true。"
                                },
                                "open_location": {
                                    "type": "string",
                                    "enum": ["new_tab", "new_window", "new_pane_right", "new_pane_below"],
                                    "description": "工作树打开位置 (默认: new_tab)。选项: new_tab (新标签页), new_window (新窗口), new_pane_right (垂直分割,右侧新窗格), new_pane_below (水平分割,下方新窗格)"
                                },
                                "switch_back": {
                                    "type": "boolean",
                                    "description": "Whether to switch back to the original tab/window after opening the worktree (default: false). Only applies to new_tab and new_window locations."
                                }
                            },
                            "required": ["feature_name", "branch_name", "worktree_folder", "description"]
                        }
                    },
                    "required": ["request"]
                }
            },
            {
                "name": "closeWorktree",
                "description": "在检查工作树已清理并推送后关闭工作树",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "要关闭的工作树文件夹名称"
                        }
                    },
                    "required": ["worktree_name"]
                }
            },
            {
                "name": "activeWorktrees",
                "description": "列出此MCP服务器管理的所有活动工作树",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "switchToWorktree",
                "description": "在iTerm2中切换到工作树标签页",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "要切换到的工作树文件夹名称"
                        },
                        "tab_id": {
                            "type": "string",
                            "description": "可选的特定标签页ID。如果未提供，将通过工作树路径查找标签页"
                        }
                    },
                    "required": ["worktree_name"]
                }
            },
            {
                "name": "openWorktree",
                "description": "在新的iTerm2标签页中打开现有工作树",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "要打开的工作树文件夹名称"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "即使工作树已在其他地方打开也强制在新标签页中打开 (默认: false)"
                        },
                        "open_location": {
                            "type": "string",
                            "enum": ["new_tab", "new_window", "new_pane_right", "new_pane_below"],
                            "description": "工作树打开位置 (默认: new_tab)。选项: new_tab (新标签页), new_window (新窗口), new_pane_right (垂直分割,右侧新窗格), new_pane_below (水平分割,下方新窗格)"
                        },
                        "switch_back": {
                            "type": "boolean",
                            "description": "Whether to switch back to the original tab/window after opening the worktree (default: false). Only applies to new_tab and new_window locations."
                        }
                    },
                    "required": ["worktree_name"]
                }
            }
        ]

    async def find_tab_by_path(self, worktree_path: str) -> Optional[str]:
        """查找具有给定工作树路径作为工作目录的iTerm2标签页ID"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 规范化工作树路径以便比较
            normalized_worktree = os.path.normpath(worktree_path)
            
            # 搜索所有标签页以找到匹配工作目录的标签页
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        # 获取会话的工作目录
                        try:
                            working_dir = await session.async_get_variable("path")
                            if working_dir:
                                normalized_working_dir = os.path.normpath(working_dir)
                                if normalized_working_dir == normalized_worktree:
                                    return tab.tab_id
                        except:
                            # 如果无法获取路径，继续下一个会话
                            continue
            
            return None
            
        except Exception as e:
            print(f"Warning: Could not search iTerm tabs: {e}", file=sys.stderr)
            return None

    async def find_all_tabs_by_path(self, worktree_path: str) -> List[Dict[str, Any]]:
        """查找所有具有给定工作树路径作为工作目录的iTerm2标签页"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 规范化工作树路径以便比较
            normalized_worktree = os.path.normpath(worktree_path)
            
            # 获取当前窗口以确定thisWindow标志
            current_window = app.current_window
            current_window_id = current_window.window_id if current_window else None
            
            matching_tabs = []
            
            # Search through all tabs to find ones with matching working directory
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        # 获取会话的工作目录
                        try:
                            working_dir = await session.async_get_variable("path")
                            if working_dir:
                                normalized_working_dir = os.path.normpath(working_dir)
                                if normalized_working_dir == normalized_worktree:
                                    matching_tabs.append({
                                        "tabId": tab.tab_id,
                                        "windowId": window.window_id,
                                        "thisWindow": window.window_id == current_window_id
                                    })
                        except:
                            # 如果无法获取路径，继续下一个会话
                            continue
            
            return matching_tabs
            
        except Exception as e:
            print(f"Warning: Could not search iTerm tabs: {e}", file=sys.stderr)
            return []


    def get_all_git_worktrees(self) -> List[Dict[str, str]]:
        """从git命令获取所有git工作树"""
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            worktrees = []
            current_worktree = {}
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    if current_worktree:
                        worktrees.append(current_worktree)
                        current_worktree = {}
                    continue
                    
                if line.startswith('worktree '):
                    current_worktree['path'] = line[9:]  # Remove 'worktree ' prefix
                    # 从路径中提取文件夹名称
                    current_worktree['folder'] = os.path.basename(current_worktree['path'])
                elif line.startswith('branch '):
                    current_worktree['branch'] = line[7:]  # Remove 'branch ' prefix
                elif line.startswith('HEAD '):
                    current_worktree['head'] = line[5:]  # Remove 'HEAD ' prefix
            
            # 如果存在则添加最后一个工作树
            if current_worktree:
                worktrees.append(current_worktree)
            
            return worktrees
            
        except subprocess.CalledProcessError:
            return []
        except Exception:
            return []

    def validate_worktree_creation(self, branch_name: str, worktree_folder: str) -> tuple[bool, str]:
        """验证是否可以创建工作树"""
        # 检查是否在git仓库中
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            return False, "Not in a git repository"

        # 检查分支是否已存在
        try:
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip():
                return False, f"Branch '{branch_name}' already exists"
        except subprocess.CalledProcessError:
            return False, "Failed to check if branch exists"

        # 检查工作树文件夹是否已在父目录中存在
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_folder)
        if os.path.exists(worktree_path):
            return False, f"Folder '{worktree_folder}' already exists in parent directory"

        return True, "Validation passed"

    def create_worktree(self, branch_name: str, worktree_folder: str) -> tuple[bool, str]:
        """创建git工作树"""
        try:
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_folder)
            
            # 使用新分支创建工作树
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, worktree_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, f"Worktree created successfully at {worktree_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create worktree: {e.stderr}"


    async def automate_iterm(self, worktree_folder: str, description: str, start_claude: bool = True, open_location: str = "new_tab", switch_back: bool = False) -> tuple[bool, str]:
        """自动化iTerm在指定位置打开工作树，切换到工作树目录，并可选地启动claude"""
        try:
            # 连接到iTerm
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 获取当前窗口和会话作为上下文
            current_window = app.current_window
            if not current_window:
                return False, "No current iTerm window found"
            
            original_tab = current_window.current_tab
            original_session = original_tab.current_session if original_tab else None
            
            session = None
            tab_id = None
            
            # 根据open_location创建会话
            if open_location == "new_window":
                # 创建新窗口
                new_window = await iterm2.Window.async_create(connection)
                session = new_window.current_tab.current_session
                tab_id = new_window.current_tab.tab_id
                
            elif open_location == "new_tab":
                # 创建新标签页（原始行为）
                new_tab = await current_window.async_create_tab()
                session = new_tab.current_session
                tab_id = new_tab.tab_id
                
            elif open_location == "new_pane_right":
                # 垂直分割窗格（新窗格在右侧）
                if not original_session:
                    return False, "No current session found for pane split"
                session = await original_session.async_split_pane(vertical=True)
                # 对于窗格，我们使用包含该窗格的标签页ID
                tab_id = original_tab.tab_id
                
            elif open_location == "new_pane_below":
                # 水平分割窗格（新窗格在下方）
                if not original_session:
                    return False, "No current session found for pane split"
                session = await original_session.async_split_pane(vertical=False)
                # 对于窗格，我们使用包含该窗格的标签页ID
                tab_id = original_tab.tab_id
                
            else:
                return False, f"Invalid open_location: {open_location}"
            
            if not session:
                return False, f"Failed to create session for {open_location}"
            
            # 等待1秒然后切换到工作树目录
            await asyncio.sleep(1)
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_folder)
            await session.async_send_text(f"cd '{worktree_path}'\n")
            
            # 可选地发送claude命令，包含禁用工具和任务描述作为参数
            if start_claude:
                escaped_description = description.replace('"', '\\"')
                await session.async_send_text(f'claude "{escaped_description}" --disallowedTools mcp__worktree__createWorktree,mcp__worktree__closeWorktree,mcp__worktree__activeWorktrees,mcp__worktree__switchToWorktree,mcp__worktree__openWorktree\n')
            
            # 仅当switch_back为True且对于new_tab和new_window情况时才切换回原标签页/窗口
            if switch_back and open_location in ["new_tab", "new_window"] and original_tab:
                await original_tab.async_select()
            
            return True, f"iTerm automation completed successfully ({open_location})"
            
        except Exception as e:
            error_msg = str(e)
            if "Connect call failed" in error_msg or "Connection refused" in error_msg:
                return False, f"iTerm automation failed: Unable to connect to iTerm API. Please enable 'Python API' in iTerm2 Preferences > General > Magic, then restart iTerm2. Error: {error_msg}"
            else:
                return False, f"iTerm automation failed: {error_msg}"

    def validate_worktree_closure(self, worktree_name: str) -> tuple[bool, str]:
        """验证工作树是否可以关闭（已清理且已推送）"""
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        if not os.path.exists(worktree_path):
            return False, f"Worktree '{worktree_name}' does not exist"
        
        try:
            # 检查git状态是否干净
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                return False, f"Worktree has uncommitted changes: {result.stdout.strip()}"
            
            # 检查所有提交是否已推送（如果上游存在）
            # 首先检查是否有上游分支
            upstream_check = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "@{u}"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            if upstream_check.returncode == 0:
                # 上游存在，检查未推送的提交
                result = subprocess.run(
                    ["git", "log", "--oneline", "@{u}..HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stdout.strip():
                    return False, f"Worktree has unpushed commits: {result.stdout.strip()}"
            else:
                # 没有上游，检查是否有超前于基分支的提交
                # 首先获取基分支（通常是main/master）
                base_branch_result = subprocess.run(
                    ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True
                )
                
                if base_branch_result.returncode == 0:
                    # 从refs/remotes/origin/HEAD提取基分支名称
                    base_branch = base_branch_result.stdout.strip().split('/')[-1]
                else:
                    # 回退到常见的基分支名称
                    for branch in ["main", "master"]:
                        check_result = subprocess.run(
                            ["git", "rev-parse", "--verify", f"origin/{branch}"],
                            cwd=worktree_path,
                            capture_output=True,
                            text=True
                        )
                        if check_result.returncode == 0:
                            base_branch = branch
                            break
                    else:
                        # 如果无法确定基分支，在工作树干净时允许删除
                        return True, "Worktree is clean and can be deleted"
                
                # 检查超前于基分支的提交
                result = subprocess.run(
                    ["git", "log", "--oneline", f"origin/{base_branch}..HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return False, f"Branch has commits ahead of origin/{base_branch} but no upstream configured. Push the branch first or use --force"
            
            return True, "Worktree is clean and pushed"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check worktree status: {e.stderr}"

    async def check_iterm_tab_exists(self, tab_id: str) -> bool:
        """检查iTerm标签页是否存在"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 通过ID查找标签页
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == tab_id:
                        return True
            
            return False
            
        except Exception as e:
            # 如果无法连接到iTerm，假设标签页不存在
            return False

    async def close_iterm_tab(self, tab_id: str) -> tuple[bool, str]:
        """如果iTerm标签页存在则关闭它"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 通过ID查找标签页
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == tab_id:
                        await tab.async_close()
                        return True, f"Closed tab {tab_id}"
            
            return False, f"Tab {tab_id} not found"
            
        except Exception as e:
            return False, f"Failed to close tab: {str(e)}"

    def check_branch_has_commits(self, worktree_name: str) -> tuple[bool, str]:
        """检查工作树的分支是否有超出基分支的提交"""
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        try:
            # 获取当前分支名称
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()
            
            # 获取基分支（通常是main/master）
            base_branch_result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            if base_branch_result.returncode == 0:
                base_branch = base_branch_result.stdout.strip().split('/')[-1]
            else:
                # Fallback to common base branch names
                for branch in ["main", "master"]:
                    check_result = subprocess.run(
                        ["git", "rev-parse", "--verify", f"origin/{branch}"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True
                    )
                    if check_result.returncode == 0:
                        base_branch = branch
                        break
                else:
                    return False, "Could not determine base branch"
            
            # Check for commits ahead of base branch
            result = subprocess.run(
                ["git", "log", "--oneline", f"origin/{base_branch}..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                has_commits = bool(result.stdout.strip())
                return has_commits, current_branch
            else:
                return False, "Failed to check commit history"
                
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check branch commits: {e.stderr}"

    def delete_branch(self, branch_name: str) -> tuple[bool, str]:
        """删除git分支"""
        try:
            # 删除分支
            result = subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Deleted branch '{branch_name}'"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to delete branch '{branch_name}': {e.stderr}"

    async def handle_close_worktree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理closeWorktree工具调用"""
        worktree_name = arguments["worktree_name"]
        
        # 步骤1: 验证工作树可以关闭
        valid, validation_msg = self.validate_worktree_closure(worktree_name)
        if not valid:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Cannot close worktree: {validation_msg}"
                    }
                ]
            }
        
        # 步骤2: 检查分支是否有提交并获取分支名称
        has_commits, branch_name_or_error = self.check_branch_has_commits(worktree_name)
        branch_to_delete = None
        if isinstance(branch_name_or_error, str) and not has_commits:
            branch_to_delete = branch_name_or_error
        
        # 步骤3: 通过工作树路径动态查找标签页ID
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        tab_id = await self.find_tab_by_path(worktree_path)
        
        # 步骤4: 移除工作树
        try:
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_name)
            
            result = subprocess.run(
                ["git", "worktree", "remove", worktree_path],
                capture_output=True,
                text=True,
                check=True
            )
            
        except subprocess.CalledProcessError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Failed to remove worktree: {e.stderr}"
                    }
                ]
            }
        
        # 步骤5: 如果分支没有提交则删除分支
        branch_deleted = False
        if branch_to_delete:
            success, delete_msg = self.delete_branch(branch_to_delete)
            branch_deleted = success
        
        # 步骤6: 如果iTerm标签页存在则关闭它
        tab_closed = False
        if tab_id:
            success, tab_msg = await self.close_iterm_tab(tab_id)
            tab_closed = success
        
        # 构建成功消息
        message = f"✅ Successfully closed worktree '{worktree_name}'"
        if branch_deleted:
            message += f" and deleted branch '{branch_to_delete}'"
        if tab_closed:
            message += " and closed iTerm tab"
        elif tab_id:
            message += " (iTerm tab could not be closed)"
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }

    async def handle_create_worktree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理createWorktree工具调用"""
        request = arguments["request"]
        feature_name = request["feature_name"]
        branch_name = request["branch_name"] 
        worktree_folder = request["worktree_folder"]
        description = request["description"]
        
        # 步骤0: 验证
        valid, validation_msg = self.validate_worktree_creation(branch_name, worktree_folder)
        if not valid:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Validation failed: {validation_msg}"
                    }
                ]
            }
        
        # 步骤1: 创建工作树
        success, worktree_msg = self.create_worktree(branch_name, worktree_folder)
        if not success:
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"❌ {worktree_msg}"
                    }
                ]
            }
        
        # 步骤2-6: iTerm自动化
        start_claude = request.get("start_claude", False)  # 默认为False以避免猜测
        open_location = request.get("open_location", "new_tab")  # 默认为new_tab
        switch_back = request.get("switch_back", False)  # 默认为False
        success, iterm_msg = await self.automate_iterm(worktree_folder, description, start_claude, open_location, switch_back)
        if not success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Worktree created but iTerm automation failed: {iterm_msg}"
                    }
                ]
            }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"✅ Successfully created worktree '{worktree_folder}' with branch '{branch_name}' and started development session"
                }
            ]
        }

    async def handle_list_worktrees(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理listWorktrees工具调用"""
        # 获取所有git工作树
        git_worktrees = self.get_all_git_worktrees()
        
        if not git_worktrees:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "📝 No git worktrees found"
                    }
                ]
            }
        
        # 动态检查每个工作树的标签页状态并构建响应
        response_lines = ["📋 All Git Worktrees:"]
        for i, git_worktree in enumerate(git_worktrees, 1):
            folder = git_worktree.get("folder", "Unknown")
            branch = git_worktree.get("branch", "Unknown")
            path = git_worktree.get("path", "Unknown")
            
            # 通过路径动态查找所有iTerm2标签页
            matching_tabs = await self.find_all_tabs_by_path(path)
            
            if matching_tabs:
                # 格式化标签页信息
                tab_info_parts = []
                for tab in matching_tabs:
                    tab_exists = await self.check_iterm_tab_exists(tab["tabId"])
                    tab_status = "✅" if tab_exists else "❌"
                    this_window_indicator = " (thisWindow)" if tab["thisWindow"] else ""
                    tab_info_parts.append(f"Tab: {tab['tabId']}{this_window_indicator} {tab_status}")
                
                tab_info = ", ".join(tab_info_parts)
                response_lines.append(f"  {i}. {folder} (Branch: {branch}, {tab_info})")
            else:
                # 没有找到使用此工作树路径的标签页
                response_lines.append(f"  {i}. {folder} (Branch: {branch}, Path: {path}) 📍 No iTerm tabs found")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": "\n".join(response_lines)
                }
            ]
        }

    async def handle_switch_to_worktree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理switchToWorktree工具调用"""
        worktree_name = arguments["worktree_name"]
        tab_id = arguments.get("tab_id")
        
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            target_tab_id = None
            
            if tab_id:
                # 提供了标签页ID - 验证其存在
                tab_exists = await self.check_iterm_tab_exists(tab_id)
                if not tab_exists:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Tab {tab_id} not found"
                            }
                        ]
                    }
                target_tab_id = tab_id
            else:
                # 未提供标签页ID - 通过工作树路径查找
                parent_dir = os.path.dirname(os.getcwd())
                worktree_path = os.path.join(parent_dir, worktree_name)
                
                # 检查工作树是否存在
                if not os.path.exists(worktree_path):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Worktree '{worktree_name}' does not exist at {worktree_path}"
                            }
                        ]
                    }
                
                # 通过工作树路径查找标签页
                target_tab_id = await self.find_tab_by_path(worktree_path)
                if not target_tab_id:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ No iTerm tab found for worktree '{worktree_name}' at {worktree_path}"
                            }
                        ]
                    }
            
            # 查找并切换到目标标签页
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == target_tab_id:
                        await tab.async_select()
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"✅ Switched to worktree '{worktree_name}' tab {target_tab_id}"
                                }
                            ]
                        }
            
            # 如果check_iterm_tab_exists工作正常，这种情况不应该发生
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Could not switch to tab {target_tab_id}"
                    }
                ]
            }
            
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Failed to switch to worktree: {str(e)}"
                    }
                ]
            }

    async def handle_open_worktree(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理openWorktree工具调用"""
        worktree_name = arguments["worktree_name"]
        force = arguments.get("force", False)
        open_location = arguments.get("open_location", "new_tab")
        switch_back = arguments.get("switch_back", False)
        
        # Check if worktree exists
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        if not os.path.exists(worktree_path):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Worktree '{worktree_name}' does not exist at {worktree_path}"
                    }
                ]
            }
        
        # 检查工作树是否已在任何标签页中打开（仅针对new_tab和new_window）
        if open_location in ["new_tab", "new_window"]:
            existing_tabs = await self.find_all_tabs_by_path(worktree_path)
            
            if existing_tabs and not force:
                # 工作树已打开且未设置强制选项
                tab_info_parts = []
                for tab in existing_tabs:
                    this_window_indicator = " (thisWindow)" if tab["thisWindow"] else ""
                    tab_info_parts.append(f"Tab: {tab['tabId']}{this_window_indicator}")
                
                tab_info = ", ".join(tab_info_parts)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Worktree '{worktree_name}' is already open in {tab_info}. Use force=true to open in a new {open_location.replace('_', ' ')} anyway."
                        }
                    ]
                }
        
        # 在指定位置打开工作树
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 获取当前窗口和会话作为上下文
            current_window = app.current_window
            if not current_window:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "❌ No current iTerm window found"
                        }
                    ]
                }
            
            original_tab = current_window.current_tab
            original_session = original_tab.current_session if original_tab else None
            
            session = None
            tab_id = None
            
            # 根据open_location创建会话
            if open_location == "new_window":
                # 创建新窗口
                new_window = await iterm2.Window.async_create(connection)
                session = new_window.current_tab.current_session
                tab_id = new_window.current_tab.tab_id
                
            elif open_location == "new_tab":
                # 创建新标签页（原始行为）
                new_tab = await current_window.async_create_tab()
                session = new_tab.current_session
                tab_id = new_tab.tab_id
                
            elif open_location == "new_pane_right":
                # 垂直分割窗格（新窗格在右侧）
                if not original_session:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "❌ No current session found for pane split"
                            }
                        ]
                    }
                session = await original_session.async_split_pane(vertical=True)
                # 对于窗格，我们使用包含该窗格的标签页ID
                tab_id = original_tab.tab_id
                
            elif open_location == "new_pane_below":
                # 水平分割窗格（新窗格在下方）
                if not original_session:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": "❌ No current session found for pane split"
                            }
                        ]
                    }
                session = await original_session.async_split_pane(vertical=False)
                # 对于窗格，我们使用包含该窗格的标签页ID
                tab_id = original_tab.tab_id
                
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Invalid open_location: {open_location}"
                        }
                    ]
                }
            
            if not session:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Failed to create session for {open_location}"
                        }
                    ]
                }
            
            # 等待1秒然后切换到工作树目录
            await asyncio.sleep(1)
            await session.async_send_text(f"cd '{worktree_path}'\n")
            
            # 仅当switch_back为True且对于new_tab和new_window情况时才切换回原标签页/窗口
            if switch_back and open_location in ["new_tab", "new_window"] and original_tab:
                await original_tab.async_select()
            
            force_message = " (forced)" if force and open_location in ["new_tab", "new_window"] else ""
            location_display = open_location.replace('_', ' ')
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Opened worktree '{worktree_name}' in {location_display} {tab_id}{force_message}"
                    }
                ]
            }
            
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Failed to open worktree: {str(e)}"
                    }
                ]
            }

async def handle_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """处理传入的MCP消息"""
    server = WorktreeMCPServer()
    
    method = message.get("method")
    
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "worktree-mcp-server",
                "version": "1.0.0"
            }
        }
    elif method == "tools/list":
        return {
            "tools": server.tools
        }
    elif method == "tools/call":
        tool_name = message["params"]["name"]
        arguments = message["params"]["arguments"]
        
# Debug: Log arguments structure
        print(f"DEBUG: Tool {tool_name} called with arguments type: {type(arguments)}", file=sys.stderr)
        print(f"DEBUG: Arguments content: {arguments}", file=sys.stderr)
        
        if tool_name == "createWorktree":
            return await server.handle_create_worktree(arguments)
        elif tool_name == "closeWorktree":
            return await server.handle_close_worktree(arguments)
        elif tool_name == "activeWorktrees":
            return await server.handle_list_worktrees(arguments)
        elif tool_name == "switchToWorktree":
            return await server.handle_switch_to_worktree(arguments)
        elif tool_name == "openWorktree":
            return await server.handle_open_worktree(arguments)
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}"
                    }
                ],
                "isError": True
            }
    else:
        return {
            "content": [
                {
                    "type": "text", 
                    "text": f"Unknown method: {method}"
                }
            ],
            "isError": True
        }

async def main():
    """主MCP服务器循环"""
    # 从stdin读取消息并将响应写入stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            message = json.loads(line.strip())
            response = await handle_message(message)
            
            # 使用正确的MCP格式发送响应
            response_obj = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": response
            }
            
            print(json.dumps(response_obj))
            sys.stdout.flush()
            
        except EOFError:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0", 
                "id": message.get("id") if 'message' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Server error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())