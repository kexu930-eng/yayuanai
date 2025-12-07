# 任务分配系统 - 项目上下文文档

## 📋 项目概述

这是一个基于钉钉的任务分配系统，包含两个钉钉微应用：
- **人工任务分配**（管理员端）：供经理/管理员使用，用于管理员工、技能池、任务库和任务分配
- **我的任务管理**（员工端）：供员工使用，查看和响应分配给自己的任务

## 🎯 核心功能

### 微应用1：人工任务分配（管理员端）

| 模块 | 功能描述 |
|------|----------|
| **技能池构建** | 管理员添加部门所需的技能，形成技能池 |
| **任务库管理** | 创建任务并关联所需技能（多选） |
| **员工管理** | 添加员工，设置员工技能及评分（1-10分） |
| **任务分配** | 选择任务和员工进行分配，显示技能匹配信息，发送钉钉通知 |
| **分配记录** | 查看所有分配的状态（待处理/已接受/已拒绝） |

**数据隔离**：每个管理员只能看到自己部门的员工、技能和分配记录

### 微应用2：我的任务管理（员工端）

| 功能 | 描述 |
|------|------|
| **钉钉免密登录** | 自动识别员工身份 |
| **任务列表** | 按截止日期排序显示分配的任务 |
| **任务筛选** | 全部/待处理/进行中 |
| **接受任务** | 点击接受，状态变为进行中 |
| **拒绝任务** | 填写拒绝理由后提交 |
| **分配人显示** | 显示是哪个经理分配的任务 |
| **我的负载** | 查看工作负载可视化 |
| **自主任务管理** | 添加非经理分配的其他任务 |
| **不可用时间管理** | 记录出差、会议、培训等不可用时间 |

---

## 🏗️ 技术架构

```
钉钉客户端
    ↓
Nginx (8082端口) - 反向代理
    ↓
Gunicorn (127.0.0.1:8002) - WSGI服务器
    ↓
Flask应用 (app.py) - 业务逻辑
    ↓
SQLite数据库 (task_distribution.db)
    ↓
Supervisor - 进程管理
```

### 技术栈
- **后端**: Python 3 + Flask + SQLAlchemy
- **数据库**: SQLite
- **Web服务器**: Gunicorn + Nginx
- **进程管理**: Supervisor
- **前端**: HTML5 + CSS3 + JavaScript（原生）
- **钉钉集成**: 钉钉 JSAPI + 钉钉开放平台 API

---

## 📁 项目文件结构

```
simple_distribute/
├── app.py                      # 【核心】Flask主应用，所有后端逻辑
├── models.py                   # 【核心】数据库模型定义
├── admin.html                  # 管理员端前端页面
├── employee.html               # 员工端前端页面
├── accept.html                 # 任务接受页面（钉钉卡片跳转）
├── reject.html                 # 任务拒绝页面（钉钉卡片跳转）
├── task_distribution.db        # SQLite数据库文件
├── requirements.txt            # Python依赖
├── gunicorn_config.py          # Gunicorn配置
├── supervisor_config.conf      # Supervisor配置
├── nginx_config.conf           # Nginx配置
├── deploy.sh                   # 一键部署脚本
├── manage.sh                   # 服务管理脚本
├── robot_message/              # 钉钉机器人消息模块
│   └── robot.py               # 发送钉钉通知
├── logs/                       # 日志目录
└── migrate_*.py                # 数据库迁移脚本
```

---

## 🗃️ 数据库设计

### 数据模型 (models.py)

#### 1. Task（任务表）
```python
- id: 主键
- name: 任务名称
- description: 任务描述
- deadline: 截止日期
- created_at: 创建时间
- 关系: task_skills (任务所需技能)
```

#### 2. Skill（技能表）
```python
- id: 主键
- name: 技能名称
- manager_dingtalk_id: 所属管理员钉钉ID（数据隔离）
- created_at: 创建时间
```

#### 3. Employee（员工表）
```python
- id: 主键
- name: 员工姓名
- dingtalk_id: 钉钉用户ID
- manager_dingtalk_id: 所属管理员钉钉ID（数据隔离）
- created_at: 创建时间
- 关系: employee_skills (员工技能)
```

#### 4. TaskSkill（任务-技能关联表）
```python
- id: 主键
- task_id: 任务ID
- skill_id: 技能ID
```

#### 5. EmployeeSkill（员工-技能关联表）
```python
- id: 主键
- employee_id: 员工ID
- skill_id: 技能ID
- rating: 评分（1-10）
```

