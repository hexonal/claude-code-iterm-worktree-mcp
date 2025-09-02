#!/usr/bin/env python3
"""
测试多会话环境下的精准通信机制
"""

import asyncio
import time
from src.worktree_mcp.core import WorktreeManager
from src.worktree_mcp.session_manager import ClaudeSessionManager
from src.worktree_mcp.models import WorktreeSessionMapping

async def test_session_mapping():
    """测试会话映射功能"""
    print("=== 多会话通信测试 ===\n")
    
    # 创建管理器实例
    worktree_manager = WorktreeManager()
    session_manager = ClaudeSessionManager()
    
    # 获取当前会话信息
    current_session = session_manager.get_current_session_id()
    print(f"1. 当前会话检测:")
    print(f"   会话 ID: {current_session.session_id}")
    print(f"   检测成功: {current_session.success}")
    
    if not current_session.success:
        print("❌ 无法获取当前会话，跳过映射测试")
        return
    
    # 模拟创建多个工作树的会话映射
    print(f"\n2. 模拟多工作树会话映射:")
    
    # 创建测试映射
    test_mappings = [
        WorktreeSessionMapping(
            worktree_name="myapp-feat-auth",
            creator_session_id=current_session.session_id,
            created_at=str(int(time.time())),
            creator_tab_id="test-tab-1",
            creator_working_dir="/Users/flink/projects/myapp"
        ),
        WorktreeSessionMapping(
            worktree_name="myapp-feat-payment",
            creator_session_id="claude-code-9999999999-other",
            created_at=str(int(time.time())),
            creator_tab_id="test-tab-2", 
            creator_working_dir="/Users/flink/projects/myapp"
        )
    ]
    
    # 保存测试映射
    for mapping in test_mappings:
        success = worktree_manager.save_worktree_session_mapping(mapping)
        print(f"   保存映射 {mapping.worktree_name}: {'✅' if success else '❌'}")
    
    # 测试映射查询
    print(f"\n3. 测试映射查询:")
    for worktree_name in ["myapp-feat-auth", "myapp-feat-payment"]:
        mapping = worktree_manager.get_worktree_creator_session(worktree_name)
        if mapping:
            print(f"   {worktree_name} -> {mapping.creator_session_id}")
        else:
            print(f"   {worktree_name} -> 未找到映射")
    
    # 测试精准通信路由
    print(f"\n4. 测试精准通信路由:")
    
    # 测试向当前会话的 worktree 发送消息（应该能找到）
    success, msg = await worktree_manager.send_message_to_main_session(
        "测试消息：来自 myapp-feat-auth", 
        "myapp-feat-auth"
    )
    print(f"   向 myapp-feat-auth 创建会话发送: {'✅' if success else '❌'} - {msg}")
    
    # 测试向其他会话的 worktree 发送消息（应该找不到，使用备选方案）
    success, msg = await worktree_manager.send_message_to_main_session(
        "测试消息：来自 myapp-feat-payment", 
        "myapp-feat-payment"
    )
    print(f"   向 myapp-feat-payment 创建会话发送: {'✅' if success else '❌'} - {msg}")
    
    # 清理测试数据
    print(f"\n5. 清理测试数据:")
    for worktree_name in ["myapp-feat-auth", "myapp-feat-payment"]:
        success = worktree_manager.cleanup_session_mapping(worktree_name)
        print(f"   清理 {worktree_name}: {'✅' if success else '❌'}")

if __name__ == "__main__":
    asyncio.run(test_session_mapping())