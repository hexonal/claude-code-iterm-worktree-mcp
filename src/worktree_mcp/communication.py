"""
跨会话通信和智能协调功能
"""

import asyncio
import json
import os
import subprocess
from typing import Any, Dict, List, Tuple
from .core import WorktreeManager


class SessionCommunicator:
    """会话间通信管理器"""
    
    def __init__(self):
        self.manager = WorktreeManager()
    
    async def notify_task_complete(self, worktree_name: str, task_summary: str) -> Tuple[bool, str]:
        """通知主会话任务已完成"""
        message = f"#WORKTREE_COMPLETE:{worktree_name}|{task_summary}"
        return await self.manager.send_message_to_main_session(message, worktree_name)
    
    async def notify_merge_ready(self, worktree_name: str, changes_summary: str) -> Tuple[bool, str]:
        """通知主会话代码已准备合并"""
        message = f"#WORKTREE_MERGE_READY:{worktree_name}|{changes_summary}"
        return await self.manager.send_message_to_main_session(message, worktree_name)
    
    def parse_notification_message(self, message: str) -> Dict[str, Any]:
        """解析通知消息"""
        if not message.startswith('#WORKTREE_'):
            return {}
        
        try:
            # 移除 # 前缀
            content = message[1:]
            
            if content.startswith('WORKTREE_COMPLETE:'):
                parts = content[18:].split('|', 1)
                return {
                    'type': 'complete',
                    'worktree_name': parts[0],
                    'task_summary': parts[1] if len(parts) > 1 else ''
                }
            elif content.startswith('WORKTREE_MERGE_READY:'):
                parts = content[21:].split('|', 1)
                return {
                    'type': 'merge_ready',
                    'worktree_name': parts[0],
                    'changes_summary': parts[1] if len(parts) > 1 else ''
                }
        except:
            pass
        
        return {}