#### 6. Assignment（任务分配表）
```python
- id: 主键
- task_id: 任务ID
- employee_id: 员工ID
- assigned_by_dingtalk_id: 分配人钉钉ID
- assigned_by_name: 分配人姓名
- status: 状态（pending/accepted/rejected）
- reject_reason: 拒绝理由
- assigned_at: 分配时间
- responded_at: 响应时间
- notification_sent: 通知是否发送成功
```

#### 7. SelfTask（员工自主任务表）
```python
- id: 主键
- employee_id: 员工ID
- name: 任务名称
- estimated_hours: 预计耗时（小时）
- deadline: 截止日期
- task_type: 任务类型（project/temporary/learning）
- description: 任务描述
- status: 状态（pending/completed）
- created_at: 创建时间
- completed_at: 完成时间
```

#### 8. UnavailableTime（员工不可用时间表）
```python
- id: 主键
- employee_id: 员工ID
- date: 日期（YYYY-MM-DD）
- start_time: 开始时间（HH:MM）
- end_time: 结束时间（HH:MM）
- reason_type: 原因类型（meeting/travel/training/leave/other）
- note: 备注说明
- created_at: 创建时间
```

---

## 🔌 API接口 (app.py)

### 钉钉认证
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/dingtalk/config` | GET | 获取钉钉配置（corpId, appKey等） |
| `/api/dingtalk/auth` | POST | 处理免密登录，验证授权码获取用户信息 |

### 技能管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/skills` | GET | 获取技能列表（支持manager_dingtalk_id筛选） |
| `/api/skills` | POST | 创建技能 |
| `/api/skills/<id>` | DELETE | 删除技能 |

### 任务管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tasks` | GET | 获取任务列表（含关联技能） |
| `/api/tasks` | POST | 创建任务（含skill_ids） |
| `/api/tasks/<id>` | DELETE | 删除任务 |

### 员工管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/employees` | GET | 获取员工列表（支持筛选，含技能） |
| `/api/employees` | POST | 创建员工（含skills数组） |
| `/api/employees/<id>` | DELETE | 删除员工 |

### 任务分配
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/assignments` | GET | 获取分配记录（支持筛选） |
| `/api/assignments/send` | POST | 发送任务分配并通知钉钉 |
| `/api/assignments/<id>/accept` | POST | 接受任务 |
| `/api/assignments/<id>/reject` | POST | 拒绝任务 |

### 自主任务管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/self-tasks` | GET | 获取员工自主任务列表（需employee_id参数） |
| `/api/self-tasks` | POST | 创建自主任务 |
| `/api/self-tasks/<id>` | DELETE | 删除自主任务 |
| `/api/self-tasks/<id>/complete` | POST | 完成自主任务 |

### 不可用时间管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/unavailable-times` | GET | 获取不可用时间列表（需employee_id参数） |
| `/api/unavailable-times` | POST | 创建不可用时间 |
| `/api/unavailable-times/<id>` | DELETE | 删除不可用时间 |

