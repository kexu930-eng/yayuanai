# 任务分配系统

一个简单高效的任务分配系统，支持管理员分配任务并通过钉钉通知员工。

## 🌟 功能特点

### 管理员端
- ✅ 任务库管理（增删改查）
- ✅ 员工管理（增删改查）
- ✅ 任务分配（可批量分配）
- ✅ 自动发送钉钉通知
- ✅ 实时查看分配状态和拒绝理由

### 员工端
- ✅ 使用钉钉ID登录
- ✅ 查看所有分配的任务
- ✅ 接受或拒绝任务
- ✅ 填写拒绝理由
- ✅ 按截止日期排序
- ✅ 任务状态筛选（全部/待处理/进行中）

## 🏗️ 技术架构

```
浏览器
  ↓
Nginx (8082端口) - 反向代理
  ↓
Gunicorn (127.0.0.1:8002) - WSGI服务器
  ↓
Flask应用 - 业务逻辑
  ↓
SQLite数据库 - 数据存储
  ↓
Supervisor - 进程管理
```

### 技术栈
- **后端**: Flask + SQLAlchemy
- **数据库**: SQLite
- **Web服务器**: Gunicorn + Nginx
- **进程管理**: Supervisor
- **通知**: 钉钉机器人API

## 📦 快速部署

### 一键部署

```bash
cd /root/workspace/xk/yayuan/simple_distribute
sudo bash deploy.sh
```

部署脚本会自动完成：
1. 安装系统依赖（Python3、Nginx、Supervisor）
2. 安装Python依赖
3. 初始化数据库
4. 配置Supervisor和Nginx
5. 启动服务

### 手动部署

如果需要手动部署，请按照以下步骤：

#### 1. 安装依赖

```bash
# 安装系统依赖
sudo yum install -y python3 python3-pip nginx supervisor

# 安装Python依赖
pip3 install -r requirements.txt
```

#### 2. 初始化数据库

```bash
python3 << EOF
from app import app, db
with app.app_context():
    db.create_all()
EOF
```

#### 3. 配置Supervisor

```bash
sudo cp supervisor_config.conf /etc/supervisor/conf.d/task_distribute.conf
sudo systemctl restart supervisord
sudo supervisorctl reread
sudo supervisorctl update
```

#### 4. 配置Nginx

```bash
sudo cp nginx_config.conf /etc/nginx/conf.d/task_distribute.conf
sudo nginx -t
sudo systemctl restart nginx
```

#### 5. 启动服务

```bash
sudo supervisorctl start task_distribute
```

## 🎮 服务管理

系统提供了便捷的管理脚本：

```bash
# 查看服务状态
./manage.sh status

# 重启服务
./manage.sh restart

# 停止服务
./manage.sh stop

# 启动服务
./manage.sh start

# 查看实时日志
./manage.sh logs

# 查看错误日志
./manage.sh logs-error

# 健康检查
./manage.sh health
```

## 🌐 访问地址

部署完成后，可以通过以下地址访问：

- **管理员端**: http://你的服务器IP:8082
- **员工端**: http://你的服务器IP:8082/employee
- **健康检查**: http://你的服务器IP:8082/health

## 🔥 防火墙配置

如果使用公网IP访问，需要开放8082端口：

```bash
sudo firewall-cmd --permanent --add-port=8082/tcp
sudo firewall-cmd --reload
```

## 📝 使用流程

### 管理员操作流程

1. **添加员工**
   - 进入"员工管理"标签
   - 输入员工姓名和钉钉用户ID
   - 点击"添加员工"

2. **创建任务**
   - 进入"任务库管理"标签
   - 输入任务名称、描述和预计完成时间
   - 点击"添加到任务库"

3. **分配任务**
   - 进入"任务分配"标签
   - 选择任务和对应的员工
   - 可点击"添加更多"批量分配
   - 点击"确认发送钉钉通知"

4. **查看记录**
   - 进入"分配记录"标签
   - 查看所有任务的状态
   - 查看员工的拒绝理由

### 员工操作流程

1. **登录系统**
   - 访问员工端页面
   - 输入钉钉用户ID登录
   - 或通过钉钉通知中的链接直接访问

