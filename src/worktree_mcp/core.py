"""
工作树 MCP 服务器的核心功能
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import iterm2
from .models import TabInfo, WorktreeStatus, WorktreeSessionMapping


class WorktreeManager:
    """工作树管理器核心类"""
    
    def __init__(self):
        self.is_iterm = self.detect_iterm()
        # 会话映射文件路径
        self.session_mapping_file = os.path.join(os.path.dirname(os.getcwd()), ".worktree-session-mappings.json")
    
    def detect_iterm(self) -> bool:
        """检测MCP服务器是否在iTerm中运行"""
        try:
            # 检查iTerm设置的环境变量
            term_program = os.environ.get('TERM_PROGRAM', '')
            if term_program == 'iTerm.app':
                return True
            
            # 尝试连接到iTerm来验证其可用性
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                connection = loop.run_until_complete(iterm2.Connection.async_create())
                loop.run_until_complete(connection.async_close())
                return True
            except:
                return False
            finally:
                loop.close()
                
        except Exception as e:
            print(f"Warning: Could not detect iTerm: {e}", file=sys.stderr)
            return False

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

    async def find_all_tabs_by_path(self, worktree_path: str) -> List[TabInfo]:
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
                                    tab_exists = await self.check_iterm_tab_exists(tab.tab_id)
                                    matching_tabs.append(TabInfo(
                                        tab_id=tab.tab_id,
                                        window_id=window.window_id,
                                        this_window=window.window_id == current_window_id,
                                        exists=tab_exists
                                    ))
                        except:
                            # 如果无法获取路径，继续下一个会话
                            continue
            
            return matching_tabs
            
        except Exception as e:
            print(f"Warning: Could not search iTerm tabs: {e}", file=sys.stderr)
            return []

    def get_all_git_worktrees(self) -> List[WorktreeStatus]:
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
                        folder = os.path.basename(current_worktree.get('path', ''))
                        worktrees.append(WorktreeStatus(
                            folder=folder,
                            branch=current_worktree.get('branch', 'Unknown'),
                            path=current_worktree.get('path', 'Unknown'),
                            status='active',  # 默认状态，后续可以增强
                            tabs=[]
                        ))
                        current_worktree = {}
                    continue
                    
                if line.startswith('worktree '):
                    current_worktree['path'] = line[9:]  # Remove 'worktree ' prefix
                elif line.startswith('branch '):
                    current_worktree['branch'] = line[7:]  # Remove 'branch ' prefix
                elif line.startswith('HEAD '):
                    current_worktree['head'] = line[5:]  # Remove 'HEAD ' prefix
            
            # 如果存在则添加最后一个工作树
            if current_worktree:
                folder = os.path.basename(current_worktree.get('path', ''))
                worktrees.append(WorktreeStatus(
                    folder=folder,
                    branch=current_worktree.get('branch', 'Unknown'),
                    path=current_worktree.get('path', 'Unknown'),
                    status='active',
                    tabs=[]
                ))
            
            return worktrees
            
        except subprocess.CalledProcessError:
            return []
        except Exception:
            return []

    def validate_worktree_creation(self, branch_name: str, worktree_folder: str) -> Tuple[bool, str]:
        """验证是否可以创建工作树"""
        # 检查是否在git仓库中
        try:
            subprocess.run(
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

    def create_worktree(self, branch_name: str, worktree_folder: str) -> Tuple[bool, str]:
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

    async def automate_iterm(
        self, 
        worktree_folder: str, 
        description: str, 
        start_claude: bool = True, 
        open_location: str = "new_tab", 
        switch_back: bool = False
    ) -> Tuple[bool, str]:
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
            
            # 可选地发送claude命令，使用增强的命令构建逻辑
            if start_claude:
                from .session_manager import ClaudeSessionManager
                session_manager = ClaudeSessionManager()
                claude_command = session_manager.build_claude_command(description, worktree_folder)
                await session.async_send_text(f'{claude_command}\n')
            
            # 仅当switch_back为True且对于new_tab和new_window情况时才切换回原标签页/窗口
            if switch_back and open_location in ["new_tab", "new_window"] and original_tab:
                await original_tab.async_select()
            
            return True, f"iTerm automation completed successfully ({open_location})"
            
        except Exception as e:
            return False, f"iTerm automation failed: {str(e)}"

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
            
        except Exception:
            # 如果无法连接到iTerm，假设标签页不存在
            return False

    async def close_iterm_tab(self, tab_id: str) -> Tuple[bool, str]:
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

    def validate_worktree_closure(self, worktree_name: str) -> Tuple[bool, str]:
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
                base_branch = self._get_base_branch(worktree_path)
                if base_branch:
                    result = subprocess.run(
                        ["git", "log", "--oneline", f"origin/{base_branch}..HEAD"],
                        cwd=worktree_path,
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        return False, f"Branch has commits ahead of origin/{base_branch} but no upstream configured. Push the branch first"
            
            return True, "Worktree is clean and pushed"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check worktree status: {e.stderr}"

    def _get_base_branch(self, worktree_path: str) -> Optional[str]:
        """获取基分支名称"""
        try:
            # 首先获取基分支（通常是main/master）
            base_branch_result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            if base_branch_result.returncode == 0:
                # 从refs/remotes/origin/HEAD提取基分支名称
                return base_branch_result.stdout.strip().split('/')[-1]
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
                        return branch
                return None
        except:
            return None

    def check_branch_has_commits(self, worktree_name: str) -> Tuple[bool, str]:
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
            base_branch = self._get_base_branch(worktree_path)
            if not base_branch:
                return False, "Could not determine base branch"
            
            # 检查超前于基分支的提交
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

    def delete_branch(self, branch_name: str) -> Tuple[bool, str]:
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

    async def send_message_to_main_session(self, message: str, worktree_name: str = None) -> Tuple[bool, str]:
        """向主会话发送消息 - 支持精准会话路由"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 如果提供了 worktree_name，尝试精准路由到创建会话
            if worktree_name:
                creator_mapping = self.get_worktree_creator_session(worktree_name)
                if creator_mapping:
                    # 尝试通过会话 ID 找到对应的标签页
                    target_tab = await self._find_tab_by_session_id(creator_mapping.creator_session_id)
                    if target_tab:
                        await target_tab.current_session.async_send_text(f"{message}\n")
                        return True, f"消息已发送到创建会话 {creator_mapping.creator_session_id}"
                    
                    # 如果有记录的标签页 ID，尝试直接查找
                    if creator_mapping.creator_tab_id:
                        tab_exists = await self.check_iterm_tab_exists(creator_mapping.creator_tab_id)
                        if tab_exists:
                            for window in app.windows:
                                for tab in window.tabs:
                                    if tab.tab_id == creator_mapping.creator_tab_id:
                                        await tab.current_session.async_send_text(f"{message}\n")
                                        return True, f"消息已发送到原创建标签页 {creator_mapping.creator_tab_id}"
            
            # 备选方案：查找主项目目录的标签页（原有逻辑）
            current_dir = os.getcwd()
            parent_dir = os.path.dirname(current_dir)
            
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        try:
                            working_dir = await session.async_get_variable("path")
                            if working_dir and os.path.normpath(working_dir) == os.path.normpath(parent_dir):
                                await session.async_send_text(f"{message}\n")
                                return True, f"消息已发送到主会话（备选方案）"
                        except:
                            continue
            
            return False, "未找到目标主会话"
            
        except Exception as e:
            return False, f"发送消息失败: {str(e)}"
    
    async def _find_tab_by_session_id(self, session_id: str) -> Optional[object]:
        """通过会话 ID 查找对应的 iTerm 标签页"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # 遍历所有标签页，查找会话标识
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        try:
                            # 检查标签页是否有会话标识环境变量
                            session_var = await session.async_get_variable("CLAUDE_SESSION_ID")
                            if session_var == session_id:
                                return tab
                            
                            # 检查工作目录中是否有会话标识文件
                            working_dir = await session.async_get_variable("path")
                            if working_dir:
                                session_file = os.path.join(working_dir, ".claude_session_id")
                                if os.path.exists(session_file):
                                    with open(session_file, 'r') as f:
                                        stored_session = f.read().strip()
                                        if stored_session == session_id:
                                            return tab
                        except:
                            continue
            
            return None
        except:
            return None
    
    def save_worktree_session_mapping(self, mapping: WorktreeSessionMapping) -> bool:
        """保存工作树到会话的映射关系"""
        try:
            # 读取现有映射
            mappings = self._load_session_mappings()
            
            # 添加或更新映射
            mappings[mapping.worktree_name] = mapping.model_dump()
            
            # 保存到文件
            with open(self.session_mapping_file, 'w') as f:
                json.dump(mappings, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save session mapping: {e}", file=sys.stderr)
            return False
    
    def get_worktree_creator_session(self, worktree_name: str) -> Optional[WorktreeSessionMapping]:
        """获取工作树的创建会话信息"""
        try:
            mappings = self._load_session_mappings()
            mapping_data = mappings.get(worktree_name)
            
            if mapping_data:
                return WorktreeSessionMapping(**mapping_data)
            
            return None
        except Exception as e:
            print(f"Failed to get session mapping: {e}", file=sys.stderr)
            return None
    
    def _load_session_mappings(self) -> Dict[str, Any]:
        """加载会话映射文件"""
        try:
            if os.path.exists(self.session_mapping_file):
                with open(self.session_mapping_file, 'r') as f:
                    return json.load(f)
            return {}
        except:
            return {}
    
    def cleanup_session_mapping(self, worktree_name: str) -> bool:
        """清理工作树的会话映射"""
        try:
            mappings = self._load_session_mappings()
            if worktree_name in mappings:
                del mappings[worktree_name]
                
                with open(self.session_mapping_file, 'w') as f:
                    json.dump(mappings, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to cleanup session mapping: {e}", file=sys.stderr)
            return False