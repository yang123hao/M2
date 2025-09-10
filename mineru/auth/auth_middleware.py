#!/usr/bin/env python3
"""
MinerU 认证中间件
用于处理登录验证和权限控制
"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, env_path="docker/.env"):
        self.env_path = env_path
        self.secret_key = self._generate_secret_key()
        self.load_credentials()
    
    def _generate_secret_key(self):
        """生成JWT密钥"""
        return hashlib.sha256("mineru_auth_secret_2025".encode()).hexdigest()
    
    def load_credentials(self):
        """从.env文件加载用户凭据"""
        self.credentials = {}
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", self.env_path)
        
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if key == 'MANAGEMENT_ADMIN_USERNAME':
                                self.admin_username = value
                            elif key == 'MANAGEMENT_ADMIN_PASSWORD':
                                self.admin_password = value
        
        # 设置默认凭据
        if hasattr(self, 'admin_username') and hasattr(self, 'admin_password'):
            self.credentials[self.admin_username] = self.admin_password
        else:
            # 备用凭据
            self.credentials['admin'] = 'mineru123'
        
        logger.info(f"已加载 {len(self.credentials)} 个用户凭据")
    
    def verify_credentials(self, username, password):
        """验证用户凭据"""
        return username in self.credentials and self.credentials[username] == password
    
    def generate_token(self, username):
        """生成JWT令牌"""
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['username']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

# 全局认证管理器实例
auth_manager = AuthManager()

def require_auth(f):
    """装饰器：要求身份验证"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查Authorization头
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            username = auth_manager.verify_token(token)
            if username:
                request.current_user = username
                return f(*args, **kwargs)
        
        # 检查session中的token
        session_token = request.cookies.get('mineru_auth_token')
        if session_token:
            username = auth_manager.verify_token(session_token)
            if username:
                request.current_user = username
                return f(*args, **kwargs)
        
        # 未授权访问
        return jsonify({'error': '未授权访问', 'redirect': '/login'}), 401
    
    return decorated_function

def setup_auth_routes(app):
    """设置认证相关的路由"""
    
    @app.route('/login')
    def login_page():
        """显示登录页面"""
        try:
            login_file = os.path.join(os.path.dirname(__file__), '..', 'resources', 'login.html')
            with open(login_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载登录页面失败: {e}")
            return "登录页面加载失败", 500
    
    @app.route('/auth/login', methods=['POST'])
    def api_login():
        """处理登录请求"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
            
            if auth_manager.verify_credentials(username, password):
                token = auth_manager.generate_token(username)
                response = jsonify({
                    'success': True, 
                    'message': '登录成功',
                    'token': token,
                    'username': username
                })
                # 设置cookie
                response.set_cookie('mineru_auth_token', token, max_age=24*60*60, httponly=True)
                return response
            else:
                return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
                
        except Exception as e:
            logger.error(f"登录处理失败: {e}")
            return jsonify({'success': False, 'message': '服务器内部错误'}), 500
    
    @app.route('/auth/verify')
    def verify_auth():
        """验证当前登录状态"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            username = auth_manager.verify_token(token)
            if username:
                return jsonify({'valid': True, 'username': username})
        
        session_token = request.cookies.get('mineru_auth_token')
        if session_token:
            username = auth_manager.verify_token(session_token)
            if username:
                return jsonify({'valid': True, 'username': username})
        
        return jsonify({'valid': False}), 401
    
    @app.route('/auth/logout', methods=['POST'])
    def logout():
        """登出"""
        response = jsonify({'success': True, 'message': '已登出'})
        response.set_cookie('mineru_auth_token', '', expires=0)
        return response

if __name__ == "__main__":
    # 测试认证管理器
    auth = AuthManager()
    print("测试认证系统...")
    print(f"凭据: {auth.credentials}")
    
    # 测试验证
    test_user = list(auth.credentials.keys())[0]
    test_pass = auth.credentials[test_user]
    
    if auth.verify_credentials(test_user, test_pass):
        token = auth.generate_token(test_user)
        print(f"生成的令牌: {token}")
        
        verified_user = auth.verify_token(token)
        print(f"验证结果: {verified_user}")
    else:
        print("凭据验证失败")
