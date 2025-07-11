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
        
        # Ensure .worktree-metadata.json is excluded from git
        self.setup_git_exclude()
        
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
            }
        ]

    def setup_git_exclude(self):
        """Add metadata files to .git/info/exclude if not already there"""
        try:
            # Get git directory
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=True
            )
            git_dir = result.stdout.strip()
            
            # Path to exclude file
            exclude_file = os.path.join(git_dir, "info", "exclude")
            
            # Ensure info directory exists
            info_dir = os.path.dirname(exclude_file)
            os.makedirs(info_dir, exist_ok=True)
            
            # Files to exclude
            exclude_entries = [
                ".worktree-metadata.json",
                ".worktree-manager-metadata.json"
            ]
            
            # Read existing content
            existing_content = ""
            if os.path.exists(exclude_file):
                with open(exclude_file, 'r') as f:
                    existing_content = f.read()
            
            # Add missing entries
            entries_to_add = []
            for entry in exclude_entries:
                if entry not in existing_content:
                    entries_to_add.append(entry)
            
            if entries_to_add:
                with open(exclude_file, 'a') as f:
                    if existing_content and not existing_content.endswith('\n'):
                        f.write('\n')
                    for entry in entries_to_add:
                        f.write(f"{entry}\n")
                
        except Exception as e:
            # Don't fail if we can't set up exclude, just warn
            print(f"Warning: Could not setup git exclude: {e}", file=sys.stderr)

    def get_manager_metadata_path(self) -> str:
        """Get the path to the manager metadata file"""
        return os.path.join(os.getcwd(), ".worktree-manager-metadata.json")

    def load_manager_metadata(self) -> dict:
        """Load manager metadata, create if doesn't exist"""
        metadata_path = self.get_manager_metadata_path()
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"worktrees": []}

    def save_manager_metadata(self, metadata: dict) -> bool:
        """Save manager metadata"""
        try:
            metadata_path = self.get_manager_metadata_path()
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            return True
        except:
            return False

    def add_worktree_to_manager(self, worktree_folder: str, tab_id: str) -> bool:
        """Add worktree to manager metadata"""
        metadata = self.load_manager_metadata()
        
        # Remove existing entry if it exists
        metadata["worktrees"] = [w for w in metadata["worktrees"] if w["folder"] != worktree_folder]
        
        # Add new entry
        metadata["worktrees"].append({
            "folder": worktree_folder,
            "tabId": tab_id
        })
        
        return self.save_manager_metadata(metadata)

    def remove_worktree_from_manager(self, worktree_folder: str) -> bool:
        """Remove worktree from manager metadata"""
        metadata = self.load_manager_metadata()
        metadata["worktrees"] = [w for w in metadata["worktrees"] if w["folder"] != worktree_folder]
        return self.save_manager_metadata(metadata)

    def get_worktree_tab_id(self, worktree_folder: str) -> Optional[str]:
        """Get tab ID for a worktree"""
        metadata = self.load_manager_metadata()
        for worktree in metadata["worktrees"]:
            if worktree["folder"] == worktree_folder:
                return worktree["tabId"]
        return None

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

    def create_worktree_metadata(self, worktree_folder: str, tab_id: str) -> tuple[bool, str]:
        """Create .worktree-metadata.json file and configure git to skip it"""
        try:
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_folder)
            metadata_file = os.path.join(worktree_path, ".worktree-metadata.json")
            
            # Get parent worktree folder (the current directory name)
            parent_worktree_folder = os.path.basename(os.getcwd())
            
            # Create metadata
            metadata = {
                "parentWorktreeFolder": parent_worktree_folder,
                "worktreeItermTabId": tab_id
            }
            
            # Write metadata file
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True, f"Created metadata file at {metadata_file}"
        except Exception as e:
            return False, f"Failed to create metadata file: {str(e)}"

    async def automate_iterm(self, worktree_folder: str, description: str) -> tuple[bool, str]:
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
            
            # Send claude command with disallowed tools
            await session.async_send_text("claude --disallowedTools mcp__worktree__createWorktree,mcp__worktree__closeWorktree,mcp__worktree__activeWorktrees\n")
            
            # Wait 1 second then send return key
            await asyncio.sleep(1)
            await session.async_send_text("\r")
            
            # Paste description
            await session.async_send_text(description)
            
            # Wait 0.5 seconds then send return key again
            await asyncio.sleep(0.5)
            await session.async_send_text("\r")
            
            # Create metadata file
            metadata_success, metadata_msg = self.create_worktree_metadata(worktree_folder, tab_id)
            if not metadata_success:
                # Don't fail the whole operation, just log the issue
                print(f"Warning: {metadata_msg}", file=sys.stderr)
            
            # Add to manager metadata
            manager_success = self.add_worktree_to_manager(worktree_folder, tab_id)
            if not manager_success:
                print(f"Warning: Failed to update manager metadata", file=sys.stderr)
            
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
                # No upstream, check if there are any commits at all
                result = subprocess.run(
                    ["git", "log", "--oneline", "HEAD"],
                    cwd=worktree_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return False, f"Branch has commits but no upstream configured. Push the branch first or use --force"
            
            return True, "Worktree is clean and pushed"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check worktree status: {e.stderr}"

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
        
        # Step 2: Get tab ID before removing from manager
        tab_id = self.get_worktree_tab_id(worktree_name)
        
        # Step 3: Remove worktree
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
        
        # Step 4: Close iTerm tab if it exists
        tab_closed = False
        if tab_id:
            success, tab_msg = await self.close_iterm_tab(tab_id)
            tab_closed = success
        
        # Step 5: Remove from manager metadata
        self.remove_worktree_from_manager(worktree_name)
        
        # Build success message
        message = f"✅ Successfully closed worktree '{worktree_name}'"
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
        success, iterm_msg = await self.automate_iterm(worktree_folder, description)
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

    async def handle_active_worktrees(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the activeWorktrees tool call"""
        metadata = self.load_manager_metadata()
        worktrees = metadata.get("worktrees", [])
        
        if not worktrees:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "📝 No active worktrees found"
                    }
                ]
            }
        
        # Build the response with worktree details
        response_lines = ["📋 Active Worktrees:"]
        for i, worktree in enumerate(worktrees, 1):
            folder = worktree.get("folder", "Unknown")
            tab_id = worktree.get("tabId", "Unknown")
            response_lines.append(f"  {i}. {folder} (Tab: {tab_id})")
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": "\n".join(response_lines)
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
            return await server.handle_active_worktrees(arguments)
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