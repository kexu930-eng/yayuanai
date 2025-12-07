#!/bin/bash

# 任务分配系统管理脚本

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="task_distribute"

# 显示帮助信息
show_help() {
    echo "任务分配系统管理脚本"
    echo ""
    echo "用法: ./manage.sh [命令]"
    echo ""
    echo "命令:"
    echo "  status    - 查看服务状态"
    echo "  start     - 启动服务"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  logs      - 查看日志（实时）"
    echo "  logs-error - 查看错误日志"
    echo "  health    - 健康检查"
    echo "  help      - 显示此帮助信息"
    echo ""
}

# 检查服务状态
check_status() {
    echo -e "${BLUE}📊 服务状态：${NC}"
    sudo supervisorctl status $SERVICE_NAME
    echo ""
    
    echo -e "${BLUE}🌐 端口监听：${NC}"
    netstat -tlnp | grep -E ':(8002|8082)' || echo "未找到监听端口"
    echo ""
}

# 启动服务
start_service() {
    echo -e "${BLUE}🚀 启动服务...${NC}"
    sudo supervisorctl start $SERVICE_NAME
    sleep 2
    check_status
}

# 停止服务
stop_service() {
    echo -e "${YELLOW}🛑 停止服务...${NC}"
    sudo supervisorctl stop $SERVICE_NAME
    sleep 1
    check_status
}

# 重启服务
restart_service() {
    echo -e "${BLUE}🔄 重启服务...${NC}"
    sudo supervisorctl restart $SERVICE_NAME
    sleep 2
    check_status
}

# 查看日志
view_logs() {
    echo -e "${BLUE}📋 实时日志 (按 Ctrl+C 退出)：${NC}"
    echo ""
    tail -f logs/supervisor.log
}

# 查看错误日志
view_error_logs() {
    echo -e "${RED}❌ 错误日志：${NC}"
    echo ""
    if [ -f "logs/error.log" ]; then
        tail -n 50 logs/error.log
    else
        echo "错误日志文件不存在"
    fi
}

# 健康检查
health_check() {
    echo -e "${BLUE}🔍 健康检查：${NC}"
    echo ""
    
    # 检查后端服务
    echo -n "后端服务 (8002): "
    if curl -s http://127.0.0.1:8002/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 正常${NC}"
        curl -s http://127.0.0.1:8002/health | python3 -m json.tool
    else
        echo -e "${RED}❌ 异常${NC}"
    fi
    echo ""
    
    # 检查Nginx代理
    echo -n "Nginx代理 (8082): "
    if curl -s http://127.0.0.1:8082/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 正常${NC}"
    else
        echo -e "${RED}❌ 异常${NC}"
    fi
    echo ""
    
    # 检查数据库
    echo -n "数据库: "
    if [ -f "task_distribution.db" ]; then
        echo -e "${GREEN}✅ 存在${NC}"
        ls -lh task_distribution.db
    else
        echo -e "${RED}❌ 不存在${NC}"
    fi
    echo ""
}

# 主逻辑
case "$1" in
    status)
        check_status
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        view_logs
        ;;
    logs-error)
        view_error_logs
        ;;
    health)
        health_check
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

