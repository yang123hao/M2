#!/usr/bin/env python3
"""
测试 simple_auth_app.py 的修复
"""

import requests
import json
import time

def test_auth_app():
    """测试认证应用"""
    base_url = "http://localhost:7861"
    
    print("🧪 开始测试 MinerU 认证应用...")
    
    # 测试 1: 检查服务器是否运行
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ 服务器运行正常 (状态码: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 服务器连接失败: {e}")
        return False
    
    # 测试 2: 检查登录页面
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        if response.status_code == 200:
            print("✅ 登录页面可访问")
        else:
            print(f"❌ 登录页面访问失败 (状态码: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 登录页面访问错误: {e}")
    
    # 测试 3: 测试登录功能
    try:
        login_data = {
            "username": "administrator",
            "password": "@worklan18"
        }
        
        response = requests.post(
            f"{base_url}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 登录功能正常")
                print(f"   获得令牌: {result.get('token', '')[:20]}...")
            else:
                print(f"❌ 登录失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 登录请求失败 (状态码: {response.status_code})")
            print(f"   响应内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 登录请求错误: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
    
    # 测试 4: 测试 CORS 预检
    try:
        response = requests.options(f"{base_url}/auth/login", timeout=5)
        if response.status_code == 200:
            print("✅ CORS 预检正常")
        else:
            print(f"❌ CORS 预检失败 (状态码: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ CORS 预检错误: {e}")
    
    print("\n🎉 测试完成！")
    return True

if __name__ == "__main__":
    test_auth_app()
