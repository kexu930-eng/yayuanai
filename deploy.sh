#!/bin/bash

# 任务分配系统一键部署脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "     任务分配系统 - 一键部署脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📍 当前目录: $SCRIPT_DIR${NC}"
echo ""

# 激活conda环境
echo -e "${BLUE}🐍 激活conda环境...${NC}"
if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate xk
    echo -e "${GREEN}✅ conda环境 'xk' 已激活${NC}"
elif [ -f "/root/anaconda3/etc/profile.d/conda.sh" ]; then
    source /root/anaconda3/etc/profile.d/conda.sh
    conda activate xk
    echo -e "${GREEN}✅ conda环境 'xk' 已激活${NC}"
else
    echo -e "${YELLOW}⚠️  未找到conda，使用系统Python${NC}"
fi

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 权限检查通过${NC}"

# ==================== 步骤1: 安装系统依赖 ====================
echo ""
echo -e "${BLUE}📦 步骤1: 安装系统依赖...${NC}"

# 检查并安装Python3
if ! command -v python3 &> /dev/null; then
    echo "安装 Python3..."
    yum install -y python3 python3-pip
else
    echo -e "${GREEN}✅ Python3 已安装${NC}"
fi

# 检查并安装pip
if ! command -v pip3 &> /dev/null; then
    echo "安装 pip3..."
    yum install -y python3-pip
else
    echo -e "${GREEN}✅ pip3 已安装${NC}"
fi

# 检查并安装Nginx
if ! command -v nginx &> /dev/null; then
    echo "安装 Nginx..."
    yum install -y nginx
    systemctl enable nginx
else
    echo -e "${GREEN}✅ Nginx 已安装${NC}"
fi

# 检查并安装Supervisor
if ! command -v supervisord &> /dev/null; then
    echo "安装 Supervisor..."
    yum install -y supervisor
    systemctl enable supervisord
else
    echo -e "${GREEN}✅ Supervisor 已安装${NC}"
fi

# ==================== 步骤2: 创建目录 ====================
echo ""
echo -e "${BLUE}📁 步骤2: 创建必要目录...${NC}"

mkdir -p logs
mkdir -p /etc/supervisor/conf.d
mkdir -p /etc/nginx/conf.d

echo -e "${GREEN}✅ 目录创建完成${NC}"

# ==================== 步骤3: 安装Python依赖 ====================
echo ""
echo -e "${BLUE}📦 步骤3: 安装Python依赖...${NC}"

if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    echo -e "${GREEN}✅ Python依赖安装完成${NC}"
else
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

# ==================== 步骤4: 初始化数据库 ====================
echo ""
echo -e "${BLUE}💾 步骤4: 初始化数据库...${NC}"

python3 << EOF
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ 数据库初始化完成")
EOF

echo -e "${GREEN}✅ 数据库创建成功${NC}"

# ==================== 步骤5: 配置Supervisor ====================
echo ""
echo -e "${BLUE}⚙️  步骤5: 配置Supervisor...${NC}"

# 复制Supervisor配置
cp supervisor_config.conf /etc/supervisor/conf.d/task_distribute.conf

# 重新加载Supervisor配置
systemctl restart supervisord
sleep 2
supervisorctl reread
supervisorctl update

echo -e "${GREEN}✅ Supervisor配置完成${NC}"

# ==================== 步骤6: 配置Nginx ====================
echo ""
echo -e "${BLUE}⚙️  步骤6: 配置Nginx...${NC}"

# 复制Nginx配置
cp nginx_config.conf /etc/nginx/conf.d/task_distribute.conf

# 测试Nginx配置
nginx -t

if [ $? -eq 0 ]; then
    # 重启Nginx
    systemctl restart nginx
    echo -e "${GREEN}✅ Nginx配置完成${NC}"
else
    echo -e "${RED}❌ Nginx配置测试失败${NC}"
    exit 1
fi

# ==================== 步骤7: 启动服务 ====================
echo ""
echo -e "${BLUE}🚀 步骤7: 启动服务...${NC}"

# 先停止已存在的服务
if supervisorctl status task_distribute 2>/dev/null | grep -q -E "RUNNING|STARTING"; then
    echo -e "${YELLOW}检测到服务已在运行，先停止...${NC}"
    supervisorctl stop task_distribute
    sleep 2
fi

# 启动服务
echo "启动服务..."
supervisorctl start task_distribute

# 等待服务启动（最多等待30秒）
echo -n "等待服务启动"
for i in {1..30}; do
    sleep 1
    echo -n "."
    if supervisorctl status task_distribute 2>/dev/null | grep -q "RUNNING"; then
        echo ""
        echo -e "${GREEN}✅ 应用启动成功${NC}"
        break
    fi
    
    # 如果超过30秒还没启动，报错
    if [ $i -eq 30 ]; then
        echo ""
        echo -e "${RED}❌ 应用启动超时${NC}"
        supervisorctl status task_distribute
        echo ""
        echo -e "${YELLOW}查看最近的日志：${NC}"
        tail -n 20 logs/supervisor.log
        exit 1
    fi
done

# ==================== 步骤8: 健康检查 ====================
echo ""
echo -e "${BLUE}🔍 步骤8: 健康检查...${NC}"

sleep 2

# 检查后端服务
if curl -s http://127.0.0.1:8002/health > /dev/null; then
    echo -e "${GREEN}✅ 后端服务健康${NC}"
else
    echo -e "${RED}❌ 后端服务异常${NC}"
fi

# 检查Nginx代理
if curl -s http://127.0.0.1:8082/health > /dev/null; then
    echo -e "${GREEN}✅ Nginx代理正常${NC}"
else
    echo -e "${RED}❌ Nginx代理异常${NC}"
fi

# ==================== 部署完成 ====================
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📋 服务信息：${NC}"
echo "  • 服务名称: 任务分配系统"
echo "  • 后端端口: 8002 (内部)"
echo "  • 访问端口: 8082 (外部)"
echo ""
echo -e "${BLUE}🌐 访问地址：${NC}"
echo "  • 管理员端: http://你的服务器IP:8082"
echo "  • 员工端:   http://你的服务器IP:8082/employee"
echo "  • 健康检查: http://你的服务器IP:8082/health"
echo ""
echo -e "${BLUE}📝 管理命令：${NC}"
echo "  • 查看状态: ./manage.sh status"
echo "  • 重启服务: ./manage.sh restart"
echo "  • 查看日志: ./manage.sh logs"
echo "  • 停止服务: ./manage.sh stop"
echo ""
echo -e "${YELLOW}💡 提示：如果使用公网IP，请确保防火墙已开放8082端口${NC}"
echo ""

# 显示防火墙配置提示
if command -v firewall-cmd &> /dev/null; then
    echo -e "${BLUE}🔥 配置防火墙（可选）：${NC}"
    echo "  sudo firewall-cmd --permanent --add-port=8082/tcp"
    echo "  sudo firewall-cmd --reload"
    echo ""
fi

echo "=========================================="

