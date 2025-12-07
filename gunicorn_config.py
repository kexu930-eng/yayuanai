#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gunicorn配置文件
"""
import multiprocessing

# 服务器绑定地址和端口
bind = "127.0.0.1:8002"

# 工作进程数（CPU核心数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 每个工作进程的线程数
threads = 2

# 超时时间（秒）
timeout = 120

# 保持活动连接的时间（秒）
keepalive = 5

# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 日志
accesslog = "/root/workspace/xk/yayuan/simple_distribute/logs/access.log"
errorlog = "/root/workspace/xk/yayuan/simple_distribute/logs/error.log"
loglevel = "info"

# 进程命名
proc_name = "task_distribute"

# 守护进程模式（由supervisor管理，设为False）
daemon = False

# 预加载应用
preload_app = True

# 工作进程重启前处理的最大请求数
max_requests = 1000

