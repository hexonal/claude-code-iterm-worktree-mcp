#!/usr/bin/env python3
"""
测试合并流程的功能文件
"""

def test_feature_function():
    """新功能测试函数"""
    return "This is a test feature for merge flow testing"

def calculate_multiply(a, b):
    """计算两个数的乘积"""
    return a * b

def greeting_message(name):
    """生成问候消息"""
    return f"Hello, {name}! Welcome to the test feature."

if __name__ == "__main__":
    print(test_feature_function())
    print(f"5 * 6 = {calculate_multiply(5, 6)}")
    print(greeting_message("Claude"))