#!/usr/bin/env python3
"""
测试路由访问Gradio应用的功能
"""

import requests
import json

def test_route_app():
    """测试路由访问Gradio应用"""
    base_url = "http://localhost:7861"
    
    print("🧪 开始测试路由访问Gradio应用...")
    
    # 测试 1: 未认证访问 /app 路由
    try:
        response = requests.get(f"{base_url}/app", allow_redirects=False)
        if response.status_code == 302:
            print("✅ 未认证访问 /app 正确重定向到登录页面")
        else:
            print(f"❌ 未认证访问 /app 状态码错误: {response.status_code}")
    except Exception as e:
        print(f"❌ 未认证访问 /app 错误: {e}")
    
    # 测试 2: 登录获取令牌
    try:
        login_data = {
            "username": "administrator",
            "password": "@worklan18"
        }
        
        response = requests.post(
            f"{base_url}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                token = result.get("token")
                print("✅ 登录成功，获得令牌")
                
                # 测试 3: 使用令牌访问 /app 路由
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{base_url}/app", headers=headers)
                
                if response.status_code == 200:
                    print("✅ 使用令牌访问 /app 路由成功")
                    if "MinerU PDF 提取工具" in response.text:
                        print("✅ 返回了正确的Gradio应用页面")
                    else:
                        print("❌ 返回的页面内容不正确")
                else:
                    print(f"❌ 使用令牌访问 /app 失败: {response.status_code}")
            else:
                print(f"❌ 登录失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 登录请求失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试过程错误: {e}")
    
    # 测试 4: 测试启动API
    try:
        response = requests.post(f"{base_url}/api/start_gradio")
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 启动API返回正确")
                if result.get("route") == "/app":
                    print("✅ 返回了正确的路由信息")
                else:
                    print("❌ 返回的路由信息不正确")
            else:
                print(f"❌ 启动API失败: {result.get('message', '未知错误')}")
        else:
            print(f"❌ 启动API请求失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 启动API测试错误: {e}")
    
    print("\n🎉 路由测试完成！")

if __name__ == "__main__":
    test_route_app()
