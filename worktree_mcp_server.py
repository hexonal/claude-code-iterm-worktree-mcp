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
        # Check if running in iTerm
        self.is_iterm = self.detect_iterm()
        
        # Only provide tools if running in iTerm
        self.tools = self.get_tools() if self.is_iterm else []

    def detect_iterm(self) -> bool:
        """Detect if the MCP server is running in iTerm"""
        try:
            # Check environment variables that iTerm sets
            term_program = os.environ.get('TERM_PROGRAM', '')
            if term_program == 'iTerm.app':
                return True
            
            # Try to connect to iTerm to verify it's available
            import asyncio
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

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of available tools"""
        return [
            {
                "name": "createWorktree",
                "description": "Create a git worktree with iTerm automation to start development",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "feature_name": {
                            "type": "string",
                            "description": "The feature name to work on (e.g., 'add-auth')"
                        },
                        "branch_name": {
                            "type": "string", 
                            "description": "The branch name to use (e.g., 'feature/add-auth')"
                        },
                        "worktree_folder": {
                            "type": "string",
                            "description": "The worktree folder name (e.g., 'project-name-feat-add-auth')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the task to do"
                        },
                        "start_claude": {
                            "type": "boolean",
                            "description": "Whether to automatically start Claude with the task description (default: false). Only set to true if you want Claude to start with a specific command."
                        }
                    },
                    "required": ["feature_name", "branch_name", "worktree_folder", "description"]
                }
            },
            {
                "name": "closeWorktree",
                "description": "Close a worktree after checking it's clean and pushed",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "The name of the worktree folder to close"
                        }
                    },
                    "required": ["worktree_name"]
                }
            },
            {
                "name": "activeWorktrees",
                "description": "List all active worktrees managed by this MCP server",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "switchToWorktree",
                "description": "Switch to a worktree tab in iTerm2",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "The name of the worktree folder to switch to"
                        },
                        "tab_id": {
                            "type": "string",
                            "description": "Optional specific tab ID to switch to. If not provided, will find tab by worktree path"
                        }
                    },
                    "required": ["worktree_name"]
                }
            },
            {
                "name": "openWorktree",
                "description": "Open an existing worktree in a new iTerm2 tab",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "worktree_name": {
                            "type": "string",
                            "description": "The name of the worktree folder to open"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force open in new tab even if worktree is already open elsewhere (default: false)"
                        }
                    },
                    "required": ["worktree_name"]
                }
            }
        ]

    async def find_tab_by_path(self, worktree_path: str) -> Optional[str]:
        """Find iTerm2 tab ID that has the given worktree path as working directory"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Normalize the worktree path for comparison
            normalized_worktree = os.path.normpath(worktree_path)
            
            # Search through all tabs to find one with matching working directory
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        # Get the working directory of the session
                        try:
                            working_dir = await session.async_get_variable("path")
                            if working_dir:
                                normalized_working_dir = os.path.normpath(working_dir)
                                if normalized_working_dir == normalized_worktree:
                                    return tab.tab_id
                        except:
                            # If we can't get the path, continue to next session
                            continue
            
            return None
            
        except Exception as e:
            print(f"Warning: Could not search iTerm tabs: {e}", file=sys.stderr)
            return None

    async def find_all_tabs_by_path(self, worktree_path: str) -> List[Dict[str, Any]]:
        """Find all iTerm2 tabs that have the given worktree path as working directory"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Normalize the worktree path for comparison
            normalized_worktree = os.path.normpath(worktree_path)
            
            # Get current window to determine thisWindow flag
            current_window = app.current_window
            current_window_id = current_window.window_id if current_window else None
            
            matching_tabs = []
            
            # Search through all tabs to find ones with matching working directory
            for window in app.windows:
                for tab in window.tabs:
                    session = tab.current_session
                    if session:
                        # Get the working directory of the session
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
                            # If we can't get the path, continue to next session
                            continue
            
            return matching_tabs
            
        except Exception as e:
            print(f"Warning: Could not search iTerm tabs: {e}", file=sys.stderr)
            return []


    def get_all_git_worktrees(self) -> List[Dict[str, str]]:
        """Get all git worktrees from git command"""
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
                    # Extract folder name from path
                    current_worktree['folder'] = os.path.basename(current_worktree['path'])
                elif line.startswith('branch '):
                    current_worktree['branch'] = line[7:]  # Remove 'branch ' prefix
                elif line.startswith('HEAD '):
                    current_worktree['head'] = line[5:]  # Remove 'HEAD ' prefix
            
            # Add the last worktree if exists
            if current_worktree:
                worktrees.append(current_worktree)
            
            return worktrees
            
        except subprocess.CalledProcessError:
            return []
        except Exception:
            return []

    def validate_worktree_creation(self, branch_name: str, worktree_folder: str) -> tuple[bool, str]:
        """Validate if worktree can be created"""
        # Check if we're in a git repo
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            return False, "Not in a git repository"

        # Check if branch already exists
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

        # Check if worktree folder already exists in parent directory
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_folder)
        if os.path.exists(worktree_path):
            return False, f"Folder '{worktree_folder}' already exists in parent directory"

        return True, "Validation passed"

    def create_worktree(self, branch_name: str, worktree_folder: str) -> tuple[bool, str]:
        """Create the git worktree"""
        try:
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_folder)
            
            # Create worktree with new branch
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, worktree_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            return True, f"Worktree created successfully at {worktree_path}"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create worktree: {e.stderr}"


    async def automate_iterm(self, worktree_folder: str, description: str, start_claude: bool = True) -> tuple[bool, str]:
        """Automate iTerm to open new tab, cd to worktree, start claude, and paste description"""
        try:
            # Connect to iTerm
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Get current window
            window = app.current_window
            if not window:
                return False, "No current iTerm window found"
            
            # Remember the original tab to switch back to
            original_tab = window.current_tab
            
            # Create new tab
            new_tab = await window.async_create_tab()
            session = new_tab.current_session
            
            # Get tab ID for metadata
            tab_id = new_tab.tab_id
            
            # Wait 1 second then cd to worktree
            await asyncio.sleep(1)
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_folder)
            await session.async_send_text(f"cd '{worktree_path}'\n")
            
            # Optionally send claude command with disallowed tools and description as argument
            if start_claude:
                escaped_description = description.replace('"', '\\"')
                await session.async_send_text(f'claude "{escaped_description}" --disallowedTools mcp__worktree__createWorktree,mcp__worktree__closeWorktree,mcp__worktree__activeWorktrees,mcp__worktree__switchToWorktree,mcp__worktree__openWorktree\n')
            
            # Switch back to original tab
            await original_tab.async_select()
            
            return True, "iTerm automation completed successfully"
            
        except Exception as e:
            return False, f"iTerm automation failed: {str(e)}"

    def validate_worktree_closure(self, worktree_name: str) -> tuple[bool, str]:
        """Validate if worktree can be closed (clean and pushed)"""
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        if not os.path.exists(worktree_path):
            return False, f"Worktree '{worktree_name}' does not exist"
        
        try:
            # Check if git status is clean
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                return False, f"Worktree has uncommitted changes: {result.stdout.strip()}"
            
            # Check if all commits are pushed (if upstream exists)
            # First check if there's an upstream branch
            upstream_check = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "@{u}"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            if upstream_check.returncode == 0:
                # Upstream exists, check for unpushed commits
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
                # No upstream, check if there are commits ahead of the base branch
                # First get the base branch (usually main/master)
                base_branch_result = subprocess.run(
                    ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True
                )
                
                if base_branch_result.returncode == 0:
                    # Extract base branch name from refs/remotes/origin/HEAD
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
                        # If we can't determine base branch, allow deletion if working tree is clean
                        return True, "Worktree is clean and can be deleted"
                
                # Check for commits ahead of base branch
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
        """Check if iTerm tab exists"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Find tab by ID
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == tab_id:
                        return True
            
            return False
            
        except Exception as e:
            # If we can't connect to iTerm, assume tab doesn't exist
            return False

    async def close_iterm_tab(self, tab_id: str) -> tuple[bool, str]:
        """Close iTerm tab if it exists"""
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Find tab by ID
            for window in app.windows:
                for tab in window.tabs:
                    if tab.tab_id == tab_id:
                        await tab.async_close()
                        return True, f"Closed tab {tab_id}"
            
            return False, f"Tab {tab_id} not found"
            
        except Exception as e:
            return False, f"Failed to close tab: {str(e)}"

    def check_branch_has_commits(self, worktree_name: str) -> tuple[bool, str]:
        """Check if the worktree's branch has any commits beyond the base branch"""
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        try:
            # Get the current branch name
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()
            
            # Get base branch (usually main/master)
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
        """Delete a git branch"""
        try:
            # Delete the branch
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
        """Handle the closeWorktree tool call"""
        worktree_name = arguments["worktree_name"]
        
        # Step 1: Validate worktree can be closed
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
        
        # Step 2: Check if branch has commits and get branch name
        has_commits, branch_name_or_error = self.check_branch_has_commits(worktree_name)
        branch_to_delete = None
        if isinstance(branch_name_or_error, str) and not has_commits:
            branch_to_delete = branch_name_or_error
        
        # Step 3: Find tab ID dynamically by worktree path
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        tab_id = await self.find_tab_by_path(worktree_path)
        
        # Step 4: Remove worktree
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
        
        # Step 5: Delete branch if it has no commits
        branch_deleted = False
        if branch_to_delete:
            success, delete_msg = self.delete_branch(branch_to_delete)
            branch_deleted = success
        
        # Step 6: Close iTerm tab if it exists
        tab_closed = False
        if tab_id:
            success, tab_msg = await self.close_iterm_tab(tab_id)
            tab_closed = success
        
        # Build success message
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
        """Handle the createWorktree tool call"""
        feature_name = arguments["feature_name"]
        branch_name = arguments["branch_name"] 
        worktree_folder = arguments["worktree_folder"]
        description = arguments["description"]
        
        # Step 0: Validate
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
        
        # Step 1: Create worktree
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
        
        # Steps 2-6: iTerm automation
        start_claude = arguments.get("start_claude", False)  # Default to False to avoid guessing
        success, iterm_msg = await self.automate_iterm(worktree_folder, description, start_claude)
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
        """Handle the listWorktrees tool call"""
        # Get all git worktrees
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
        
        # Check each worktree's tab status dynamically and build response
        response_lines = ["📋 All Git Worktrees:"]
        for i, git_worktree in enumerate(git_worktrees, 1):
            folder = git_worktree.get("folder", "Unknown")
            branch = git_worktree.get("branch", "Unknown")
            path = git_worktree.get("path", "Unknown")
            
            # Find all iTerm2 tabs dynamically by path
            matching_tabs = await self.find_all_tabs_by_path(path)
            
            if matching_tabs:
                # Format tabs info
                tab_info_parts = []
                for tab in matching_tabs:
                    tab_exists = await self.check_iterm_tab_exists(tab["tabId"])
                    tab_status = "✅" if tab_exists else "❌"
                    this_window_indicator = " (thisWindow)" if tab["thisWindow"] else ""
                    tab_info_parts.append(f"Tab: {tab['tabId']}{this_window_indicator} {tab_status}")
                
                tab_info = ", ".join(tab_info_parts)
                response_lines.append(f"  {i}. {folder} (Branch: {branch}, {tab_info})")
            else:
                # No tabs found with this worktree path
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
        """Handle the switchToWorktree tool call"""
        worktree_name = arguments["worktree_name"]
        tab_id = arguments.get("tab_id")
        
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            target_tab_id = None
            
            if tab_id:
                # Tab ID provided - verify it exists
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
                # No tab ID provided - find by worktree path
                parent_dir = os.path.dirname(os.getcwd())
                worktree_path = os.path.join(parent_dir, worktree_name)
                
                # Check if worktree exists
                if not os.path.exists(worktree_path):
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ Worktree '{worktree_name}' does not exist at {worktree_path}"
                            }
                        ]
                    }
                
                # Find tab by worktree path
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
            
            # Find and switch to the target tab
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
            
            # This shouldn't happen if check_iterm_tab_exists worked correctly
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
        """Handle the openWorktree tool call"""
        worktree_name = arguments["worktree_name"]
        force = arguments.get("force", False)
        
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
        
        # Check if worktree is already open in any tabs
        existing_tabs = await self.find_all_tabs_by_path(worktree_path)
        
        if existing_tabs and not force:
            # Worktree is already open and force is not set
            tab_info_parts = []
            for tab in existing_tabs:
                this_window_indicator = " (thisWindow)" if tab["thisWindow"] else ""
                tab_info_parts.append(f"Tab: {tab['tabId']}{this_window_indicator}")
            
            tab_info = ", ".join(tab_info_parts)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"❌ Worktree '{worktree_name}' is already open in {tab_info}. Use force=true to open in a new tab anyway."
                    }
                ]
            }
        
        # Open worktree in new tab
        try:
            connection = await iterm2.Connection.async_create()
            app = await iterm2.async_get_app(connection)
            
            # Get current window
            window = app.current_window
            if not window:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "❌ No current iTerm window found"
                        }
                    ]
                }
            
            # Remember the original tab to switch back to
            original_tab = window.current_tab
            
            # Create new tab
            new_tab = await window.async_create_tab()
            session = new_tab.current_session
            
            # Get tab ID
            tab_id = new_tab.tab_id
            
            # Wait 1 second then cd to worktree
            await asyncio.sleep(1)
            await session.async_send_text(f"cd '{worktree_path}'\n")
            
            # Switch back to original tab
            await original_tab.async_select()
            
            force_message = " (forced)" if force and existing_tabs else ""
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"✅ Opened worktree '{worktree_name}' in new tab {tab_id}{force_message}"
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
    """Handle incoming MCP messages"""
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
    """Main MCP server loop"""
    # Read messages from stdin and write responses to stdout
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            message = json.loads(line.strip())
            response = await handle_message(message)
            
            # Send response with proper MCP format
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