2. **查看任务**
   - 查看所有分配给自己的任务
   - 按截止日期排序（最近的优先）
   - 使用标签筛选（全部/待处理/进行中）

3. **响应任务**
   - 接受任务：点击"✅ 接受任务"
   - 拒绝任务：点击"❌ 拒绝"，填写理由后提交
   - 查看任务状态和紧急程度提醒

## 🗂️ 项目结构

```
simple_distribute/
├── app.py                      # Flask主应用
├── models.py                   # 数据库模型
├── admin.html                  # 管理员端页面
├── employee.html               # 员工端页面
├── requirements.txt            # Python依赖
├── gunicorn_config.py          # Gunicorn配置
├── supervisor_config.conf      # Supervisor配置
├── nginx_config.conf           # Nginx配置
├── deploy.sh                   # 一键部署脚本
├── manage.sh                   # 服务管理脚本
├── README.md                   # 本文档
├── logs/                       # 日志目录
│   ├── access.log             # 访问日志
│   ├── error.log              # 错误日志
│   └── supervisor.log         # Supervisor日志
└── task_distribution.db        # SQLite数据库
```

## 📊 API接口

### 任务管理
- `GET /api/tasks` - 获取所有任务
- `POST /api/tasks` - 创建新任务
- `DELETE /api/tasks/<id>` - 删除任务

### 员工管理
- `GET /api/employees` - 获取所有员工
- `POST /api/employees` - 创建新员工
- `DELETE /api/employees/<id>` - 删除员工

### 任务分配
- `GET /api/assignments` - 获取所有分配记录
- `POST /api/assignments/send` - 发送任务分配
- `GET /api/assignments/<id>` - 获取分配详情
- `POST /api/assignments/<id>/accept` - 接受任务
- `POST /api/assignments/<id>/reject` - 拒绝任务
- `GET /api/assignments/employee/<dingtalk_id>` - 获取员工的任务

### 系统
- `GET /health` - 健康检查

## 🔧 配置说明

### 端口配置
- **后端端口**: 8002 (仅内部访问)
- **Nginx端口**: 8082 (外部访问)

如需修改端口，需要同时修改：
1. `gunicorn_config.py` - bind参数
2. `nginx_config.conf` - listen和proxy_pass参数

### 钉钉机器人配置

钉钉机器人配置在 `../dingding/robot.py` 文件中：
- `x-acs-dingtalk-access-token`: 钉钉访问令牌
- `robotCode`: 机器人编码
- `userIds`: 默认接收用户ID列表

## 🐛 故障排查

### 服务无法启动

```bash
# 查看日志
./manage.sh logs-error

# 检查Supervisor状态
sudo supervisorctl status

# 手动启动测试
python3 app.py
```

### 无法访问页面

```bash
# 检查Nginx状态
sudo systemctl status nginx

# 检查Nginx配置
sudo nginx -t

# 检查端口监听
netstat -tlnp | grep -E ':(8002|8082)'
```

### 数据库问题

```bash
# 检查数据库文件
ls -lh task_distribution.db

# 重新初始化数据库
rm task_distribution.db
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## 📈 性能优化

- **Gunicorn workers**: 默认为 CPU核心数 * 2 + 1
- **数据库**: 使用SQLite，适合中小规模应用
- **缓存**: 前端使用轮询，每5秒刷新一次状态

如需支持更大规模，建议：
1. 更换为PostgreSQL或MySQL数据库
2. 添加Redis缓存
3. 使用WebSocket替代轮询
4. 部署多个应用实例+负载均衡

## 🔒 安全建议

1. **使用HTTPS**: 配置SSL证书
2. **添加认证**: 为管理员端添加登录系统
3. **API限流**: 防止恶意请求
4. **输入验证**: 严格验证用户输入
5. **定期备份**: 备份数据库文件

## 📞 技术支持

如有问题，请查看：
1. 日志文件：`logs/` 目录
2. 健康检查：`./manage.sh health`
3. 服务状态：`./manage.sh status`

## 📄 许可证

MIT License

---

**版本**: 1.0.0  
**更新日期**: 2024-11-28

