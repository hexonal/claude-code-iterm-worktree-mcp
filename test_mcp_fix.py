#!/usr/bin/env python3
"""
MCP 服务器修复验证测试

此文件用于验证 MCP 服务器事件循环冲突修复是否成功。
"""

import sys
import subprocess
import json

def test_mcp_server_initialization():
    """测试 MCP 服务器初始化"""
    print("🧪 测试 MCP 服务器初始化...")
    
    # 创建初始化消息
    init_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        # 运行 MCP 服务器并发送初始化消息
        result = subprocess.run(
            [sys.executable, "worktree_mcp_server.py"],
            input=json.dumps(init_message) + "\n",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            response = json.loads(result.stdout.strip())
            print(f"✅ 初始化成功: {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
            return True
        else:
            print(f"❌ 初始化失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解码失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False

def test_tools_list():
    """测试工具列表"""
    print("🧪 测试工具列表...")
    
    tools_message = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    try:
        result = subprocess.run(
            [sys.executable, "worktree_mcp_server.py"],
            input=json.dumps(tools_message) + "\n",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            response = json.loads(result.stdout.strip())
            tools = response.get('result', {}).get('tools', [])
            print(f"✅ 发现 {len(tools)} 个工具:")
            for tool in tools:
                print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            return True
        else:
            print(f"❌ 工具列表获取失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始 MCP 服务器修复验证测试")
    print("=" * 50)
    
    # 运行测试
    init_success = test_mcp_server_initialization()
    tools_success = test_tools_list()
    
    print("=" * 50)
    if init_success and tools_success:
        print("🎉 所有测试通过！MCP 服务器修复成功！")
        return 0
    else:
        print("💥 部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    exit(main())