### 负载计算
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/workload/<employee_id>` | GET | 获取员工负载数据（含统计和可视化数据） |

---

## 🔐 钉钉免密登录实现

### 流程
```
1. 前端检测钉钉环境 (dd.env.platform)
2. 前端调用 dd.runtime.permission.requestAuthCode 获取授权码
3. 前端发送授权码到后端 /api/dingtalk/auth
4. 后端获取应用AccessToken (https://api.dingtalk.com/v1.0/oauth2/accessToken)
5. 后端用授权码获取用户信息 (https://oapi.dingtalk.com/topapi/v2/user/getuserinfo)
6. 后端查询数据库验证员工身份
7. 返回用户信息给前端
```

### 钉钉配置 (app.py)
```python
# 人工任务分配（管理员端）
DINGTALK_TASK_APP_KEY = "dingicmyjrh5qw265io1"
DINGTALK_TASK_APP_SECRET = "or3uduH_uUy2ZrIU8X7nzSByPijtMwbHyE-hUUojpZmOi4XWOZjtRUULbM5QgFMj"
APP_ID = "1981b38d-0762-4589-80d0-e600d92cb487"

# 我的任务管理（员工端）
DINGTALK_EMPLOYEE_APP_KEY = "dingfptkullvlunojgq8"
DINGTALK_EMPLOYEE_APP_SECRET = "ak5XhBPMMnYr0XOm0_NYssGlQ-eEyL5Dv2Yk18LNBkGEoUCiSzwfx5JPKrJbQ3r0"
APP_ID = "7a5d1d01-023a-439a-a220-c907f6fcfd36"

# 企业ID
CORP_ID = "ding795a49edf28b4433"
```

---

## 🎨 前端实现要点

### admin.html（管理员端）

#### 页面结构
1. **登录页面**：钉钉免密登录
2. **技能池构建**：技能砖块展示，点击添加/删除
3. **任务库管理**：创建任务，点击技能砖块选择所需技能
4. **员工管理**：添加员工，动态添加技能行（下拉框+滑块评分）
5. **任务分配**：选择任务/员工时显示技能信息
6. **分配记录**：展示状态卡片

#### 关键JavaScript函数
- `loadDingTalkConfig()` - 加载钉钉配置
- `handleDingTalkLogin()` - 处理免密登录
- `loadDataFromServer()` - 加载数据（带管理员筛选）
- `renderSkills()` - 渲染技能池（砖块形式）
- `toggleSkillSelection()` - 技能砖块选择切换
- `addEmployeeSkillRow()` - 添加员工技能行
- `onTaskSelectChange()` - 任务选择时显示技能
- `onEmployeeSelectChange()` - 员工选择时显示技能

### employee.html（员工端）

#### 页面结构
1. **登录页面**：免密登录 + 手动输入ID备选
2. **任务列表**：卡片形式，显示任务详情、截止日期、分配人
3. **任务筛选**：Tab切换（全部/待处理/进行中）

#### 关键JavaScript函数
- `loadDingTalkConfig()` - 加载钉钉配置
- `handleDingTalkLogin()` - 处理免密登录
- `getDingTalkAuthCode()` - 获取授权码
- `loadTasks()` - 加载员工任务
- `renderTasks()` - 渲染任务列表
- `acceptTask()` - 接受任务
- `rejectTask()` - 拒绝任务

---

## 🚀 运行方式

### 开发模式
```bash
cd /root/workspace/xk/yayuan/simple_distribute
python3 app.py
# 访问 http://服务器IP:8002
```

### 生产模式
```bash
# 一键部署
sudo bash deploy.sh

# 服务管理
./manage.sh status   # 查看状态
./manage.sh restart  # 重启服务
./manage.sh logs     # 查看日志
./manage.sh health   # 健康检查

# 访问地址
# 管理员端: http://服务器IP:8082
# 员工端: http://服务器IP:8082/employee
```

### 数据库迁移
```bash
# 如需添加新字段，运行对应的迁移脚本
python3 migrate_add_manager_fields.py
python3 migrate_add_skills.py
python3 migrate_add_employee_skills.py
```

---

## 🔑 关键实现细节

### 1. 数据隔离机制
- 员工表有 `manager_dingtalk_id` 字段
- 技能表有 `manager_dingtalk_id` 字段
- 分配记录有 `assigned_by_dingtalk_id` 字段
- API查询时带 `?manager_dingtalk_id=xxx` 参数筛选

### 2. 技能砖块选择
- CSS样式：`.skill-brick`、`.skill-brick.selected`
- 点击切换选择状态
- 选中后右上角显示红色×按钮
- 使用隐藏的input存储选中的技能ID

### 3. 员工技能评分
- 使用range滑块（1-10）
- 动态添加/删除技能行
- 提交时收集所有技能行数据

### 4. 任务分配技能对比
- 选择任务后显示任务所需技能（橙色标签）
- 选择员工后显示员工技能及评分（绿色标签）
- 便于管理员匹配合适的员工

### 5. AccessToken缓存
- 分别缓存两个应用的token
- 自动检查过期时间
- 提前5分钟刷新

---

## ⚠️ 注意事项

1. **必须在钉钉中打开**：免密登录只能在钉钉客户端中使用
2. **配置微应用首页**：在钉钉开放平台配置正确的首页URL
3. **防火墙开放端口**：8082端口需要开放
4. **员工需先添加**：员工端登录需要管理员先在系统中添加员工
5. **技能池先建立**：添加员工和任务前，先建立技能池

---

## 📞 调试方法

### 后端日志
```bash
tail -f logs/error.log
```

### 前端调试
- 浏览器开发者工具 Console 查看日志
- Network 标签查看API请求

### 检查服务状态
```bash
./manage.sh status
./manage.sh health
netstat -tlnp | grep -E ':(8002|8082)'
```

---

## 🔮 可扩展方向

1. **任务自动匹配**：根据技能自动推荐合适的员工
2. **技能差距分析**：分析员工技能与任务需求的差距
3. **批量导入**：支持Excel批量导入员工和技能
4. **统计报表**：任务完成率、员工工作量统计
5. **消息提醒**：任务即将到期提醒
6. **权限管理**：更细粒度的管理员权限控制

---

**项目路径**: `/root/workspace/xk/yayuan/simple_distribute`  
**主要文件**: `app.py`（后端）、`admin.html`（管理员前端）、`employee.html`（员工前端）  
**数据库**: `task_distribution.db`（SQLite）  
**服务端口**: 8082（Nginx）→ 8002（Gunicorn）

