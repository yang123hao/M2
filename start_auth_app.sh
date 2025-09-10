#!/bin/bash
# MinerU 认证应用启动脚本

echo "🚀 启动 MinerU 认证应用..."

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到，请先安装 Python3"
    exit 1
fi

# 检查应用文件是否存在
if [ ! -f "mineru/cli/simple_auth_app.py" ]; then
    echo "❌ 找不到 simple_auth_app.py 文件"
    exit 1
fi

# 设置环境变量（可选）
export MANAGEMENT_ADMIN_USERNAME="administrator"
export MANAGEMENT_ADMIN_PASSWORD="@worklan18"

# 启动应用
echo "📡 启动服务器..."
echo "   访问地址: http://localhost:7861"
echo "   登录页面: http://localhost:7861/login"
echo "   默认用户名: administrator"
echo "   默认密码: @worklan18"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

python3 mineru/cli/simple_auth_app.py --host 0.0.0.0 --port 7861
