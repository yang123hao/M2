#!/usr/bin/env python3
"""
简化的带认证的 MinerU 应用
使用内置的 HTTP 服务器，避免所有外部依赖问题
"""

import os
import sys
import logging
import json
import hashlib
import time
import hmac
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import tempfile
import uuid

logger = logging.getLogger(__name__)

# 配置上传
UPLOAD_FOLDER = '/tmp/mineru_uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class SimpleAuth:
    """简单的认证管理器"""
    def __init__(self):
        self.secret_key = hashlib.sha256("mineru_auth_secret_2025".encode()).hexdigest()
        self.credentials = {
            'administrator': '@worklan18'
        }
    
    def verify_credentials(self, username, password):
        """验证用户凭据"""
        return username in self.credentials and self.credentials[username] == password
    
    def generate_token(self, username):
        """生成简单的令牌"""
        timestamp = str(int(time.time()))
        message = f"{username}:{timestamp}"
        signature = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
        return f"{message}.{signature}"
    
    def verify_token(self, token):
        """验证令牌"""
        try:
            parts = token.split('.')
            if len(parts) != 2:
                return None
            
            message, signature = parts
            username, timestamp = message.split(':')
            
            # 检查时间戳（24小时有效期）
            if int(time.time()) - int(timestamp) > 24 * 3600:
                return None
            
            # 验证签名
            expected_signature = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                return username
            
            return None
        except:
            return None

class SimpleAuthHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, auth_manager=None, **kwargs):
        self.auth_manager = auth_manager
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_main_page().encode('utf-8'))
        elif path == '/login':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_login_page().encode('utf-8'))
        elif path == '/auth/verify':
            self.handle_auth_verify()
        elif path == '/gradio':
            self.handle_gradio_app()
        elif path == '/app':
            self.handle_gradio_route()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/auth/login':
            self.handle_login()
        elif path == '/auth/logout':
            self.handle_logout()
        elif path == '/api/process':
            self.handle_file_process()
        elif path == '/api/start_gradio':
            self.handle_start_gradio()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_OPTIONS(self):
        """处理 OPTIONS 请求（CORS 预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()
    
    def handle_auth_verify(self):
        """验证认证状态"""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            username = self.auth_manager.verify_token(token) if self.auth_manager else None
            if username:
                self.send_json_response({'valid': True, 'username': username})
                return
        
        self.send_json_response({'valid': False}, 401)
    
    def handle_login(self):
        """处理登录请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            # 检查 Content-Type 来决定如何解析数据
            content_type = self.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                # 处理 JSON 格式的请求
                data = json.loads(post_data.decode('utf-8'))
                username = data.get('username', '')
                password = data.get('password', '')
            else:
                # 处理表单格式的请求
                data = parse_qs(post_data.decode('utf-8'))
                username = data.get('username', [''])[0]
                password = data.get('password', [''])[0]
            
            # 从环境变量获取凭据
            import os
            env_username = os.environ.get('MANAGEMENT_ADMIN_USERNAME', 'administrator')
            env_password = os.environ.get('MANAGEMENT_ADMIN_PASSWORD', '@worklan18')
            
            if username == env_username and password == env_password:
                # 登录成功，生成 token
                token = self.auth_manager.generate_token(username)
                
                if 'application/json' in content_type:
                    # JSON 响应，同时设置cookie
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.send_header('Set-Cookie', f'mineru_auth_token={token}; Path=/; HttpOnly')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'token': token,
                        'message': '登录成功'
                    }, ensure_ascii=False).encode('utf-8'))
                else:
                    # 重定向响应
                    self.send_response(302)
                    self.send_header('Set-Cookie', f'mineru_auth_token={token}; Path=/; HttpOnly')
                    self.send_header('Location', '/api/start_gradio')
                    self.end_headers()
            else:
                # 登录失败
                if 'application/json' in content_type:
                    self.send_json_response({
                        'success': False,
                        'message': '用户名或密码错误'
                    }, 401)
                else:
                    self.send_response(302)
                    self.send_header('Location', '/login?error=invalid_credentials')
                    self.end_headers()
                
        except Exception as e:
            logger.error(f"登录处理错误: {e}")
            if 'application/json' in self.headers.get('Content-Type', ''):
                self.send_json_response({
                    'success': False,
                    'message': f'服务器错误: {str(e)}'
                }, 500)
            else:
                self.send_response(302)
                self.send_header('Location', '/login?error=server_error')
                self.end_headers()
    
    def handle_logout(self):
        """处理登出请求"""
        self.send_json_response({'success': True, 'message': '已登出'})
    
    def handle_file_process(self):
        """处理文件上传"""
        # 简化的文件处理演示
        self.send_json_response({
            'success': True,
            'message': '文件处理成功（演示）',
            'file_id': str(uuid.uuid4())
        })
    
    def handle_start_gradio(self):
        """处理启动 Gradio 应用的请求"""
        try:
            # 直接返回路由信息
            self.send_json_response({
                'success': True,
                'message': 'MinerU 应用已准备就绪',
                'gradio_url': '/app',
                'route': '/app'
            })
                
        except Exception as e:
            self.send_json_response({
                'success': False,
                'message': f'启动失败: {str(e)}'
            })
    
    def handle_gradio_app(self):
        """处理直接集成 Gradio 应用的请求"""
        try:
            # 直接返回 Gradio 应用的 HTML 内容
            gradio_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>MinerU Gradio App</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { margin: 0; padding: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
                    .gradio-container { width: 100%; height: 100vh; }
                </style>
            </head>
            <body>
                <div class="gradio-container">
                    <h2 style="text-align: center; padding: 20px; background: #f0f0f0;">
                        MinerU PDF 提取工具 - 本地集成版本
                    </h2>
                    <div style="padding: 20px;">
                        <p>这里是 MinerU 的 Gradio 应用界面。</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(gradio_html.encode('utf-8'))
                
        except Exception as e:
            self.send_json_response({
                'success': False,
                'message': f'加载失败: {str(e)}'
            })
    
    def handle_gradio_route(self):
        """处理 Gradio 应用路由请求"""
        try:
            # 检查认证状态
            auth_header = self.headers.get('Authorization')
            token = None
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                # 检查cookie
                cookie_header = self.headers.get('Cookie', '')
                if 'mineru_auth_token=' in cookie_header:
                    # 从cookie中提取token
                    cookies = cookie_header.split(';')
                    for cookie in cookies:
                        if 'mineru_auth_token=' in cookie:
                            token = cookie.split('=')[1].strip()
                            break
            
            # 验证token
            if token and self.auth_manager.verify_token(token):
                # 启动Gradio应用并返回嵌入页面
                self.start_gradio_embedded()
            else:
                # 未认证，重定向到登录页面
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
                
        except Exception as e:
            self.send_json_response({
                'success': False,
                'message': f'启动失败: {str(e)}'
            })
    
    def start_gradio_embedded(self):
        """启动Gradio应用并重定向到根路径"""
        try:
            # 直接重定向到根路径，让Gradio应用处理
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            
        except Exception as e:
            logger.error(f"启动Gradio应用失败: {e}")
            # 如果启动失败，返回错误页面
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>MinerU 启动失败</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: red; background: #ffe6e6; padding: 20px; border-radius: 10px; margin: 20px; }}
                    .back-btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>❌ MinerU 启动失败</h1>
                <div class="error">
                    <h3>错误信息:</h3>
                    <p>{str(e)}</p>
                </div>
                <a href="/" class="back-btn">返回主页</a>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(error_html.encode('utf-8'))
    
    def send_json_response(self, data, status_code=200):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def get_login_page(self):
        """获取登录页面 HTML"""
        try:
            login_file = os.path.join(os.path.dirname(__file__), '..', 'resources', 'login.html')
            with open(login_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"加载登录页面失败: {e}")
            return self.get_simple_login_page()
    
    def get_simple_login_page(self):
        """简单的登录页面（备用）"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MinerU 登录</title>
            <style>
                body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f0f0; margin: 0; padding: 20px; }
                .login-container { max-width: 400px; margin: 100px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                button:hover { background: #0056b3; }
                .error { color: red; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="login-container">
                <h2 style="text-align: center; color: #007bff;">MinerU 登录</h2>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="username">用户名</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">密码</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit">登录</button>
                    <div id="errorMessage" class="error" style="display: none;"></div>
                </form>
            </div>
            <script>
                document.getElementById('loginForm').onsubmit = async function(e) {
                    e.preventDefault();
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    const errorElement = document.getElementById('errorMessage');
                    
                    // 清除之前的错误信息
                    errorElement.style.display = 'none';
                    errorElement.textContent = '';
                    
                    // 显示加载状态
                    const submitBtn = document.querySelector('button[type="submit"]');
                    const originalText = submitBtn.textContent;
                    submitBtn.textContent = '登录中...';
                    submitBtn.disabled = true;
                    
                    try {
                        const response = await fetch('/auth/login', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            },
                            body: JSON.stringify({username, password})
                        });
                        
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            localStorage.setItem('mineru_auth_token', result.token);
                            window.location.href = '/';
                        } else {
                            errorElement.textContent = result.message || '登录失败';
                            errorElement.style.display = 'block';
                        }
                    } catch (error) {
                        console.error('登录错误:', error);
                        let errorMsg = '网络错误，请稍后重试';
                        
                        if (error.message.includes('Failed to fetch')) {
                            errorMsg = '无法连接到服务器，请检查网络连接';
                        } else if (error.message.includes('HTTP')) {
                            errorMsg = `服务器错误: ${error.message}`;
                        }
                        
                        errorElement.textContent = errorMsg;
                        errorElement.style.display = 'block';
                    } finally {
                        // 恢复按钮状态
                        submitBtn.textContent = originalText;
                        submitBtn.disabled = false;
                    }
                };
            </script>
        </body>
        </html>
        """
    
    def get_main_page(self):
        """获取主页面 HTML"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MinerU PDF 提取工具</title>
            <style>
                body { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); margin: 0; padding: 20px; min-height: 100vh; }
                .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
                .header { background: linear-gradient(45deg, #007bff 0%, #0056b3 100%); color: white; padding: 30px; text-align: center; }
                .header h1 { margin: 0; font-size: 2.5rem; }
                .content { padding: 30px; }
                .start-btn { background: linear-gradient(45deg, #007bff 0%, #0056b3 100%); color: white; padding: 15px 30px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; margin: 20px 0; }
                .start-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0, 123, 255, 0.3); }
                .logout-btn { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 6px; text-decoration: none; }
                .logout-btn:hover { background: rgba(255,255,255,0.3); }
                .status { text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <a href="/auth/logout" class="logout-btn" onclick="return handleLogout()">登出</a>
                <div class="header">
                    <h1>📄 MinerU</h1>
                    <p>高质量 PDF 提取工具</p>
                </div>
                <div class="content">
                    <div class="status">
                        <h3>🎉 登录成功！</h3>
                        <p>欢迎使用 MinerU PDF 提取工具</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <button class="start-btn" onclick="startGradioApp()">
                            🚀 启动 MinerU 应用
                        </button>
                    </div>
                    
                    <div id="statusMessage" style="text-align: center; margin-top: 20px; display: none;">
                        <p>正在启动 MinerU 应用，请稍候...</p>
                    </div>
                </div>
            </div>
            <script>
                function handleLogout() {
                    fetch('/auth/logout', {method: 'POST'})
                        .then(() => {
                            localStorage.removeItem('mineru_auth_token');
                            window.location.href = '/login';
                        });
                    return false;
                }
                
                function startGradioApp() {
                    document.getElementById('statusMessage').style.display = 'block';
                    
                    // 直接跳转到Gradio应用路由
                    window.location.href = '/app';
                }
            </script>
        </body>
        </html>
        """
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.address_string()} - {format % args}")

def create_server(host='0.0.0.0', port=7861):
    """创建 HTTP 服务器"""
    auth_manager = SimpleAuth()
    
    class Handler(SimpleAuthHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, auth_manager=auth_manager, **kwargs)
    
    server = HTTPServer((host, port), Handler)
    return server

def main():
    """主函数"""
    import argparse
    import socket
    
    parser = argparse.ArgumentParser(description="MinerU Simple Auth App")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=7861, help="Port number")
    
    args = parser.parse_args()
    
    # 检查端口是否可用
    def is_port_available(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((args.host, port))
                return True
            except OSError:
                return False
    
    # 如果默认端口被占用，尝试其他端口
    port = args.port
    if not is_port_available(port):
        print(f"端口 {port} 已被占用，尝试其他端口...")
        for alt_port in range(7862, 7870):
            if is_port_available(alt_port):
                port = alt_port
                print(f"使用端口 {port}")
                break
        else:
            print("无法找到可用端口，退出")
            return
    
    server = create_server(args.host, port)
    
    print(f"启动 MinerU 认证应用")
    print(f"访问地址: http://{args.host}:{port}")
    print("请先访问 /login 进行登录")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()

if __name__ == "__main__":
    main()