class SmartMergeAnalyzer:
    """智能合并分析器"""
    
    def __init__(self):
        self.manager = WorktreeManager()
    
    def analyze_worktree_changes(self, worktree_name: str) -> Dict[str, Any]:
        """分析工作树的代码变更"""
        parent_dir = os.path.dirname(os.getcwd())
        worktree_path = os.path.join(parent_dir, worktree_name)
        
        if not os.path.exists(worktree_path):
            return {"error": f"Worktree '{worktree_name}' does not exist"}
        
        try:
            # 获取变更统计
            diff_stats = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            # 获取变更文件列表
            changed_files = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            
            # 检查测试状态
            test_result = self._run_tests(worktree_path)
            
            # 检查代码质量
            quality_result = self._check_code_quality(worktree_path)
            
            return {
                "worktree_name": worktree_name,
                "diff_stats": diff_stats.stdout.strip(),
                "changed_files": changed_files.stdout.strip().split('\n') if changed_files.stdout.strip() else [],
                "test_status": test_result,
                "quality_status": quality_result,
                "merge_recommendation": self._get_merge_recommendation(test_result, quality_result)
            }
            
        except Exception as e:
            return {"error": f"Failed to analyze changes: {str(e)}"}
    
    def _run_tests(self, worktree_path: str) -> Dict[str, Any]:
        """运行测试检查"""
        # 检查是否有测试命令配置
        test_commands = [
            "npm test",
            "pytest", 
            "python -m pytest",
            "make test"
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(
                    cmd.split(),
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                return {
                    "command": cmd,
                    "success": result.returncode == 0,
                    "output": result.stdout[:1000],  # 限制输出长度
                    "error": result.stderr[:1000] if result.stderr else None
                }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return {"status": "no_tests_found"}
    
    def _check_code_quality(self, worktree_path: str) -> Dict[str, Any]:
        """检查代码质量"""
        quality_checks = []
        
        # Python质量检查
        if self._has_python_files(worktree_path):
            quality_checks.extend([
                ("ruff", "ruff check ."),
                ("black", "black --check ."),
                ("mypy", "mypy .")
            ])
        
        # JavaScript/TypeScript质量检查
        if self._has_js_files(worktree_path):
            quality_checks.extend([
                ("eslint", "npm run lint"),
                ("prettier", "npm run format:check")
            ])
        
        results = []
        for name, cmd in quality_checks:
            try:
                result = subprocess.run(
                    cmd.split(),
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                results.append({
                    "tool": name,
                    "success": result.returncode == 0,
                    "output": result.stdout[:500]
                })
            except:
                continue
        
        return {"checks": results}
    
    def _has_python_files(self, path: str) -> bool:
        """检查是否包含Python文件"""
        try:
            result = subprocess.run(
                ["find", path, "-name", "*.py", "-type", "f"],
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def _has_js_files(self, path: str) -> bool:
        """检查是否包含JavaScript/TypeScript文件"""
        try:
            result = subprocess.run(
                ["find", path, "-name", "*.js", "-o", "-name", "*.ts", "-o", "-name", "*.jsx", "-o", "-name", "*.tsx", "-type", "f"],
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def _get_merge_recommendation(self, test_result: Dict, quality_result: Dict) -> str:
        """基于测试和质量检查结果生成合并建议"""
        if test_result.get("status") == "no_tests_found":
            if not quality_result.get("checks"):
                return "可以合并：未找到测试，但代码变更看起来安全"
            else:
                quality_passed = all(check.get("success", False) for check in quality_result["checks"])
                if quality_passed:
                    return "推荐合并：代码质量检查通过"
                else:
                    return "谨慎合并：代码质量检查有问题，请检查后手动合并"
        
        if test_result.get("success"):
            return "安全合并：所有测试通过"
        else:
            return "禁止合并：测试失败，请修复后重试"


class AutoMergeHandler:
    """自动合并处理器"""
    
    def __init__(self):
        self.manager = WorktreeManager()
        self.analyzer = SmartMergeAnalyzer()
    
    async def handle_task_complete_notification(self, worktree_name: str, task_summary: str) -> Dict[str, Any]:
        """处理任务完成通知并执行自动合并流程"""
        # 分析代码变更
        analysis = self.analyzer.analyze_worktree_changes(worktree_name)
        
        if "error" in analysis:
            return {"success": False, "error": analysis["error"]}
        
        # 根据分析结果决定是否自动合并
        recommendation = analysis.get("merge_recommendation", "")
        
        if "安全合并" in recommendation or "推荐合并" in recommendation:
            # 执行自动合并
            merge_result = await self._execute_auto_merge(worktree_name)
            
            return {
                "success": True,
                "action": "auto_merged",
                "analysis": analysis,
                "merge_result": merge_result
            }
        else:
            # 需要手动干预
            return {
                "success": True,
                "action": "manual_review_required",
                "analysis": analysis,
                "recommendation": recommendation
            }
    
    async def _execute_auto_merge(self, worktree_name: str) -> Dict[str, Any]:
        """执行自动合并流程"""
        try:
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_name)
            
            # 获取当前分支
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=True
            )
            branch_name = branch_result.stdout.strip()
            
            # 切换到主目录并合并
            base_branch = self.manager._get_base_branch(worktree_path) or "main"
            
            # 在主仓库中执行合并
            subprocess.run(["git", "checkout", base_branch], cwd=os.getcwd(), check=True)
            subprocess.run(["git", "pull", "origin", base_branch], cwd=os.getcwd(), check=True)
            subprocess.run(["git", "merge", "--no-ff", branch_name, "-m", f"Merge {branch_name}: {worktree_name}"], cwd=os.getcwd(), check=True)
            
            # 推送合并结果
            subprocess.run(["git", "push", "origin", base_branch], cwd=os.getcwd(), check=True)
            
            # 关闭工作树
            close_result = await self._close_worktree_after_merge(worktree_name)
            
            return {
                "merged_branch": branch_name,
                "target_branch": base_branch,
                "worktree_closed": close_result,
                "status": "success"
            }
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _close_worktree_after_merge(self, worktree_name: str) -> bool:
        """合并后关闭工作树"""
        try:
            # 查找并关闭标签页
            parent_dir = os.path.dirname(os.getcwd())
            worktree_path = os.path.join(parent_dir, worktree_name)
            tab_id = await self.manager.find_tab_by_path(worktree_path)
            
            if tab_id:
                await self.manager.close_iterm_tab(tab_id)
            
            # 移除工作树
            subprocess.run(
                ["git", "worktree", "remove", worktree_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            return True
        except:
            return False