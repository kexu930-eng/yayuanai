#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务分配系统 - Flask后端应用
"""
import os
import sys
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import requests as req

# 添加钉钉机器人路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'robot_message'))
from robot import send_task_notification

# 钉钉配置 - 人工任务分配（管理员端，用于发送通知）
DINGTALK_TASK_APP_KEY = "dingicmyjrh5qw265io1"
DINGTALK_TASK_APP_SECRET = "or3uduH_uUy2ZrIU8X7nzSByPijtMwbHyE-hUUojpZmOi4XWOZjtRUULbM5QgFMj"
DINGTALK_ROBOT_CODE = "dingb3x9dvpkgz0iwpyu"  # 机器人编码

# 钉钉配置 - 我的任务管理（员工端，用于免密登录）
DINGTALK_EMPLOYEE_APP_KEY = "dingfptkullvlunojgq8"
DINGTALK_EMPLOYEE_APP_SECRET = "ak5XhBPMMnYr0XOm0_NYssGlQ-eEyL5Dv2Yk18LNBkGEoUCiSzwfx5JPKrJbQ3r0"

# AccessToken 缓存（分别缓存两个应用的token）
_access_token_cache = {
    'task_app': {  # 人工任务分配应用
        'token': None,
        'expires_at': None
    },
    'employee_app': {  # 我的任务管理应用
        'token': None,
        'expires_at': None
    }
}


def get_dingtalk_access_token(app_type='task_app'):
    """
    获取钉钉 AccessToken（自动缓存和刷新）
    
    参数:
        app_type: 'task_app' (人工任务分配) 或 'employee_app' (我的任务管理)
    """
    global _access_token_cache
    
    # 根据应用类型选择配置
    if app_type == 'task_app':
        app_key = DINGTALK_TASK_APP_KEY
        app_secret = DINGTALK_TASK_APP_SECRET
        app_name = "人工任务分配"
    else:
        app_key = DINGTALK_EMPLOYEE_APP_KEY
        app_secret = DINGTALK_EMPLOYEE_APP_SECRET
        app_name = "我的任务管理"
    
    print("=" * 60)
    print(f"🔑 开始获取钉钉 AccessToken - 应用: {app_name}")
    
    # 如果token还在有效期内，直接返回
    cache = _access_token_cache[app_type]
    if cache['token'] and cache['expires_at']:
        if datetime.now() < cache['expires_at']:
            print(f"✅ 使用缓存的 AccessToken")
            print(f"   Token: {cache['token'][:20]}...")
            print(f"   过期时间: {cache['expires_at']}")
            print("=" * 60)
            return cache['token']
    
    # 重新获取token
    print("🔄 缓存失效，正在获取新的 AccessToken...")
    print(f"   应用: {app_name}")
    print(f"   AppKey: {app_key}")
    print(f"   AppSecret: {app_secret[:10]}...")
    
    url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "appKey": app_key,
        "appSecret": app_secret
    }
    
    try:
        print(f"   请求URL: {url}")
        response = req.post(url, headers=headers, json=payload, timeout=10)
        print(f"   响应状态码: {response.status_code}")
        result = response.json()
        print(f"   响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if 'accessToken' in result:
            token = result['accessToken']
            expires_in = result.get('expireIn', 7200)  # 默认2小时
            
            # 缓存token（提前5分钟过期）
            cache['token'] = token
            cache['expires_at'] = datetime.now() + timedelta(seconds=expires_in - 300)
            
            print(f"✅ AccessToken 获取成功！")
            print(f"   完整Token: {token}")
            print(f"   有效期: {expires_in}秒")
            print(f"   过期时间: {cache['expires_at']}")
            print("=" * 60)
            return token
        else:
            print(f"❌ 获取 AccessToken 失败！")
            print(f"   错误信息: {result}")
            print("=" * 60)
            return None
    except Exception as e:
        print(f"❌ 获取 AccessToken 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return None

# 导入数据库模型
from models import db, Task, Employee, Assignment, Skill, TaskSkill, EmployeeSkill, SelfTask, UnavailableTime, WorkSession, WorkInterruption

app = Flask(__name__, static_folder='.')
CORS(app)

# 配置数据库
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "task_distribution.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False  # 支持中文

# 初始化数据库
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()


# ==================== 静态文件路由 ====================

@app.route('/')
def index():
    """管理员端首页"""
    return send_from_directory('.', 'admin.html')


@app.route('/employee')
def employee_page():
    """员工端页面"""
    return send_from_directory('.', 'employee.html')


@app.route('/accept')
def accept_page():
    """接受任务页面"""
    return send_from_directory('.', 'accept.html')


@app.route('/reject')
def reject_page():
    """拒绝任务页面"""
    return send_from_directory('.', 'reject.html')


# ==================== 技能管理API ====================

@app.route('/api/skills', methods=['GET'])
def get_skills():
    """
    获取技能列表
    可选参数: manager_dingtalk_id - 筛选某个管理员的技能
    """
    manager_dingtalk_id = request.args.get('manager_dingtalk_id')
    
    query = Skill.query
    if manager_dingtalk_id:
        query = query.filter_by(manager_dingtalk_id=manager_dingtalk_id)
    
    # 使用索引排序
    skills = query.order_by(Skill.id.desc()).all()
    
    return jsonify([skill.to_dict() for skill in skills])


@app.route('/api/skills', methods=['POST'])
def create_skill():
    """创建新技能"""
    data = request.json
    skill = Skill(
        name=data.get('name'),
        manager_dingtalk_id=data.get('manager_dingtalk_id')  # 记录所属管理员
    )
    db.session.add(skill)
    db.session.commit()
    return jsonify(skill.to_dict()), 201


@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    """删除技能（同时清理关联数据）"""
    try:
        skill = Skill.query.get_or_404(skill_id)
        
        # 1. 先删除员工技能关联（EmployeeSkill引用了此技能）
        EmployeeSkill.query.filter_by(skill_id=skill_id).delete()
        
        # 2. 删除任务技能关联（TaskSkill引用了此技能，虽然有cascade但显式删除更安全）
        TaskSkill.query.filter_by(skill_id=skill_id).delete()
        
        # 3. 删除技能本身
        db.session.delete(skill)
        db.session.commit()
        
        print(f"✅ 技能删除成功: {skill.name} (ID: {skill_id})")
        return '', 204
    except Exception as e:
        db.session.rollback()
        print(f"❌ 技能删除失败: {str(e)}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


# ==================== 任务管理API ====================

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务（优化：使用eager loading减少N+1查询）"""
    from sqlalchemy.orm import joinedload
    
    # 使用joinedload预加载任务技能
    tasks = Task.query.options(
        joinedload(Task.task_skills).joinedload(TaskSkill.skill)
    ).order_by(Task.id.desc()).all()
    
    return jsonify([task.to_dict() for task in tasks])


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.json
    task = Task(
        name=data.get('name'),
        description=data.get('description'),
        deadline=data.get('deadline'),
        estimated_hours=data.get('estimated_hours'),  # 预计耗时（小时）
        importance=data.get('importance', 5),  # 重要程度（1-10）
        importance_note=data.get('importance_note')  # 重要度说明
    )
    db.session.add(task)
    db.session.flush()  # 获取task的ID
    
    # 处理技能关联
    skill_ids = data.get('skill_ids', [])
    if skill_ids:
        for skill_id in skill_ids:
            task_skill = TaskSkill(
                task_id=task.id,
                skill_id=skill_id
            )
            db.session.add(task_skill)
    
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务详情"""
    from sqlalchemy.orm import joinedload
    
    task = Task.query.options(
        joinedload(Task.task_skills).joinedload(TaskSkill.skill)
    ).get_or_404(task_id)
    
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    task = Task.query.get_or_404(task_id)
    data = request.json
    
    # 更新基本字段
    if 'name' in data:
        task.name = data['name']
    if 'description' in data:
        task.description = data['description']
    if 'deadline' in data:
        task.deadline = data['deadline']
    if 'estimated_hours' in data:
        task.estimated_hours = data['estimated_hours']
    if 'importance' in data:
        task.importance = data['importance']
    if 'importance_note' in data:
        task.importance_note = data['importance_note']
    
    # 更新技能关联
    if 'skill_ids' in data:
        # 删除旧的技能关联
        TaskSkill.query.filter_by(task_id=task_id).delete()
        
        # 添加新的技能关联
        skill_ids = data.get('skill_ids', [])
        for skill_id in skill_ids:
            task_skill = TaskSkill(
                task_id=task.id,
                skill_id=skill_id
            )
            db.session.add(task_skill)
    
    db.session.commit()
    
    # 重新查询以获取更新后的关联数据
    from sqlalchemy.orm import joinedload
    task = Task.query.options(
        joinedload(Task.task_skills).joinedload(TaskSkill.skill)
    ).get(task_id)
    
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204


# ==================== 员工管理API ====================

@app.route('/api/employees', methods=['GET'])
def get_employees():
    """
    获取员工列表（优化：使用eager loading减少N+1查询）
    可选参数: manager_dingtalk_id - 筛选某个管理员的员工
    """
    from sqlalchemy.orm import joinedload
    
    manager_dingtalk_id = request.args.get('manager_dingtalk_id')
    
    # 使用joinedload预加载员工技能，避免N+1查询
    query = Employee.query.options(
        joinedload(Employee.employee_skills).joinedload(EmployeeSkill.skill)
    )
    
    if manager_dingtalk_id:
        query = query.filter_by(manager_dingtalk_id=manager_dingtalk_id)
    
    employees = query.order_by(Employee.id.desc()).all()
    
    return jsonify([emp.to_dict() for emp in employees])


@app.route('/api/employees', methods=['POST'])
def create_employee():
    """创建新员工"""
    data = request.json
    employee = Employee(
        name=data.get('name'),
        dingtalk_id=data.get('dingtalk_id'),
        manager_dingtalk_id=data.get('manager_dingtalk_id')  # 记录所属管理员
    )
    db.session.add(employee)
    db.session.flush()  # 获取employee的ID
    
    # 处理员工技能
    skills_data = data.get('skills', [])
    if skills_data:
        for skill_item in skills_data:
            skill_id = skill_item.get('skill_id')
            rating = skill_item.get('rating', 5)
            if skill_id:
                employee_skill = EmployeeSkill(
                    employee_id=employee.id,
                    skill_id=skill_id,
                    rating=rating
                )
                db.session.add(employee_skill)
    
    db.session.commit()
    return jsonify(employee.to_dict()), 201


@app.route('/api/employees/<int:employee_id>', methods=['GET'])
def get_employee(employee_id):
    """获取单个员工详情"""
    from sqlalchemy.orm import joinedload
    
    employee = Employee.query.options(
        joinedload(Employee.employee_skills).joinedload(EmployeeSkill.skill)
    ).get_or_404(employee_id)
    
    return jsonify(employee.to_dict())


@app.route('/api/employees/<int:employee_id>', methods=['PUT'])
def update_employee(employee_id):
    """更新员工"""
    employee = Employee.query.get_or_404(employee_id)
    data = request.json
    
    # 更新基本字段
    if 'name' in data:
        employee.name = data['name']
    if 'dingtalk_id' in data:
        employee.dingtalk_id = data['dingtalk_id']
    
    # 更新技能
    if 'skills' in data:
        # 删除旧的技能
        EmployeeSkill.query.filter_by(employee_id=employee_id).delete()
        
        # 添加新的技能
        skills_data = data.get('skills', [])
        for skill_item in skills_data:
            skill_id = skill_item.get('skill_id')
            rating = skill_item.get('rating', 5)
            if skill_id:
                employee_skill = EmployeeSkill(
                    employee_id=employee.id,
                    skill_id=skill_id,
                    rating=rating
                )
                db.session.add(employee_skill)
    
    db.session.commit()
    
    # 重新查询以获取更新后的关联数据
    from sqlalchemy.orm import joinedload
    employee = Employee.query.options(
        joinedload(Employee.employee_skills).joinedload(EmployeeSkill.skill)
    ).get(employee_id)
    
    return jsonify(employee.to_dict())


@app.route('/api/employees/<int:employee_id>', methods=['DELETE'])
def delete_employee(employee_id):
    """删除员工"""
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    return '', 204


# ==================== 任务分配API ====================

@app.route('/api/assignments', methods=['GET'])
def get_assignments():
    """
    获取任务分配记录（优化：使用eager loading减少N+1查询）
    可选参数: manager_dingtalk_id - 筛选某个管理员的分配记录
    """
    from sqlalchemy.orm import joinedload
    
    manager_dingtalk_id = request.args.get('manager_dingtalk_id')
    
    # 使用joinedload预加载任务和员工信息
    query = Assignment.query.options(
        joinedload(Assignment.task),
        joinedload(Assignment.employee)
    )
    
    if manager_dingtalk_id:
        query = query.filter_by(assigned_by_dingtalk_id=manager_dingtalk_id)
    
    assignments = query.order_by(Assignment.id.desc()).all()
    
    return jsonify([assign.to_dict() for assign in assignments])


@app.route('/api/assignments/employee/<dingtalk_id>', methods=['GET'])
def get_employee_assignments(dingtalk_id):
    """根据钉钉ID获取员工的任务分配"""
    # 查找员工
    employee = Employee.query.filter_by(dingtalk_id=dingtalk_id).first()
    if not employee:
        return jsonify([])
    
    # 查找该员工的所有分配
    assignments = Assignment.query.filter_by(employee_id=employee.id).order_by(Assignment.assigned_at.desc()).all()
    return jsonify([assign.to_dict() for assign in assignments])


@app.route('/api/assignments/send', methods=['POST'])
def send_assignments():
    """发送任务分配并通知钉钉"""
    data = request.json
    assignments_data = data.get('assignments', [])
    assigned_by_dingtalk_id = data.get('assignedByDingtalkId')  # 分配人钉钉ID
    assigned_by_name = data.get('assignedByName')  # 分配人姓名
    
    if not assignments_data:
        return jsonify({'error': '没有任务分配'}), 400
    
    created_assignments = []
    
    for assign_data in assignments_data:
        # 查找任务和员工
        task = Task.query.get(assign_data.get('taskId'))
        employee = Employee.query.get(assign_data.get('employeeId'))
        
        if not task or not employee:
            continue
        
        # 创建分配记录，包含分配人信息
        assignment = Assignment(
            task_id=task.id,
            employee_id=employee.id,
            assigned_by_dingtalk_id=assigned_by_dingtalk_id,
            assigned_by_name=assigned_by_name,
            status='pending'
        )
        db.session.add(assignment)
        db.session.flush()  # 获取assignment的ID
        
        # 构建URL（强制使用公网IP地址）
        # 使用公网IP而不是request.host_url，避免生成localhost或127.0.0.1
        base_url = "http://101.37.168.176:8082"
        detail_url = f"{base_url}/employee?id={assignment.id}"
        accept_url = f"{base_url}/accept?id={assignment.id}"
        reject_url = f"{base_url}/reject?id={assignment.id}"
        
        print(f"🔗 生成的URL:")
        print(f"   详情: {detail_url}")
        print(f"   接受: {accept_url}")
        print(f"   拒绝: {reject_url}")
        
        # 发送钉钉通知
        try:
            print("\n" + "=" * 60)
            print(f"📤 准备发送钉钉通知给: {employee.name} (ID: {employee.dingtalk_id})")
            print(f"   任务: {task.name}")
            
            # 获取最新的AccessToken（使用人工任务分配应用）
            access_token = get_dingtalk_access_token(app_type='task_app')
            if not access_token:
                print(f"❌ 无法获取AccessToken，跳过钉钉通知")
                print("=" * 60 + "\n")
                continue
            
            print(f"✅ 已获取AccessToken，开始发送通知...")
            print(f"   使用Token: {access_token[:20]}...")
            
            planned_time = task.deadline if task.deadline else "待定"
            
            print(f"📋 通知参数:")
            print(f"   - 任务名称: {task.name}")
            print(f"   - 任务描述: {task.description[:30]}...")
            print(f"   - 计划时间: {planned_time}")
            print(f"   - 员工钉钉ID: {employee.dingtalk_id}")
            print(f"   - 详情URL: {detail_url}")
            print(f"   - 接受URL: {accept_url}")
            print(f"   - 拒绝URL: {reject_url}")
            
            result = send_task_notification(
                task_name=task.name,
                subtask_name=task.description[:50] + "..." if len(task.description) > 50 else task.description,
                planned_time=planned_time,
                detail_url=detail_url,
                accept_url=accept_url,
                reject_url=reject_url,
                employee_dingtalk_id=employee.dingtalk_id,  # 传入员工的钉钉ID
                robot_token=access_token  # 传入自动获取的AccessToken
            )
            
            print(f"\n📨 钉钉API响应:")
            print(f"   状态码: {result.status_code}")
            print(f"   响应体: {result.text}")
            
            # 更新数据库中的发送状态
            if result.status_code == 200:
                try:
                    response_data = result.json()
                    print(f"   解析后的响应: {response_data}")
                    
                    # 检查钉钉机器人API的响应格式
                    # 成功的响应包含: processQueryKey, flowControlledStaffIdList, invalidStaffIdList
                    # 或者 success=True 或者 errcode=0
                    if 'processQueryKey' in response_data or response_data.get('success') or response_data.get('errcode') == 0:
                        # 检查是否有发送失败的员工
                        invalid_list = response_data.get('invalidStaffIdList', [])
                        if invalid_list and len(invalid_list) > 0:
                            assignment.notification_sent = False
                            assignment.notification_error = f"员工ID无效: {', '.join(invalid_list)}"
                            print(f"❌ 员工ID无效，通知未发送")
                        else:
                            assignment.notification_sent = True
                            assignment.notification_error = None
                            print(f"✅ 钉钉通知发送成功！")
                    else:
                        assignment.notification_sent = False
                        assignment.notification_error = f"API返回错误: {response_data.get('errmsg', '未知错误')}"
                        print(f"❌ 钉钉API返回错误: {assignment.notification_error}")
                except Exception as e:
                    # 状态码200但解析失败，也算成功
                    assignment.notification_sent = True
                    assignment.notification_error = None
                    print(f"✅ 钉钉通知发送成功（响应解析异常但状态码200）")
            else:
                assignment.notification_sent = False
                assignment.notification_error = f"HTTP {result.status_code}: {result.text[:100]}"
                print(f"❌ 钉钉通知发送失败，状态码: {result.status_code}")
            
            db.session.commit()
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"❌ 发送钉钉通知异常: {str(e)}")
            import traceback
            traceback.print_exc()
            print("=" * 60 + "\n")
        
        created_assignments.append(assignment)
    
    db.session.commit()
    
    return jsonify({
        'message': f'成功创建 {len(created_assignments)} 个任务分配',
        'assignments': [assign.to_dict() for assign in created_assignments]
    }), 201


@app.route('/api/assignments/<int:assignment_id>/accept', methods=['GET', 'POST'])
def accept_assignment(assignment_id):
    """接受任务"""
    assignment = Assignment.query.get_or_404(assignment_id)
    assignment.status = 'accepted'
    assignment.responded_at = datetime.now()
    db.session.commit()
    
    return jsonify({
        'message': '任务已接受',
        'assignment': assignment.to_dict()
    })


@app.route('/api/assignments/<int:assignment_id>/reject', methods=['POST'])
def reject_assignment(assignment_id):
    """拒绝任务"""
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.json
    
    assignment.status = 'rejected'
    assignment.reject_reason = data.get('reason', '未提供原因')
    assignment.responded_at = datetime.now()
    db.session.commit()
    
    return jsonify({
        'message': '任务已拒绝',
        'assignment': assignment.to_dict()
    })


@app.route('/api/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    """获取单个任务分配详情"""
    assignment = Assignment.query.get_or_404(assignment_id)
    return jsonify(assignment.to_dict())


@app.route('/api/assignments/<int:assignment_id>/complete', methods=['POST'])
def complete_assignment(assignment_id):
    """员工提交任务完成情况"""
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.json
    
    assignment.status = 'completed'
    assignment.completed_at = datetime.now()
    assignment.actual_hours = data.get('actual_hours')
    assignment.completion_note = data.get('completion_note', '')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '完成情况已提交',
        'assignment': assignment.to_dict()
    })


@app.route('/api/assignments/<int:assignment_id>/review', methods=['POST'])
def review_assignment(assignment_id):
    """经理评价任务完成情况"""
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.json
    
    assignment.efficiency_rating = data.get('efficiency_rating')
    assignment.quality_rating = data.get('quality_rating')
    assignment.review_comment = data.get('review_comment', '')
    assignment.reviewed_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '评价已保存',
        'assignment': assignment.to_dict()
    })


# ==================== 钉钉免密登录 ====================

@app.route('/api/dingtalk/config', methods=['GET'])
def get_dingtalk_config():
    """
    获取钉钉配置信息（前端需要）
    根据 user_type 参数返回对应应用的配置
    """
    user_type = request.args.get('type', 'employee')  # 'admin' 或 'employee'
    
    if user_type == 'admin':
        # 人工任务分配应用（管理员端）
        return jsonify({
            'corpId': 'ding795a49edf28b4433',
            'appKey': DINGTALK_TASK_APP_KEY,
            'appId': '1981b38d-0762-4589-80d0-e600d92cb487'
        })
    else:
        # 我的任务管理应用（员工端）
        return jsonify({
            'corpId': 'ding795a49edf28b4433',
            'appKey': DINGTALK_EMPLOYEE_APP_KEY,
            'appId': '7a5d1d01-023a-439a-a220-c907f6fcfd36'
        })


@app.route('/api/dingtalk/auth', methods=['POST'])
def dingtalk_auth():
    """
    处理钉钉免密登录
    接收授权码，返回用户信息
    """
    try:
        data = request.get_json()
        auth_code = data.get('authCode')
        user_type = data.get('type', 'employee')  # 'admin' 或 'employee'
        
        if not auth_code:
            return jsonify({
                'success': False,
                'message': '缺少授权码'
            }), 400
        
        print(f"\n{'='*60}")
        print(f"🔐 处理钉钉免密登录")
        print(f"   用户类型: {user_type}")
        print(f"   授权码: {auth_code[:20]}...")
        
        # 1. 获取 Access Token（根据用户类型选择应用）
        app_type = 'task_app' if user_type == 'admin' else 'employee_app'
        access_token = get_dingtalk_access_token(app_type)
        
        if not access_token:
            print(f"❌ 获取 Access Token 失败")
            print(f"{'='*60}\n")
            return jsonify({
                'success': False,
                'message': '获取 Access Token 失败'
            }), 500
        
        # 2. 通过授权码获取用户信息
        print(f"📱 正在获取用户信息...")
        user_info_url = "https://oapi.dingtalk.com/topapi/v2/user/getuserinfo"
        params = {'access_token': access_token}
        payload = {'code': auth_code}
        
        response = req.post(user_info_url, params=params, json=payload, timeout=10)
        result = response.json()
        
        print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get('errcode') == 0:
            user_data = result.get('result', {})
            userid = user_data.get('userid')
            
            print(f"✅ 用户信息获取成功")
            print(f"   UserId: {userid}")
            
            # 3. 查询数据库中的员工信息
            employee = Employee.query.filter_by(dingtalk_id=userid).first()
            
            if employee:
                print(f"✅ 找到员工: {employee.name}")
                print(f"{'='*60}\n")
                
                return jsonify({
                    'success': True,
                    'message': '登录成功',
                    'data': {
                        'userid': userid,
                        'name': user_data.get('name'),
                        'employee': {
                            'id': employee.id,
                            'name': employee.name,
                            'dingtalk_id': employee.dingtalk_id
                        }
                    }
                })
            else:
                print(f"⚠️  用户不在系统中: {userid}")
                print(f"{'='*60}\n")
                
                return jsonify({
                    'success': False,
                    'message': '该钉钉账号未绑定员工，请联系管理员',
                    'data': {
                        'userid': userid,
                        'name': user_data.get('name')
                    }
                }), 403
        else:
            print(f"❌ 获取用户信息失败: {result}")
            print(f"{'='*60}\n")
            
            return jsonify({
                'success': False,
                'message': f"获取用户信息失败: {result.get('errmsg', '未知错误')}"
            }), 500
            
    except Exception as e:
        print(f"❌ 免密登录异常: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


# ==================== 自主任务API ====================

@app.route('/api/self-tasks', methods=['GET'])
def get_self_tasks():
    """
    获取员工自主任务列表
    参数: employee_id - 员工ID
    """
    employee_id = request.args.get('employee_id')
    
    if not employee_id:
        return jsonify({'error': '缺少employee_id参数'}), 400
    
    tasks = SelfTask.query.filter_by(employee_id=employee_id).order_by(SelfTask.created_at.desc()).all()
    return jsonify([task.to_dict() for task in tasks])


@app.route('/api/self-tasks', methods=['POST'])
def create_self_task():
    """创建员工自主任务"""
    data = request.json
    
    if not data.get('employee_id'):
        return jsonify({'error': '缺少employee_id'}), 400
    if not data.get('name'):
        return jsonify({'error': '缺少任务名称'}), 400
    if not data.get('estimated_hours'):
        return jsonify({'error': '缺少预计耗时'}), 400
    if not data.get('task_type'):
        return jsonify({'error': '缺少任务类型'}), 400
    
    task = SelfTask(
        employee_id=data.get('employee_id'),
        name=data.get('name'),
        estimated_hours=float(data.get('estimated_hours')),
        deadline=data.get('deadline'),
        task_type=data.get('task_type'),
        description=data.get('description'),
        status='pending'
    )
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201


@app.route('/api/self-tasks/<int:task_id>', methods=['DELETE'])
def delete_self_task(task_id):
    """删除自主任务"""
    task = SelfTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204


@app.route('/api/self-tasks/<int:task_id>/complete', methods=['POST'])
def complete_self_task(task_id):
    """完成自主任务（可选填写完成情况）"""
    task = SelfTask.query.get_or_404(task_id)
    data = request.json or {}
    
    task.status = 'completed'
    task.completed_at = datetime.now()
    
    # 可选的完成记录
    if 'actual_hours' in data:
        task.actual_hours = data.get('actual_hours')
    if 'completion_note' in data:
        task.completion_note = data.get('completion_note')
    
    db.session.commit()
    return jsonify({
        'success': True,
        'message': '任务已完成',
        'task': task.to_dict()
    })


# ==================== 不可用时间API ====================

@app.route('/api/unavailable-times', methods=['GET'])
def get_unavailable_times():
    """
    获取员工不可用时间列表
    参数: employee_id - 员工ID
    """
    employee_id = request.args.get('employee_id')
    
    if not employee_id:
        return jsonify({'error': '缺少employee_id参数'}), 400
    
    times = UnavailableTime.query.filter_by(employee_id=employee_id).order_by(UnavailableTime.date.desc()).all()
    return jsonify([t.to_dict() for t in times])


@app.route('/api/unavailable-times', methods=['POST'])
def create_unavailable_time():
    """创建不可用时间"""
    data = request.json
    
    if not data.get('employee_id'):
        return jsonify({'error': '缺少employee_id'}), 400
    if not data.get('date'):
        return jsonify({'error': '缺少日期'}), 400
    if not data.get('start_time'):
        return jsonify({'error': '缺少开始时间'}), 400
    if not data.get('end_time'):
        return jsonify({'error': '缺少结束时间'}), 400
    if not data.get('reason_type'):
        return jsonify({'error': '缺少原因类型'}), 400
    
    unavailable = UnavailableTime(
        employee_id=data.get('employee_id'),
        date=data.get('date'),
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        reason_type=data.get('reason_type'),
        note=data.get('note')
    )
    db.session.add(unavailable)
    db.session.commit()
    
    return jsonify(unavailable.to_dict()), 201


@app.route('/api/unavailable-times/<int:time_id>', methods=['DELETE'])
def delete_unavailable_time(time_id):
    """删除不可用时间"""
    unavailable = UnavailableTime.query.get_or_404(time_id)
    db.session.delete(unavailable)
    db.session.commit()
    return '', 204


# ==================== 负载计算API ====================

def calculate_workdays_between(start_date, end_date):
    """计算两个日期之间的工作日数量（周一至周五）"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    workdays = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # 0-4 是周一到周五
            workdays += 1
        current += timedelta(days=1)
    return workdays


def get_workdays_in_range(start_date, end_date):
    """获取日期范围内的所有工作日列表"""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    workdays = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:
            workdays.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    return workdays


def calculate_task_daily_allocation(task_start, task_end, total_hours, week_start, week_end):
    """
    分摊法：计算任务在本周每天的分摊工时
    
    参数：
        task_start: 任务开始日期
        task_end: 任务截止日期
        total_hours: 任务总预计耗时
        week_start: 本周开始日期
        week_end: 本周结束日期
    
    返回：
        dict: {日期: 分摊工时}
    """
    if isinstance(task_start, str):
        task_start = datetime.strptime(task_start, '%Y-%m-%d')
    if isinstance(task_end, str):
        task_end = datetime.strptime(task_end, '%Y-%m-%d')
    if isinstance(week_start, str):
        week_start = datetime.strptime(week_start, '%Y-%m-%d')
    if isinstance(week_end, str):
        week_end = datetime.strptime(week_end, '%Y-%m-%d')
    
    # 计算任务周期内的总工作日
    task_workdays = get_workdays_in_range(task_start, task_end)
    if not task_workdays:
        return {}
    
    # 每个工作日分摊的工时
    daily_hours = total_hours / len(task_workdays)
    
    # 计算本周内该任务的分摊
    week_workdays = get_workdays_in_range(week_start, week_end)
    allocation = {}
    
    for day in week_workdays:
        if day in task_workdays:
            allocation[day] = daily_hours
    
    return allocation


@app.route('/api/workload/<int:employee_id>', methods=['GET'])
def get_employee_workload(employee_id):
    """
    获取员工负载数据（分摊法计算）
    
    分摊法逻辑：
    1. 每个任务根据开始时间和截止时间，计算任务周期内的工作日数
    2. 将任务预计耗时均匀分摊到每个工作日
    3. 累加本周每天的分摊时长，得到本周任务占用
    4. 负载指数 = 本周任务占用 / (本周可用工时 - 不可用时间) × 100%
    """
    # 获取查询参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    daily_hours = float(request.args.get('daily_hours', 8))
    
    # 默认使用本周
    if not start_date or not end_date:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        start_date = start_of_week.strftime('%Y-%m-%d')
        end_date = end_of_week.strftime('%Y-%m-%d')
    
    week_start = datetime.strptime(start_date, '%Y-%m-%d')
    week_end = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 获取本周工作日列表
    week_workdays = get_workdays_in_range(week_start, week_end)
    work_days = len(week_workdays)
    
    # 初始化每日数据
    daily_workload = {}
    for day in week_workdays:
        daily_workload[day] = {
            'date': day,
            'dayOfWeek': datetime.strptime(day, '%Y-%m-%d').strftime('%A'),
            'dayLabel': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.strptime(day, '%Y-%m-%d').weekday()],
            'availableHours': daily_hours,
            'unavailableHours': 0,
            'managerTaskHours': 0,
            'selfTaskHours': 0,
            'totalTaskHours': 0,
            'isWorkday': True
        }
    
    # 添加周末（用于图表展示）
    current = week_start
    while current <= week_end:
        day_str = current.strftime('%Y-%m-%d')
        if day_str not in daily_workload:
            daily_workload[day_str] = {
                'date': day_str,
                'dayOfWeek': current.strftime('%A'),
                'dayLabel': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][current.weekday()],
                'availableHours': 0,
                'unavailableHours': 0,
                'managerTaskHours': 0,
                'selfTaskHours': 0,
                'totalTaskHours': 0,
                'isWorkday': False
            }
        current += timedelta(days=1)
    
    # ========== 1. 处理管理员分配的任务（分摊法） ==========
    assignments = Assignment.query.filter_by(employee_id=employee_id).filter(
        Assignment.status.in_(['pending', 'accepted'])
    ).all()
    
    manager_tasks = []
    manager_task_hours_total = 0  # 任务总工时（用于展示）
    manager_task_hours_week = 0   # 本周分摊工时（用于负载计算）
    
    for assign in assignments:
        task = Task.query.get(assign.task_id)
        if not task:
            continue
        
        estimated_hours = task.estimated_hours if task.estimated_hours else 0
        manager_task_hours_total += estimated_hours
        
        # 确定任务开始和结束日期
        # 开始日期：使用分配时间
        task_start = assign.assigned_at.strftime('%Y-%m-%d') if assign.assigned_at else start_date
        # 结束日期：使用任务截止日期，如果没有则假设一周后
        if task.deadline:
            try:
                task_end = task.deadline.split('T')[0] if 'T' in task.deadline else task.deadline
            except:
                task_end = (week_end + timedelta(days=7)).strftime('%Y-%m-%d')
        else:
            task_end = (week_end + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # 计算分摊
        allocation = calculate_task_daily_allocation(task_start, task_end, estimated_hours, start_date, end_date)
        
        # 累加到每日数据
        task_week_hours = 0
        for day, hours in allocation.items():
            if day in daily_workload:
                daily_workload[day]['managerTaskHours'] += hours
                daily_workload[day]['totalTaskHours'] += hours
                task_week_hours += hours
        
        manager_task_hours_week += task_week_hours
        
        # 构建任务数据
        task_data = assign.to_dict()
        task_data['estimatedHours'] = estimated_hours
        task_data['importance'] = task.importance if task else 5
        task_data['weekHours'] = round(task_week_hours, 2)
        task_data['taskStart'] = task_start
        task_data['taskEnd'] = task_end
        manager_tasks.append(task_data)
    
    # ========== 2. 处理自主任务（分摊法） ==========
    self_tasks_query = SelfTask.query.filter_by(employee_id=employee_id, status='pending').all()
    self_tasks = []
    self_task_hours_total = 0
    self_task_hours_week = 0
    
    for task in self_tasks_query:
        estimated_hours = task.estimated_hours if task.estimated_hours else 0
        self_task_hours_total += estimated_hours
        
        # 确定任务开始和结束日期
        # 对于自主任务，使用更灵活的开始日期策略
        created_date = task.created_at.strftime('%Y-%m-%d') if task.created_at else start_date
        
        # 如果任务创建于本周内，使用本周一作为开始日期（确保本周有分摊）
        created_datetime = datetime.strptime(created_date, '%Y-%m-%d')
        if created_datetime >= week_start and created_datetime <= week_end:
            task_start = start_date  # 使用本周一
        else:
            task_start = created_date
        
        if task.deadline:
            task_end = task.deadline.split('T')[0] if 'T' in task.deadline else task.deadline
        else:
            # 无截止日期的任务，从开始日期算起7个工作日
            task_start_dt = datetime.strptime(task_start, '%Y-%m-%d')
            task_end = (task_start_dt + timedelta(days=14)).strftime('%Y-%m-%d')  # 约2周时间
        
        # 计算分摊
        allocation = calculate_task_daily_allocation(task_start, task_end, estimated_hours, start_date, end_date)
        
        # 累加到每日数据
        task_week_hours = 0
        for day, hours in allocation.items():
            if day in daily_workload:
                daily_workload[day]['selfTaskHours'] += hours
                daily_workload[day]['totalTaskHours'] += hours
                task_week_hours += hours
        
        self_task_hours_week += task_week_hours
        
        # 构建任务数据
        task_data = task.to_dict()
        task_data['weekHours'] = round(task_week_hours, 2)
        task_data['taskStart'] = task_start
        task_data['taskEnd'] = task_end
        self_tasks.append(task_data)
    
    # ========== 3. 处理不可用时间 ==========
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date >= start_date,
        UnavailableTime.date <= end_date
    ).all()
    
    unavailable_hours = 0
    for ut in unavailable_times:
        if ut.date in daily_workload:
            try:
                start_parts = ut.start_time.split(':')
                end_parts = ut.end_time.split(':')
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
                hours = (end_minutes - start_minutes) / 60
                daily_workload[ut.date]['unavailableHours'] += hours
                unavailable_hours += hours
            except:
                pass
    
    # ========== 4. 计算负载统计 ==========
    total_available_hours = work_days * daily_hours
    actual_available_hours = max(0, total_available_hours - unavailable_hours)
    total_task_hours_week = manager_task_hours_week + self_task_hours_week
    
    # 负载比例
    if actual_available_hours > 0:
        workload_ratio = (total_task_hours_week / actual_available_hours) * 100
    else:
        workload_ratio = 100 if total_task_hours_week > 0 else 0
    
    # 负载等级
    if workload_ratio >= 100:
        workload_level = 'overload'
        workload_label = '超负荷'
    elif workload_ratio >= 80:
        workload_level = 'high'
        workload_label = '高负载'
    elif workload_ratio >= 50:
        workload_level = 'medium'
        workload_label = '中等'
    else:
        workload_level = 'low'
        workload_label = '较轻'
    
    # 四舍五入每日数据
    for day in daily_workload:
        daily_workload[day]['managerTaskHours'] = round(daily_workload[day]['managerTaskHours'], 2)
        daily_workload[day]['selfTaskHours'] = round(daily_workload[day]['selfTaskHours'], 2)
        daily_workload[day]['totalTaskHours'] = round(daily_workload[day]['totalTaskHours'], 2)
        daily_workload[day]['unavailableHours'] = round(daily_workload[day]['unavailableHours'], 2)
    
    # 按日期排序
    sorted_daily = sorted(daily_workload.values(), key=lambda x: x['date'])
    
    # 饼图数据
    pie_chart_data = {
        'managerTaskHours': round(manager_task_hours_week, 1),
        'selfTaskHours': round(self_task_hours_week, 1),
        'unavailableHours': round(unavailable_hours, 1),
        'freeHours': round(max(0, actual_available_hours - total_task_hours_week), 1)
    }
    
    return jsonify({
        'employeeId': employee_id,
        'dateRange': {
            'startDate': start_date,
            'endDate': end_date
        },
        'settings': {
            'dailyHours': daily_hours
        },
        'managerTasks': manager_tasks,
        'selfTasks': self_tasks,
        'unavailableTimes': [t.to_dict() for t in unavailable_times],
        'statistics': {
            'workDays': work_days,
            'totalAvailableHours': round(total_available_hours, 1),
            'unavailableHours': round(unavailable_hours, 1),
            'actualAvailableHours': round(actual_available_hours, 1),
            'managerTaskHoursTotal': round(manager_task_hours_total, 1),
            'managerTaskHoursWeek': round(manager_task_hours_week, 1),
            'selfTaskHoursTotal': round(self_task_hours_total, 1),
            'selfTaskHoursWeek': round(self_task_hours_week, 1),
            'totalTaskHoursWeek': round(total_task_hours_week, 1),
            'workloadRatio': round(min(workload_ratio, 200), 1),  # 限制最大200%
            'workloadLevel': workload_level,
            'workloadLabel': workload_label
        },
        'dailyWorkload': sorted_daily,
        'pieChartData': pie_chart_data
    })


# ==================== 自动任务分配API ====================

def calculate_skill_match(task, employee):
    """
    计算员工与任务的技能匹配度
    
    返回：
        match_ratio: 匹配度百分比 (0-100)
        matched_skills: 匹配到的技能列表
        avg_rating: 匹配技能的平均评分
    """
    # 获取任务所需技能ID列表
    task_skill_ids = set([ts.skill_id for ts in task.task_skills])
    
    if not task_skill_ids:
        # 任务没有设置技能要求，视为完全匹配
        return 100, [], 10
    
    # 获取员工技能
    employee_skill_map = {}  # skill_id -> rating
    for es in employee.employee_skills:
        employee_skill_map[es.skill_id] = es.rating
    
    # 计算匹配
    matched_skills = []
    matched_ratings = []
    
    for skill_id in task_skill_ids:
        if skill_id in employee_skill_map:
            skill = Skill.query.get(skill_id)
            matched_skills.append({
                'skill_id': skill_id,
                'skill_name': skill.name if skill else '',
                'rating': employee_skill_map[skill_id]
            })
            matched_ratings.append(employee_skill_map[skill_id])
    
    # 计算匹配度
    if len(task_skill_ids) > 0:
        match_ratio = (len(matched_skills) / len(task_skill_ids)) * 100
    else:
        match_ratio = 100
    
    # 平均评分
    avg_rating = sum(matched_ratings) / len(matched_ratings) if matched_ratings else 0
    
    return match_ratio, matched_skills, avg_rating


def get_employee_current_workload(employee_id):
    """
    获取员工当前的负载数据（简化版，用于自动分配）
    
    返回：
        workload_ratio: 负载百分比
        available_hours: 本周可用工时
        task_hours: 本周任务工时
    """
    from datetime import datetime, timedelta
    
    # 获取本周日期范围
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    start_date = start_of_week.strftime('%Y-%m-%d')
    end_date = end_of_week.strftime('%Y-%m-%d')
    
    daily_hours = 8
    
    # 计算工作日
    week_workdays = get_workdays_in_range(start_of_week, end_of_week)
    work_days = len(week_workdays)
    
    # 计算不可用时间
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date >= start_date,
        UnavailableTime.date <= end_date
    ).all()
    
    unavailable_hours = 0
    for ut in unavailable_times:
        try:
            start_parts = ut.start_time.split(':')
            end_parts = ut.end_time.split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            hours = (end_minutes - start_minutes) / 60
            unavailable_hours += hours
        except:
            pass
    
    # 计算经理分配的任务工时（分摊法）
    assignments = Assignment.query.filter_by(employee_id=employee_id).filter(
        Assignment.status.in_(['pending', 'accepted'])
    ).all()
    
    manager_task_hours_week = 0
    for assign in assignments:
        task = Task.query.get(assign.task_id)
        if not task:
            continue
        
        estimated_hours = task.estimated_hours if task.estimated_hours else 0
        
        task_start = assign.assigned_at.strftime('%Y-%m-%d') if assign.assigned_at else start_date
        if task.deadline:
            try:
                task_end = task.deadline.split('T')[0] if 'T' in task.deadline else task.deadline
            except:
                task_end = (end_of_week + timedelta(days=7)).strftime('%Y-%m-%d')
        else:
            task_end = (end_of_week + timedelta(days=7)).strftime('%Y-%m-%d')
        
        allocation = calculate_task_daily_allocation(task_start, task_end, estimated_hours, start_date, end_date)
        task_week_hours = sum(allocation.values())
        manager_task_hours_week += task_week_hours
    
    # 计算自主任务工时
    self_tasks = SelfTask.query.filter_by(employee_id=employee_id, status='pending').all()
    self_task_hours_week = 0
    
    for task in self_tasks:
        estimated_hours = task.estimated_hours if task.estimated_hours else 0
        task_start = task.created_at.strftime('%Y-%m-%d') if task.created_at else start_date
        if task.deadline:
            task_end = task.deadline.split('T')[0] if 'T' in task.deadline else task.deadline
        else:
            task_end = (end_of_week + timedelta(days=7)).strftime('%Y-%m-%d')
        
        allocation = calculate_task_daily_allocation(task_start, task_end, estimated_hours, start_date, end_date)
        self_task_hours_week += sum(allocation.values())
    
    # 计算负载
    total_available_hours = work_days * daily_hours
    actual_available_hours = max(0, total_available_hours - unavailable_hours)
    total_task_hours = manager_task_hours_week + self_task_hours_week
    
    if actual_available_hours > 0:
        workload_ratio = (total_task_hours / actual_available_hours) * 100
    else:
        workload_ratio = 100 if total_task_hours > 0 else 0
    
    return workload_ratio, actual_available_hours, total_task_hours


def score_employee_for_task(task, employee, skill_match_ratio, avg_skill_rating, workload_ratio, available_hours, task_hours):
    """
    给候选员工打分
    
    评分权重：
    - 技能匹配度：40%
    - 技能评分：20%
    - 负载指数（越低越好）：25%
    - 可用工时匹配度：15%
    
    返回：总分 (0-100)
    """
    score = 0
    score_details = {}
    
    # 1. 技能匹配度得分 (40分满分)
    skill_match_score = (skill_match_ratio / 100) * 40
    score += skill_match_score
    score_details['skill_match'] = round(skill_match_score, 2)
    
    # 2. 技能评分得分 (20分满分)
    skill_rating_score = (avg_skill_rating / 10) * 20
    score += skill_rating_score
    score_details['skill_rating'] = round(skill_rating_score, 2)
    
    # 3. 负载指数得分 (25分满分，负载越低分数越高)
    # 负载0%=满分，负载100%=0分
    workload_score = max(0, (100 - workload_ratio) / 100) * 25
    score += workload_score
    score_details['workload'] = round(workload_score, 2)
    
    # 4. 可用工时匹配度 (15分满分)
    task_estimated_hours = task.estimated_hours if task.estimated_hours else 0
    remaining_hours = max(0, available_hours - task_hours)
    
    if task_estimated_hours > 0 and remaining_hours > 0:
        # 如果剩余工时能覆盖任务所需工时，得满分；否则按比例
        if remaining_hours >= task_estimated_hours:
            hours_match_score = 15
        else:
            hours_match_score = (remaining_hours / task_estimated_hours) * 15
    else:
        hours_match_score = 0
    score += hours_match_score
    score_details['hours_match'] = round(hours_match_score, 2)
    
    return round(score, 2), score_details


@app.route('/api/auto-assign', methods=['POST'])
def auto_assign_tasks():
    """
    自动任务分配
    
    算法逻辑：
    1. 按任务重要性排序（高优先），同等重要性按截止时间近的优先
    2. 筛选符合技能需求且匹配度≥80%的员工，剔除负载超过阈值的员工
    3. 给候选员工打分
    4. 分配给评分最高的员工
    5. 可选进行负载平衡调整
    """
    data = request.json or {}
    manager_dingtalk_id = data.get('manager_dingtalk_id')
    
    # 配置参数
    skill_match_threshold = data.get('skill_match_threshold', 80)  # 技能匹配度阈值
    workload_threshold = data.get('workload_threshold', 85)  # 负载阈值
    enable_balance = data.get('enable_balance', True)  # 是否启用负载平衡
    
    print("=" * 60)
    print("🤖 开始自动任务分配")
    print(f"   管理员: {manager_dingtalk_id}")
    print(f"   技能匹配阈值: {skill_match_threshold}%")
    print(f"   负载阈值: {workload_threshold}%")
    print("=" * 60)
    
    # 1. 获取待分配的任务（未分配或所有分配都被拒绝的任务）
    all_tasks = Task.query.order_by(
        Task.importance.desc(),  # 重要性降序
        Task.deadline.asc()       # 截止日期升序
    ).all()
    
    # 筛选可分配的任务
    unassigned_tasks = []
    for task in all_tasks:
        task_assignments = Assignment.query.filter_by(task_id=task.id).all()
        
        if not task_assignments:
            # 没有分配记录
            unassigned_tasks.append(task)
        elif all(a.status == 'rejected' for a in task_assignments):
            # 所有分配都被拒绝
            unassigned_tasks.append(task)
        elif not any(a.status in ['pending', 'accepted'] for a in task_assignments):
            # 没有进行中的分配
            unassigned_tasks.append(task)
    
    print(f"📋 待分配任务数: {len(unassigned_tasks)}")
    
    # 2. 获取可用员工列表
    if manager_dingtalk_id:
        available_employees = Employee.query.filter_by(manager_dingtalk_id=manager_dingtalk_id).all()
    else:
        available_employees = Employee.query.all()
    
    print(f"👥 可用员工数: {len(available_employees)}")
    
    if not unassigned_tasks:
        return jsonify({
            'success': True,
            'message': '没有需要分配的任务',
            'assignments': [],
            'statistics': {
                'total_tasks': 0,
                'assigned_tasks': 0,
                'unassigned_tasks': 0
            }
        })
    
    if not available_employees:
        return jsonify({
            'success': False,
            'message': '没有可用的员工',
            'assignments': [],
            'statistics': {
                'total_tasks': len(unassigned_tasks),
                'assigned_tasks': 0,
                'unassigned_tasks': len(unassigned_tasks)
            }
        })
    
    # 缓存员工负载数据（会随着分配更新）
    employee_workload_cache = {}
    for emp in available_employees:
        workload_ratio, available_hours, task_hours = get_employee_current_workload(emp.id)
        employee_workload_cache[emp.id] = {
            'workload_ratio': workload_ratio,
            'available_hours': available_hours,
            'task_hours': task_hours
        }
    
    # 3. 执行分配
    auto_assignments = []
    unassigned_reasons = []
    
    for task in unassigned_tasks:
        print(f"\n📌 处理任务: {task.name} (重要度: {task.importance}, 预计: {task.estimated_hours}h)")
        
        # 获取任务所需技能
        task_skill_ids = [ts.skill_id for ts in task.task_skills]
        task_skills = [Skill.query.get(sid) for sid in task_skill_ids]
        task_skill_names = [s.name for s in task_skills if s]
        
        print(f"   所需技能: {task_skill_names}")
        
        # 筛选候选员工
        candidates = []
        
        for emp in available_employees:
            # 计算技能匹配度
            match_ratio, matched_skills, avg_rating = calculate_skill_match(task, emp)
            
            # 获取当前负载
            emp_workload = employee_workload_cache[emp.id]
            workload_ratio = emp_workload['workload_ratio']
            available_hours = emp_workload['available_hours']
            task_hours = emp_workload['task_hours']
            
            # 筛选条件
            if match_ratio < skill_match_threshold:
                print(f"   ❌ {emp.name}: 技能匹配度 {match_ratio:.1f}% < {skill_match_threshold}%")
                continue
            
            if workload_ratio > workload_threshold:
                print(f"   ❌ {emp.name}: 负载 {workload_ratio:.1f}% > {workload_threshold}%")
                continue
            
            # 计算评分
            score, score_details = score_employee_for_task(
                task, emp, match_ratio, avg_rating, workload_ratio, available_hours, task_hours
            )
            
            candidates.append({
                'employee': emp,
                'score': score,
                'score_details': score_details,
                'match_ratio': match_ratio,
                'matched_skills': matched_skills,
                'avg_rating': avg_rating,
                'workload_ratio': workload_ratio,
                'available_hours': available_hours
            })
            
            print(f"   ✅ {emp.name}: 得分 {score} (匹配{match_ratio:.0f}%, 负载{workload_ratio:.0f}%)")
        
        if not candidates:
            unassigned_reasons.append({
                'task_id': task.id,
                'task_name': task.name,
                'reason': '没有符合条件的候选员工'
            })
            print(f"   ⚠️  无可用候选员工")
            continue
        
        # 选择得分最高的员工
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best_candidate = candidates[0]
        selected_employee = best_candidate['employee']
        
        print(f"   🎯 选中: {selected_employee.name} (得分: {best_candidate['score']})")
        
        # 模拟更新员工负载缓存（假设任务被接受）
        task_estimated_hours = task.estimated_hours if task.estimated_hours else 0
        employee_workload_cache[selected_employee.id]['task_hours'] += task_estimated_hours
        if employee_workload_cache[selected_employee.id]['available_hours'] > 0:
            new_workload = (employee_workload_cache[selected_employee.id]['task_hours'] / 
                          employee_workload_cache[selected_employee.id]['available_hours']) * 100
            employee_workload_cache[selected_employee.id]['workload_ratio'] = new_workload
        
        # 添加到分配结果
        auto_assignments.append({
            'task': task.to_dict(),
            'employee': selected_employee.to_dict(),
            'score': best_candidate['score'],
            'score_details': best_candidate['score_details'],
            'match_ratio': best_candidate['match_ratio'],
            'matched_skills': best_candidate['matched_skills'],
            'workload_before': best_candidate['workload_ratio'],
            'workload_after': employee_workload_cache[selected_employee.id]['workload_ratio'],
            'candidates_count': len(candidates),
            'all_candidates': [{
                'employee_id': c['employee'].id,
                'employee_name': c['employee'].name,
                'score': c['score'],
                'match_ratio': c['match_ratio'],
                'workload_ratio': c['workload_ratio']
            } for c in candidates[:5]]  # 最多返回前5名候选
        })
    
    # 4. 计算员工负载变化汇总
    employee_workload_changes = []
    assigned_employee_ids = set()
    for assign in auto_assignments:
        emp_id = assign['employee']['id']
        if emp_id not in assigned_employee_ids:
            assigned_employee_ids.add(emp_id)
            emp = Employee.query.get(emp_id)
            if emp:
                # 获取分配前的负载
                original_workload, original_available, original_task_hours = get_employee_current_workload(emp_id)
                
                # 计算分配后的负载
                final_data = employee_workload_cache[emp_id]
                
                # 计算该员工被分配的任务数和总工时
                emp_tasks = [a for a in auto_assignments if a['employee']['id'] == emp_id]
                assigned_task_count = len(emp_tasks)
                assigned_hours = sum(a['task'].get('estimated_hours', 0) or 0 for a in emp_tasks)
                
                # 负载等级
                def get_workload_level(ratio):
                    if ratio >= 100:
                        return {'level': 'overload', 'label': '超负荷', 'color': '#ef4444'}
                    elif ratio >= 80:
                        return {'level': 'high', 'label': '高负载', 'color': '#f59e0b'}
                    elif ratio >= 50:
                        return {'level': 'medium', 'label': '中等', 'color': '#3b82f6'}
                    else:
                        return {'level': 'low', 'label': '较轻', 'color': '#10b981'}
                
                employee_workload_changes.append({
                    'employee_id': emp_id,
                    'employee_name': emp.name,
                    'workload_before': round(original_workload, 1),
                    'workload_after': round(final_data['workload_ratio'], 1),
                    'workload_change': round(final_data['workload_ratio'] - original_workload, 1),
                    'level_before': get_workload_level(original_workload),
                    'level_after': get_workload_level(final_data['workload_ratio']),
                    'available_hours': round(final_data['available_hours'], 1),
                    'assigned_task_count': assigned_task_count,
                    'assigned_hours': round(assigned_hours, 1)
                })
    
    # 按负载变化排序
    employee_workload_changes.sort(key=lambda x: x['workload_change'], reverse=True)
    
    # 5. 计算任务延期风险
    task_delay_risks = []
    today = datetime.now()
    
    for assign in auto_assignments:
        task = assign['task']
        emp_id = assign['employee']['id']
        
        # 检查任务是否有截止日期
        if task.get('deadline'):
            try:
                deadline_str = task['deadline'].split('T')[0] if 'T' in task['deadline'] else task['deadline']
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                days_until_deadline = (deadline - today).days
                
                estimated_hours = task.get('estimated_hours', 0) or 0
                emp_workload = employee_workload_cache.get(emp_id, {})
                available_hours = emp_workload.get('available_hours', 40) - emp_workload.get('task_hours', 0)
                
                # 计算风险等级
                # 如果剩余天数*8小时 < 任务预计耗时，则有延期风险
                available_work_hours = max(0, days_until_deadline) * 8
                
                risk_level = 'low'
                risk_label = '低风险'
                risk_color = '#10b981'
                risk_reason = ''
                
                if days_until_deadline < 0:
                    risk_level = 'overdue'
                    risk_label = '已逾期'
                    risk_color = '#ef4444'
                    risk_reason = f'已逾期 {abs(days_until_deadline)} 天'
                elif days_until_deadline == 0:
                    risk_level = 'critical'
                    risk_label = '紧急'
                    risk_color = '#ef4444'
                    risk_reason = '今日截止'
                elif estimated_hours > available_work_hours:
                    risk_level = 'high'
                    risk_label = '高风险'
                    risk_color = '#f59e0b'
                    risk_reason = f'任务需 {estimated_hours}h，剩余工作时间约 {available_work_hours}h'
                elif emp_workload.get('workload_ratio', 0) > 90:
                    risk_level = 'medium'
                    risk_label = '中风险'
                    risk_color = '#f59e0b'
                    risk_reason = f'员工负载已达 {emp_workload.get("workload_ratio", 0):.0f}%'
                elif days_until_deadline <= 3:
                    risk_level = 'medium'
                    risk_label = '中风险'
                    risk_color = '#f59e0b'
                    risk_reason = f'仅剩 {days_until_deadline} 天'
                
                if risk_level in ['overdue', 'critical', 'high', 'medium']:
                    task_delay_risks.append({
                        'task_id': task['id'],
                        'task_name': task['name'],
                        'employee_name': assign['employee']['name'],
                        'deadline': deadline_str,
                        'days_until_deadline': days_until_deadline,
                        'estimated_hours': estimated_hours,
                        'risk_level': risk_level,
                        'risk_label': risk_label,
                        'risk_color': risk_color,
                        'risk_reason': risk_reason
                    })
            except Exception as e:
                print(f"解析截止日期失败: {e}")
    
    # 按风险等级排序
    risk_order = {'overdue': 0, 'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
    task_delay_risks.sort(key=lambda x: risk_order.get(x['risk_level'], 5))
    
    # 6. 负载平衡调整（可选）
    balance_adjustments = []
    if enable_balance and len(auto_assignments) > 1:
        # 检查是否有员工负载过高
        final_workloads = {}
        for emp_id, data in employee_workload_cache.items():
            final_workloads[emp_id] = data['workload_ratio']
        
        # 找出负载最高和最低的员工
        max_workload = max(final_workloads.values()) if final_workloads else 0
        min_workload = min(final_workloads.values()) if final_workloads else 0
        
        if max_workload - min_workload > 30:  # 负载差异超过30%
            print(f"\n⚖️  负载差异较大 (最高: {max_workload:.1f}%, 最低: {min_workload:.1f}%)")
            balance_adjustments.append({
                'message': f'负载差异较大，建议手动调整',
                'max_workload': max_workload,
                'min_workload': min_workload
            })
    
    print(f"\n{'='*60}")
    print(f"✅ 自动分配完成")
    print(f"   成功分配: {len(auto_assignments)} 个任务")
    print(f"   未能分配: {len(unassigned_reasons)} 个任务")
    print(f"   有延期风险: {len(task_delay_risks)} 个任务")
    print(f"{'='*60}\n")
    
    return jsonify({
        'success': True,
        'message': f'自动分配完成，共匹配 {len(auto_assignments)} 个任务',
        'assignments': auto_assignments,
        'unassigned_reasons': unassigned_reasons,
        'balance_adjustments': balance_adjustments,
        'employee_workload_changes': employee_workload_changes,
        'task_delay_risks': task_delay_risks,
        'statistics': {
            'total_tasks': len(unassigned_tasks),
            'assigned_tasks': len(auto_assignments),
            'unassigned_tasks': len(unassigned_reasons),
            'delay_risk_count': len(task_delay_risks)
        },
        'config': {
            'skill_match_threshold': skill_match_threshold,
            'workload_threshold': workload_threshold,
            'enable_balance': enable_balance
        }
    })


@app.route('/api/auto-assign/confirm', methods=['POST'])
def confirm_auto_assignments():
    """
    确认并执行自动分配结果
    接收自动分配结果，创建实际的分配记录并发送钉钉通知
    """
    data = request.json
    assignments_to_confirm = data.get('assignments', [])
    assigned_by_dingtalk_id = data.get('assignedByDingtalkId')
    assigned_by_name = data.get('assignedByName', '系统自动分配')
    
    if not assignments_to_confirm:
        return jsonify({'error': '没有待确认的分配'}), 400
    
    print("=" * 60)
    print("📤 确认自动分配结果，开始发送通知")
    print(f"   分配数量: {len(assignments_to_confirm)}")
    print("=" * 60)
    
    created_assignments = []
    
    for assign_data in assignments_to_confirm:
        task_id = assign_data.get('task', {}).get('id') or assign_data.get('taskId')
        employee_id = assign_data.get('employee', {}).get('id') or assign_data.get('employeeId')
        
        task = Task.query.get(task_id)
        employee = Employee.query.get(employee_id)
        
        if not task or not employee:
            print(f"⚠️  跳过无效分配: task_id={task_id}, employee_id={employee_id}")
            continue
        
        # 创建分配记录
        assignment = Assignment(
            task_id=task.id,
            employee_id=employee.id,
            assigned_by_dingtalk_id=assigned_by_dingtalk_id,
            assigned_by_name=assigned_by_name + '(自动)',
            status='pending'
        )
        db.session.add(assignment)
        db.session.flush()
        
        # 构建URL
        base_url = "http://101.37.168.176:8082"
        detail_url = f"{base_url}/employee?id={assignment.id}"
        accept_url = f"{base_url}/accept?id={assignment.id}"
        reject_url = f"{base_url}/reject?id={assignment.id}"
        
        # 发送钉钉通知
        try:
            access_token = get_dingtalk_access_token(app_type='task_app')
            if access_token:
                planned_time = task.deadline if task.deadline else "待定"
                
                result = send_task_notification(
                    task_name=task.name,
                    subtask_name=task.description[:50] + "..." if len(task.description) > 50 else task.description,
                    planned_time=planned_time,
                    detail_url=detail_url,
                    accept_url=accept_url,
                    reject_url=reject_url,
                    employee_dingtalk_id=employee.dingtalk_id,
                    robot_token=access_token
                )
                
                if result.status_code == 200:
                    assignment.notification_sent = True
                    print(f"✅ 通知发送成功: {employee.name} <- {task.name}")
                else:
                    assignment.notification_sent = False
                    assignment.notification_error = f"HTTP {result.status_code}"
                    print(f"❌ 通知发送失败: {employee.name}")
        except Exception as e:
            assignment.notification_sent = False
            assignment.notification_error = str(e)
            print(f"❌ 通知发送异常: {str(e)}")
        
        created_assignments.append(assignment)
    
    db.session.commit()
    
    print(f"\n✅ 确认完成，共创建 {len(created_assignments)} 条分配记录")
    print("=" * 60)
    
    return jsonify({
        'success': True,
        'message': f'成功创建 {len(created_assignments)} 个任务分配并发送通知',
        'assignments': [a.to_dict() for a in created_assignments]
    }), 201


# ==================== 日程制定API ====================

from models import Schedule, ScheduleItem

@app.route('/api/assignments/<int:assignment_id>/employee-importance', methods=['PUT'])
def update_assignment_employee_importance(assignment_id):
    """更新经理任务的员工重要性评分"""
    assignment = Assignment.query.get_or_404(assignment_id)
    data = request.json
    
    importance = data.get('employee_importance')
    if importance is not None:
        if not (1 <= importance <= 10):
            return jsonify({'error': '重要性必须在1-10之间'}), 400
        assignment.employee_importance = importance
    
    db.session.commit()
    return jsonify(assignment.to_dict())


@app.route('/api/self-tasks/<int:task_id>/importance', methods=['PUT'])
def update_self_task_importance(task_id):
    """更新自主任务的重要性"""
    task = SelfTask.query.get_or_404(task_id)
    data = request.json
    
    importance = data.get('importance')
    if importance is not None:
        if not (1 <= importance <= 10):
            return jsonify({'error': '重要性必须在1-10之间'}), 400
        task.importance = importance
    
    db.session.commit()
    return jsonify(task.to_dict())


@app.route('/api/schedule/generate', methods=['POST'])
def generate_schedule():
    """
    自动生成日程排程（支持权重配置）
    
    排程算法：
    1. 收集所有待完成任务（经理任务+自主任务）
    2. 根据用户设置的权重计算优先级得分
    3. 按优先级排序，分配任务到每天
    4. 计算任务进度和延期风险
    """
    data = request.json
    employee_id = data.get('employee_id')
    days = data.get('days', 14)
    daily_hours = data.get('daily_hours', 8)
    
    # 获取权重配置（总和应为100）
    urgency_weight = data.get('urgency_weight', 40)  # 紧急度权重
    importance_weight = data.get('importance_weight', 40)  # 重要度权重
    continuity_weight = data.get('continuity_weight', 20)  # 连续性权重
    
    if not employee_id:
        return jsonify({'error': '缺少employee_id'}), 400
    
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({'error': '员工不存在'}), 404
    
    # 计算日期范围
    today = datetime.now()
    start_date = today.strftime('%Y-%m-%d')
    
    # 获取工作日列表
    work_dates = []
    current = today
    for _ in range(days * 2):
        if current.weekday() < 5:
            work_dates.append(current.strftime('%Y-%m-%d'))
            if len(work_dates) >= days:
                break
        current += timedelta(days=1)
    
    end_date = work_dates[-1] if work_dates else start_date
    
    # 获取不可用时间
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date >= start_date,
        UnavailableTime.date <= end_date
    ).all()
    
    # 构建每日不可用时间映射
    daily_unavailable = {}
    for ut in unavailable_times:
        if ut.date not in daily_unavailable:
            daily_unavailable[ut.date] = []
        try:
            start_parts = ut.start_time.split(':')
            end_parts = ut.end_time.split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            hours = (end_minutes - start_minutes) / 60
            daily_unavailable[ut.date].append({
                'id': ut.id,
                'reason': ut.get_reason_type_label(),
                'note': ut.note,
                'startTime': ut.start_time,
                'endTime': ut.end_time,
                'hours': round(hours, 2)
            })
        except:
            pass
    
    # 构建每日可用时间
    daily_available = {}
    for date in work_dates:
        unavail_hours = sum(u['hours'] for u in daily_unavailable.get(date, []))
        daily_available[date] = max(0, daily_hours - unavail_hours)
    
    # 收集所有任务
    all_tasks = []
    
    # 1. 经理分配的任务
    assignments = Assignment.query.filter_by(employee_id=employee_id).filter(
        Assignment.status.in_(['pending', 'accepted'])
    ).all()
    
    for assign in assignments:
        task = Task.query.get(assign.task_id)
        if not task:
            continue
        
        manager_imp = task.importance or 5
        employee_imp = assign.employee_importance
        combined_importance = (manager_imp + employee_imp) / 2 if employee_imp else manager_imp
        
        all_tasks.append({
            'type': 'manager',
            'id': assign.id,
            'name': task.name,
            'estimated_hours': task.estimated_hours or 4,
            'remaining_hours': task.estimated_hours or 4,
            'deadline': task.deadline,
            'importance': combined_importance,
            'manager_importance': manager_imp,
            'employee_importance': employee_imp
        })
    
    # 2. 自主任务
    self_tasks_query = SelfTask.query.filter_by(employee_id=employee_id, status='pending').all()
    
    for task in self_tasks_query:
        all_tasks.append({
            'type': 'self',
            'id': task.id,
            'name': task.name,
            'estimated_hours': task.estimated_hours or 4,
            'remaining_hours': task.estimated_hours or 4,
            'deadline': task.deadline,
            'importance': task.importance or 5,
            'manager_importance': None,
            'employee_importance': task.importance or 5
        })
    
    # 记录每个任务上一次被排程的日期（用于连续性计算）
    last_scheduled_date = {}
    
    def calculate_priority(task, current_date, task_key):
        """
        优先级计算（基于权重配置）
        - 紧急度：基于截止日期
        - 重要度：基于任务重要性
        - 连续性：优先排昨天正在进行的任务
        """
        urgency_score = 0
        importance_score = 0
        continuity_score = 0
        
        # 1. 紧急度得分（0-100）
        if task['deadline']:
            try:
                deadline_str = task['deadline'].split('T')[0] if 'T' in task['deadline'] else task['deadline']
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                current = datetime.strptime(current_date, '%Y-%m-%d')
                days_until = (deadline - current).days
                
                if days_until < 0:
                    urgency_score = 100  # 已逾期
                elif days_until == 0:
                    urgency_score = 95
                elif days_until <= 2:
                    urgency_score = 85
                elif days_until <= 5:
                    urgency_score = 70
                elif days_until <= 7:
                    urgency_score = 55
                elif days_until <= 14:
                    urgency_score = 40
                else:
                    urgency_score = max(10, 30 - days_until)
            except:
                urgency_score = 30
        else:
            urgency_score = 20
        
        # 2. 重要度得分（0-100）
        importance_score = (task['importance'] or 5) * 10
        
        # 3. 连续性得分（0-100）
        last_date = last_scheduled_date.get(task_key)
        if last_date:
            try:
                last = datetime.strptime(last_date, '%Y-%m-%d')
                curr = datetime.strptime(current_date, '%Y-%m-%d')
                days_gap = (curr - last).days
                if days_gap == 1:  # 昨天正在做
                    continuity_score = 100
                elif days_gap == 2:
                    continuity_score = 70
                elif days_gap <= 3:
                    continuity_score = 50
                else:
                    continuity_score = 20
            except:
                continuity_score = 0
        else:
            continuity_score = 0
        
        # 加权计算总分
        total_score = (
            urgency_score * urgency_weight / 100 +
            importance_score * importance_weight / 100 +
            continuity_score * continuity_weight / 100
        )
        
        return total_score, urgency_score, importance_score, continuity_score
    
    # 删除旧的日程
    old_schedules = Schedule.query.filter_by(employee_id=employee_id).all()
    for old in old_schedules:
        db.session.delete(old)
    
    # 创建新日程
    schedule = Schedule(
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        daily_hours=daily_hours
    )
    db.session.add(schedule)
    db.session.flush()
    
    # 分配任务到每天
    schedule_items = []
    tasks_scheduled = {}  # 累计已排时间
    task_daily_progress = {}  # 每个任务每天的累计进度
    
    for date in work_dates:
        available_hours = daily_available[date]
        if available_hours <= 0:
            continue
        
        pending_tasks = []
        for task in all_tasks:
            task_key = f"{task['type']}_{task['id']}"
            scheduled_hours = tasks_scheduled.get(task_key, 0)
            remaining = task['remaining_hours'] - scheduled_hours
            
            if remaining > 0:
                priority, urg, imp, cont = calculate_priority(task, date, task_key)
                pending_tasks.append({
                    **task,
                    'task_key': task_key,
                    'scheduled_hours': scheduled_hours,
                    'current_remaining': remaining,
                    'priority': priority,
                    'urgency_score': urg,
                    'importance_score': imp,
                    'continuity_score': cont
                })
        
        pending_tasks.sort(key=lambda x: x['priority'], reverse=True)
        
        day_remaining = available_hours
        for task in pending_tasks:
            if day_remaining <= 0:
                break
            
            hours_to_assign = min(task['current_remaining'], day_remaining)
            if hours_to_assign > 0:
                task_key = task['task_key']
                new_scheduled = tasks_scheduled.get(task_key, 0) + hours_to_assign
                progress = min(100, round(new_scheduled / task['estimated_hours'] * 100, 1))
                
                item = ScheduleItem(
                    schedule_id=schedule.id,
                    date=date,
                    task_type=task['type'],
                    task_id=task['id'],
                    task_name=task['name'],
                    planned_hours=round(hours_to_assign, 2),
                    priority_score=round(task['priority'], 2),
                    deadline=task['deadline']
                )
                db.session.add(item)
                schedule_items.append({
                    'item': item,
                    'progress': progress,
                    'total_hours': task['estimated_hours'],
                    'scheduled_hours': round(new_scheduled, 2)
                })
                
                tasks_scheduled[task_key] = new_scheduled
                last_scheduled_date[task_key] = date
                
                # 记录每日进度
                if task_key not in task_daily_progress:
                    task_daily_progress[task_key] = {}
                task_daily_progress[task_key][date] = progress
                
                day_remaining -= hours_to_assign
    
    db.session.commit()
    
    # 计算延期风险
    delay_risks = []
    for task in all_tasks:
        task_key = f"{task['type']}_{task['id']}"
        scheduled = tasks_scheduled.get(task_key, 0)
        remaining = task['remaining_hours'] - scheduled
        
        risk_level = None
        risk_reason = None
        
        if task['deadline']:
            try:
                deadline_str = task['deadline'].split('T')[0] if 'T' in task['deadline'] else task['deadline']
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                today_dt = datetime.now()
                days_until = (deadline - today_dt).days
                
                if remaining > 0.1:  # 任务未排完
                    if days_until < 0:
                        risk_level = 'overdue'
                        risk_reason = f'已逾期{-days_until}天，剩余{round(remaining, 1)}h未排'
                    elif scheduled == 0:
                        risk_level = 'high'
                        risk_reason = f'任务未被排程，距截止{days_until}天'
                    else:
                        risk_level = 'medium'
                        risk_reason = f'剩余{round(remaining, 1)}h未排入日程'
                elif days_until < 0:
                    risk_level = 'overdue'
                    risk_reason = f'已逾期{-days_until}天'
                elif days_until <= 1 and scheduled < task['estimated_hours'] * 0.8:
                    risk_level = 'high'
                    risk_reason = f'明天截止，仅完成{round(scheduled/task["estimated_hours"]*100)}%'
            except:
                pass
        elif remaining > 0.1:
            risk_level = 'low'
            risk_reason = f'剩余{round(remaining, 1)}h未排入日程'
        
        if risk_level:
            delay_risks.append({
                'name': task['name'],
                'type': task['type'],
                'typeLabel': '经理任务' if task['type'] == 'manager' else '自主任务',
                'deadline': task['deadline'],
                'estimated_hours': task['estimated_hours'],
                'scheduled_hours': round(scheduled, 2),
                'remaining_hours': round(remaining, 2),
                'progress': round(scheduled / task['estimated_hours'] * 100, 1) if task['estimated_hours'] > 0 else 0,
                'risk_level': risk_level,
                'risk_reason': risk_reason
            })
    
    # 按风险级别排序
    risk_order = {'overdue': 0, 'high': 1, 'medium': 2, 'low': 3}
    delay_risks.sort(key=lambda x: risk_order.get(x['risk_level'], 99))
    
    return jsonify({
        'success': True,
        'message': f'成功生成 {len(work_dates)} 天的日程安排',
        'schedule': {
            'id': schedule.id,
            'employeeId': schedule.employee_id,
            'startDate': schedule.start_date,
            'endDate': schedule.end_date,
            'dailyHours': schedule.daily_hours
        },
        'weights': {
            'urgency': urgency_weight,
            'importance': importance_weight,
            'continuity': continuity_weight
        },
        'summary': {
            'total_tasks': len(all_tasks),
            'scheduled_items': len(schedule_items),
            'work_days': len(work_dates)
        },
        'delay_risks': delay_risks,
        'daily_unavailable': daily_unavailable
    })


@app.route('/api/schedule/<int:employee_id>', methods=['GET'])
def get_schedule(employee_id):
    """获取员工的日程（包含不可用时间、任务进度、延期风险）"""
    schedule = Schedule.query.filter_by(employee_id=employee_id).order_by(Schedule.created_at.desc()).first()
    
    if not schedule:
        return jsonify({
            'success': False,
            'message': '暂无日程，请先生成',
            'schedule': None
        })
    
    # 获取不可用时间
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date >= schedule.start_date,
        UnavailableTime.date <= schedule.end_date
    ).all()
    
    # 构建每日不可用时间映射
    daily_unavailable = {}
    for ut in unavailable_times:
        if ut.date not in daily_unavailable:
            daily_unavailable[ut.date] = []
        try:
            start_parts = ut.start_time.split(':')
            end_parts = ut.end_time.split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            hours = (end_minutes - start_minutes) / 60
            daily_unavailable[ut.date].append({
                'id': ut.id,
                'reason': ut.get_reason_type_label(),
                'note': ut.note,
                'startTime': ut.start_time,
                'endTime': ut.end_time,
                'hours': round(hours, 2)
            })
        except:
            pass
    
    # 收集所有任务信息用于计算进度
    task_info = {}  # task_key -> {estimated_hours, deadline, name}
    
    # 经理任务
    assignments = Assignment.query.filter_by(employee_id=employee_id).filter(
        Assignment.status.in_(['pending', 'accepted'])
    ).all()
    for assign in assignments:
        task = Task.query.get(assign.task_id)
        if task:
            task_info[f"manager_{assign.id}"] = {
                'estimated_hours': task.estimated_hours or 4,
                'deadline': task.deadline,
                'name': task.name
            }
    
    # 自主任务
    self_tasks = SelfTask.query.filter_by(employee_id=employee_id, status='pending').all()
    for task in self_tasks:
        task_info[f"self_{task.id}"] = {
            'estimated_hours': task.estimated_hours or 4,
            'deadline': task.deadline,
            'name': task.name
        }
    
    # 按日期分组并计算累计进度
    items_by_date = {}
    cumulative_hours = {}  # 每个任务的累计工时
    
    for item in sorted(schedule.items, key=lambda x: (x.date, x.id)):
        task_key = f"{item.task_type}_{item.task_id}"
        
        # 累计工时
        cumulative_hours[task_key] = cumulative_hours.get(task_key, 0) + item.planned_hours
        
        # 计算进度
        total_hours = task_info.get(task_key, {}).get('estimated_hours', item.planned_hours)
        progress = min(100, round(cumulative_hours[task_key] / total_hours * 100, 1)) if total_hours > 0 else 100
        
        item_dict = item.to_dict()
        item_dict['progress'] = progress
        item_dict['cumulativeHours'] = round(cumulative_hours[task_key], 2)
        item_dict['totalHours'] = total_hours
        
        if item.date not in items_by_date:
            items_by_date[item.date] = []
        items_by_date[item.date].append(item_dict)
    
    # 获取日程范围内所有工作日
    all_dates = set(items_by_date.keys())
    all_dates.update(daily_unavailable.keys())  # 添加有不可用时间的日期
    
    # 添加日程范围内的所有工作日
    start_dt = datetime.strptime(schedule.start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(schedule.end_date, '%Y-%m-%d')
    current_dt = start_dt
    while current_dt <= end_dt:
        if current_dt.weekday() < 5:  # 工作日
            all_dates.add(current_dt.strftime('%Y-%m-%d'))
        current_dt += timedelta(days=1)
    
    # 构建每日日程
    sorted_dates = sorted(all_dates)
    daily_schedule = []
    for date in sorted_dates:
        items = items_by_date.get(date, [])
        unavailable = daily_unavailable.get(date, [])
        task_hours = sum(item['plannedHours'] for item in items)
        unavail_hours = sum(u['hours'] for u in unavailable)
        
        # 只有当有任务或不可用时间时才添加到日程
        if items or unavailable:
            daily_schedule.append({
                'date': date,
                'dayLabel': get_day_label(date),
                'taskHours': round(task_hours, 2),
                'unavailableHours': round(unavail_hours, 2),
                'totalHours': round(task_hours + unavail_hours, 2),
                'items': items,
                'unavailable': unavailable
            })
    
    # 计算延期风险
    delay_risks = []
    for task_key, info in task_info.items():
        scheduled = cumulative_hours.get(task_key, 0)
        remaining = info['estimated_hours'] - scheduled
        
        risk_level = None
        risk_reason = None
        
        if info['deadline']:
            try:
                deadline_str = info['deadline'].split('T')[0] if 'T' in info['deadline'] else info['deadline']
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                today_dt = datetime.now()
                days_until = (deadline - today_dt).days
                
                if remaining > 0.1:
                    if days_until < 0:
                        risk_level = 'overdue'
                        risk_reason = f'已逾期{-days_until}天，剩余{round(remaining, 1)}h未排'
                    elif scheduled == 0:
                        risk_level = 'high'
                        risk_reason = f'任务未被排程，距截止{days_until}天'
                    else:
                        risk_level = 'medium'
                        risk_reason = f'剩余{round(remaining, 1)}h未排入日程'
                elif days_until < 0:
                    risk_level = 'overdue'
                    risk_reason = f'已逾期{-days_until}天'
            except:
                pass
        elif remaining > 0.1:
            risk_level = 'low'
            risk_reason = f'剩余{round(remaining, 1)}h未排入日程'
        
        if risk_level:
            task_type = task_key.split('_')[0]
            delay_risks.append({
                'name': info['name'],
                'type': task_type,
                'typeLabel': '经理任务' if task_type == 'manager' else '自主任务',
                'deadline': info['deadline'],
                'estimated_hours': info['estimated_hours'],
                'scheduled_hours': round(scheduled, 2),
                'remaining_hours': round(remaining, 2),
                'progress': round(scheduled / info['estimated_hours'] * 100, 1) if info['estimated_hours'] > 0 else 0,
                'risk_level': risk_level,
                'risk_reason': risk_reason
            })
    
    risk_order = {'overdue': 0, 'high': 1, 'medium': 2, 'low': 3}
    delay_risks.sort(key=lambda x: risk_order.get(x['risk_level'], 99))
    
    # 计算延期率统计
    total_tasks = len(task_info)
    overdue_tasks = [r for r in delay_risks if r['risk_level'] == 'overdue']
    high_risk_tasks = [r for r in delay_risks if r['risk_level'] == 'high']
    
    # 计算总延期时间
    total_delay_hours = sum(r['remaining_hours'] for r in delay_risks if r['risk_level'] in ['overdue', 'high', 'medium'])
    
    # 计算延期天数（对于已逾期的任务）
    delay_days_info = []
    for r in overdue_tasks:
        if r['deadline']:
            try:
                deadline_str = r['deadline'].split('T')[0] if 'T' in r['deadline'] else r['deadline']
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                days_overdue = (datetime.now() - deadline).days
                delay_days_info.append({
                    'name': r['name'],
                    'days': days_overdue,
                    'hours': r['remaining_hours']
                })
            except:
                pass
    
    delay_statistics = {
        'total_tasks': total_tasks,
        'delayed_tasks': len(overdue_tasks),
        'high_risk_tasks': len(high_risk_tasks),
        'delay_rate': round(len(overdue_tasks) / total_tasks * 100, 1) if total_tasks > 0 else 0,
        'risk_rate': round((len(overdue_tasks) + len(high_risk_tasks)) / total_tasks * 100, 1) if total_tasks > 0 else 0,
        'total_delay_hours': round(total_delay_hours, 1),
        'delay_days_info': delay_days_info
    }
    
    return jsonify({
        'success': True,
        'schedule': {
            'id': schedule.id,
            'employeeId': schedule.employee_id,
            'startDate': schedule.start_date,
            'endDate': schedule.end_date,
            'dailyHours': schedule.daily_hours,
            'isAccepted': schedule.is_accepted,
            'acceptedAt': schedule.accepted_at.isoformat() if schedule.accepted_at else None,
            'createdAt': schedule.created_at.isoformat() if schedule.created_at else None
        },
        'dailySchedule': daily_schedule,
        'delay_risks': delay_risks,
        'delay_statistics': delay_statistics
    })


def get_day_label(date_str):
    """获取日期的中文标签"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return f"{date.month}月{date.day}日 {weekdays[date.weekday()]}"
    except:
        return date_str


@app.route('/api/schedule/<int:schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """删除日程"""
    schedule = Schedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    return '', 204


@app.route('/api/schedule/<int:schedule_id>/accept', methods=['POST'])
def accept_schedule(schedule_id):
    """接受日程"""
    schedule = Schedule.query.get_or_404(schedule_id)
    schedule.is_accepted = True
    schedule.accepted_at = datetime.now()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '日程已接受',
        'schedule': schedule.to_dict()
    })


@app.route('/api/schedule/<int:schedule_id>/lock-items', methods=['POST'])
def lock_schedule_items(schedule_id):
    """锁定/解锁日程项"""
    data = request.json
    item_ids = data.get('item_ids', [])
    locked = data.get('locked', True)
    
    schedule = Schedule.query.get_or_404(schedule_id)
    
    # 更新锁定状态
    for item in schedule.items:
        if item.id in item_ids:
            item.is_locked = locked
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已{"锁定" if locked else "解锁"} {len(item_ids)} 个日程项'
    })


@app.route('/api/schedule/update', methods=['POST'])
def update_schedule_with_locks():
    """更新排程（保留锁定的日程项）"""
    data = request.json
    employee_id = data.get('employee_id')
    days = data.get('days', 14)
    daily_hours = data.get('daily_hours', 8)
    urgency_weight = data.get('urgency_weight', 40)
    importance_weight = data.get('importance_weight', 40)
    continuity_weight = data.get('continuity_weight', 20)
    locked_items = data.get('locked_items', [])  # [{date, task_type, task_id, planned_hours}, ...]
    
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    
    # 获取所有任务（经理分配的 + 自主任务）
    assignments = Assignment.query.filter(
        Assignment.employee_id == employee_id,
        Assignment.status.in_(['accepted', 'pending'])
    ).all()
    
    self_tasks = SelfTask.query.filter(
        SelfTask.employee_id == employee_id,
        SelfTask.status == 'pending'
    ).all()
    
    # 获取不可用时间
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date >= today,
        UnavailableTime.date <= end_date
    ).all()
    
    # 构建每日不可用时间映射
    daily_unavailable = {}
    for ut in unavailable_times:
        if ut.date not in daily_unavailable:
            daily_unavailable[ut.date] = 0
        try:
            start_parts = ut.start_time.split(':')
            end_parts = ut.end_time.split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            hours = (end_minutes - start_minutes) / 60
            daily_unavailable[ut.date] += hours
        except:
            pass
    
    # 构建锁定项映射 (date -> [(task_type, task_id, hours), ...])
    locked_by_date = {}
    locked_task_hours = {}  # 记录每个任务已锁定的工时
    for item in locked_items:
        date = item['date']
        task_key = f"{item['task_type']}_{item['task_id']}"
        if date not in locked_by_date:
            locked_by_date[date] = []
        locked_by_date[date].append({
            'task_type': item['task_type'],
            'task_id': item['task_id'],
            'task_name': item.get('task_name', ''),
            'planned_hours': item['planned_hours'],
            'deadline': item.get('deadline')
        })
        locked_task_hours[task_key] = locked_task_hours.get(task_key, 0) + item['planned_hours']
    
    # 构建任务列表（排除已完成的工时）
    all_tasks = []
    
    for assign in assignments:
        task = assign.task
        if not task:
            continue
        
        task_key = f"manager_{assign.id}"
        estimated = task.estimated_hours or 8
        already_locked = locked_task_hours.get(task_key, 0)
        remaining = estimated - already_locked
        
        if remaining > 0.1:
            manager_imp = task.importance or 5
            emp_imp = assign.employee_importance or manager_imp
            combined_imp = (manager_imp + emp_imp) / 2
            
            # 计算紧急度
            urgency = 5
            if task.deadline:
                try:
                    deadline_str = task.deadline.split('T')[0] if 'T' in task.deadline else task.deadline
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                    days_until = (deadline - datetime.now()).days
                    if days_until <= 0:
                        urgency = 10
                    elif days_until <= 3:
                        urgency = 8
                    elif days_until <= 7:
                        urgency = 6
                    else:
                        urgency = 4
                except:
                    pass
            
            priority_score = (urgency * urgency_weight + combined_imp * importance_weight) / (urgency_weight + importance_weight)
            
            all_tasks.append({
                'type': 'manager',
                'id': assign.id,
                'name': task.name,
                'remaining_hours': remaining,
                'deadline': task.deadline,
                'priority_score': priority_score,
                'urgency': urgency,
                'importance': combined_imp
            })
    
    for st in self_tasks:
        task_key = f"self_{st.id}"
        estimated = st.estimated_hours or 4
        already_locked = locked_task_hours.get(task_key, 0)
        remaining = estimated - already_locked
        
        if remaining > 0.1:
            urgency = 5
            if st.deadline:
                try:
                    deadline_str = st.deadline.split('T')[0] if 'T' in st.deadline else st.deadline
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                    days_until = (deadline - datetime.now()).days
                    if days_until <= 0:
                        urgency = 10
                    elif days_until <= 3:
                        urgency = 8
                    elif days_until <= 7:
                        urgency = 6
                    else:
                        urgency = 4
                except:
                    pass
            
            importance = st.importance or 5
            priority_score = (urgency * urgency_weight + importance * importance_weight) / (urgency_weight + importance_weight)
            
            all_tasks.append({
                'type': 'self',
                'id': st.id,
                'name': st.name,
                'remaining_hours': remaining,
                'deadline': st.deadline,
                'priority_score': priority_score,
                'urgency': urgency,
                'importance': importance
            })
    
    # 按优先级排序
    all_tasks.sort(key=lambda x: -x['priority_score'])
    
    # 获取工作日列表
    workdays = []
    current_date = datetime.now()
    while len(workdays) < days:
        if current_date.weekday() < 5:
            workdays.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # 计算每天的可用工时（扣除不可用时间和锁定项）
    daily_available = {}
    for date in workdays:
        unavail = daily_unavailable.get(date, 0)
        locked_hours = sum(item['planned_hours'] for item in locked_by_date.get(date, []))
        daily_available[date] = max(0, daily_hours - unavail - locked_hours)
    
    # 排程
    schedule_items = []
    task_remaining = {f"{t['type']}_{t['id']}": t['remaining_hours'] for t in all_tasks}
    task_info = {f"{t['type']}_{t['id']}": t for t in all_tasks}
    
    # 添加锁定的日程项
    for date, items in locked_by_date.items():
        for item in items:
            schedule_items.append({
                'date': date,
                'task_type': item['task_type'],
                'task_id': item['task_id'],
                'task_name': item['task_name'],
                'planned_hours': item['planned_hours'],
                'priority_score': 0,
                'deadline': item.get('deadline'),
                'is_locked': True
            })
    
    # 为剩余任务分配工时
    for task in all_tasks:
        task_key = f"{task['type']}_{task['id']}"
        remaining = task_remaining[task_key]
        
        for date in workdays:
            if remaining <= 0.1:
                break
            
            available = daily_available[date]
            if available <= 0:
                continue
            
            # 分配工时（考虑连续性）
            allocate = min(remaining, available, 4)  # 单任务单日最多4小时
            
            if allocate > 0.1:
                schedule_items.append({
                    'date': date,
                    'task_type': task['type'],
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'planned_hours': round(allocate, 2),
                    'priority_score': task['priority_score'],
                    'deadline': task['deadline'],
                    'is_locked': False
                })
                
                daily_available[date] -= allocate
                remaining -= allocate
                task_remaining[task_key] = remaining
    
    # 删除旧的日程
    old_schedules = Schedule.query.filter_by(employee_id=employee_id).all()
    for old in old_schedules:
        db.session.delete(old)
    
    # 创建新日程
    schedule = Schedule(
        employee_id=employee_id,
        start_date=today,
        end_date=end_date,
        daily_hours=daily_hours,
        is_accepted=False
    )
    db.session.add(schedule)
    db.session.flush()
    
    # 创建日程项
    for item in schedule_items:
        si = ScheduleItem(
            schedule_id=schedule.id,
            date=item['date'],
            task_type=item['task_type'],
            task_id=item['task_id'],
            task_name=item['task_name'],
            planned_hours=item['planned_hours'],
            priority_score=item['priority_score'],
            deadline=item['deadline'],
            is_locked=item.get('is_locked', False)
        )
        db.session.add(si)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '排程已更新',
        'schedule': schedule.to_dict()
    })


@app.route('/api/schedule/check-updates/<int:employee_id>', methods=['GET'])
def check_schedule_updates(employee_id):
    """检查是否有新任务或不可用时间需要更新排程"""
    # 查找最新的日程（不限于已接受的）
    schedule = Schedule.query.filter_by(employee_id=employee_id).order_by(Schedule.created_at.desc()).first()
    
    if not schedule:
        return jsonify({
            'needsUpdate': False,
            'reason': '没有日程'
        })
    
    # 用日程的创建时间作为基准（如果已接受则用接受时间）
    base_time = schedule.accepted_at if schedule.is_accepted and schedule.accepted_at else schedule.created_at
    
    # 检查是否有新的任务
    new_assignments = Assignment.query.filter(
        Assignment.employee_id == employee_id,
        Assignment.status.in_(['accepted', 'pending']),
        Assignment.assigned_at > base_time
    ).count()
    
    new_self_tasks = SelfTask.query.filter(
        SelfTask.employee_id == employee_id,
        SelfTask.status == 'pending',
        SelfTask.created_at > base_time
    ).count()
    
    new_unavailable = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.created_at > base_time
    ).count()
    
    needs_update = new_assignments > 0 or new_self_tasks > 0 or new_unavailable > 0
    
    reasons = []
    if new_assignments > 0:
        reasons.append(f'{new_assignments}个新经理任务')
    if new_self_tasks > 0:
        reasons.append(f'{new_self_tasks}个新自主任务')
    if new_unavailable > 0:
        reasons.append(f'{new_unavailable}个新不可用时间')
    
    return jsonify({
        'needsUpdate': needs_update,
        'reason': '、'.join(reasons) if reasons else '无更新',
        'scheduleId': schedule.id,
        'acceptedAt': schedule.accepted_at.isoformat() if schedule.accepted_at else None
    })


# ==================== 工作会话管理 ====================

@app.route('/api/work-sessions/today/<int:employee_id>', methods=['GET'])
def get_today_work_sessions(employee_id):
    """获取今日及未来两天的任务工作会话"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 计算未来两天（只算工作日）
    future_dates = [today]
    current_date = datetime.now()
    days_added = 0
    while days_added < 2:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5:  # 工作日
            future_dates.append(current_date.strftime('%Y-%m-%d'))
            days_added += 1
    
    # 获取员工已接受的日程
    schedule = Schedule.query.filter_by(employee_id=employee_id, is_accepted=True).order_by(Schedule.created_at.desc()).first()
    
    if not schedule:
        # 检查是否有未接受的日程
        pending_schedule = Schedule.query.filter_by(employee_id=employee_id).order_by(Schedule.created_at.desc()).first()
        if pending_schedule:
            return jsonify({
                'success': False,
                'message': '请先在日程制定模块接受排程',
                'today': today,
                'dates': future_dates,
                'todayTasks': [],
                'futureTasks': [],
                'hasPendingSchedule': True
            })
        else:
            return jsonify({
                'success': False,
                'message': '请先在日程制定模块生成排程',
                'today': today,
                'dates': future_dates,
                'todayTasks': [],
                'futureTasks': [],
                'hasPendingSchedule': False
            })
    
    # 获取这些日期的日程项
    schedule_items = ScheduleItem.query.filter(
        ScheduleItem.schedule_id == schedule.id,
        ScheduleItem.date.in_(future_dates)
    ).all()
    
    # 获取已有的工作会话
    existing_sessions = WorkSession.query.filter(
        WorkSession.employee_id == employee_id,
        WorkSession.date.in_(future_dates)
    ).all()
    
    # 建立已有会话的映射 (task_type_task_id_date -> session)
    session_map = {}
    for session in existing_sessions:
        key = f"{session.task_type}_{session.task_id}_{session.date}"
        session_map[key] = session
    
    # 构建今日任务和未来任务
    today_tasks = []
    future_tasks = []
    
    for item in schedule_items:
        key = f"{item.task_type}_{item.task_id}_{item.date}"
        
        # 判断是否是今天应该完成的任务（今天是最后一天有这个任务的日期）
        is_today_only = True
        if item.deadline:
            try:
                deadline_str = item.deadline.split('T')[0] if 'T' in item.deadline else item.deadline
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                today_date = datetime.now().date()
                is_today_only = (deadline_date <= today_date)
            except:
                pass
        
        # 检查这个任务在后续日期是否还有排程
        future_items = ScheduleItem.query.filter(
            ScheduleItem.schedule_id == schedule.id,
            ScheduleItem.task_type == item.task_type,
            ScheduleItem.task_id == item.task_id,
            ScheduleItem.date > item.date
        ).first()
        if future_items:
            is_today_only = False
        
        if key in session_map:
            # 使用已有的会话
            task_data = session_map[key].to_dict()
            task_data['scheduleItemId'] = item.id
        else:
            # 创建新的会话数据（尚未保存到数据库）
            task_data = {
                'id': None,
                'employeeId': employee_id,
                'scheduleItemId': item.id,
                'taskType': item.task_type,
                'taskTypeLabel': '经理任务' if item.task_type == 'manager' else '自主任务',
                'taskId': item.task_id,
                'taskName': item.task_name,
                'date': item.date,
                'plannedHours': item.planned_hours,
                'plannedSeconds': int(item.planned_hours * 3600),
                'status': 'pending',
                'statusLabel': '待开始',
                'startedAt': None,
                'completedAt': None,
                'totalWorkedSeconds': 0,
                'workedHours': 0,
                'isTodayOnly': is_today_only,
                'deadline': item.deadline,
                'overtimeStatus': None,
                'interruptions': []
            }
        
        if item.date == today:
            today_tasks.append(task_data)
        else:
            future_tasks.append(task_data)
    
    # 获取今日不可用时间
    unavailable_times = UnavailableTime.query.filter(
        UnavailableTime.employee_id == employee_id,
        UnavailableTime.date == today
    ).all()
    
    # 检查是否有新任务需要更新排程
    needs_update = False
    update_reason = ''
    if schedule and schedule.accepted_at:
        new_assignments = Assignment.query.filter(
            Assignment.employee_id == employee_id,
            Assignment.status.in_(['accepted', 'pending']),
            Assignment.assigned_at > schedule.accepted_at
        ).count()
        
        new_self_tasks = SelfTask.query.filter(
            SelfTask.employee_id == employee_id,
            SelfTask.status == 'pending',
            SelfTask.created_at > schedule.accepted_at
        ).count()
        
        new_unavailable = UnavailableTime.query.filter(
            UnavailableTime.employee_id == employee_id,
            UnavailableTime.created_at > schedule.accepted_at
        ).count()
        
        if new_assignments > 0 or new_self_tasks > 0 or new_unavailable > 0:
            needs_update = True
            reasons = []
            if new_assignments > 0:
                reasons.append(f'{new_assignments}个新任务')
            if new_self_tasks > 0:
                reasons.append(f'{new_self_tasks}个新自主任务')
            if new_unavailable > 0:
                reasons.append(f'{new_unavailable}个新不可用时间')
            update_reason = '、'.join(reasons)
    
    return jsonify({
        'success': True,
        'today': today,
        'dates': future_dates,
        'todayTasks': today_tasks,
        'futureTasks': future_tasks,
        'unavailableTimes': [ut.to_dict() for ut in unavailable_times],
        'needsScheduleUpdate': needs_update,
        'updateReason': update_reason
    })


@app.route('/api/work-sessions/start', methods=['POST'])
def start_work_session():
    """开始工作会话"""
    data = request.json
    
    employee_id = data.get('employee_id')
    schedule_item_id = data.get('schedule_item_id')
    task_type = data.get('task_type')
    task_id = data.get('task_id')
    task_name = data.get('task_name')
    date = data.get('date')
    planned_hours = data.get('planned_hours')
    is_today_only = data.get('is_today_only', False)
    deadline = data.get('deadline')
    
    # 检查是否已有未完成的工作会话
    existing = WorkSession.query.filter(
        WorkSession.employee_id == employee_id,
        WorkSession.date == date,
        WorkSession.task_type == task_type,
        WorkSession.task_id == task_id,
        WorkSession.status.in_(['working', 'paused'])
    ).first()
    
    if existing:
        # 如果已有会话，更新为工作中状态
        if existing.status == 'paused':
            existing.status = 'working'
            db.session.commit()
            return jsonify({
                'success': True,
                'message': '已恢复工作',
                'session': existing.to_dict()
            })
        return jsonify({
            'success': False,
            'message': '任务已在进行中',
            'session': existing.to_dict()
        })
    
    # 检查是否有其他正在进行的工作
    other_working = WorkSession.query.filter(
        WorkSession.employee_id == employee_id,
        WorkSession.status == 'working'
    ).first()
    
    if other_working:
        return jsonify({
            'success': False,
            'message': f'请先完成或暂停当前任务：{other_working.task_name}',
            'currentSession': other_working.to_dict()
        })
    
    # 检查是否已有待开始的会话
    pending_session = WorkSession.query.filter(
        WorkSession.employee_id == employee_id,
        WorkSession.date == date,
        WorkSession.task_type == task_type,
        WorkSession.task_id == task_id,
        WorkSession.status == 'pending'
    ).first()
    
    if pending_session:
        # 更新为工作中
        pending_session.status = 'working'
        pending_session.started_at = datetime.now()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '开始工作',
            'session': pending_session.to_dict()
        })
    
    # 创建新的工作会话
    session = WorkSession(
        employee_id=employee_id,
        schedule_item_id=schedule_item_id,
        task_type=task_type,
        task_id=task_id,
        task_name=task_name,
        date=date,
        planned_hours=planned_hours,
        status='working',
        started_at=datetime.now(),
        is_today_only=is_today_only,
        deadline=deadline
    )
    
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '开始工作',
        'session': session.to_dict()
    })


@app.route('/api/work-sessions/<int:session_id>/pause', methods=['POST'])
def pause_work_session(session_id):
    """暂停/中断工作会话"""
    data = request.json
    reason = data.get('reason', '').strip()
    
    if not reason:
        return jsonify({
            'success': False,
            'message': '请填写中断原因'
        }), 400
    
    session = WorkSession.query.get(session_id)
    if not session:
        return jsonify({
            'success': False,
            'message': '工作会话不存在'
        }), 404
    
    if session.status != 'working':
        return jsonify({
            'success': False,
            'message': '只能暂停进行中的任务'
        })
    
    # 计算已工作时间
    if session.started_at:
        # 计算本次工作时长
        now = datetime.now()
        last_resume = session.started_at
        
        # 找最后一次恢复时间
        last_interruption = WorkInterruption.query.filter(
            WorkInterruption.work_session_id == session_id,
            WorkInterruption.resumed_at.isnot(None)
        ).order_by(WorkInterruption.resumed_at.desc()).first()
        
        if last_interruption:
            last_resume = last_interruption.resumed_at
        
        worked_seconds = int((now - last_resume).total_seconds())
        session.total_worked_seconds += worked_seconds
    
    # 创建中断记录
    interruption = WorkInterruption(
        work_session_id=session_id,
        paused_at=datetime.now(),
        reason=reason
    )
    db.session.add(interruption)
    
    session.status = 'paused'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '已暂停',
        'session': session.to_dict()
    })


@app.route('/api/work-sessions/<int:session_id>/resume', methods=['POST'])
def resume_work_session(session_id):
    """恢复工作会话"""
    session = WorkSession.query.get(session_id)
    if not session:
        return jsonify({
            'success': False,
            'message': '工作会话不存在'
        }), 404
    
    if session.status != 'paused':
        return jsonify({
            'success': False,
            'message': '只能恢复已暂停的任务'
        })
    
    # 检查是否有其他正在进行的工作
    other_working = WorkSession.query.filter(
        WorkSession.employee_id == session.employee_id,
        WorkSession.status == 'working',
        WorkSession.id != session_id
    ).first()
    
    if other_working:
        return jsonify({
            'success': False,
            'message': f'请先完成或暂停当前任务：{other_working.task_name}',
            'currentSession': other_working.to_dict()
        })
    
    # 更新最后一次中断记录的恢复时间
    last_interruption = WorkInterruption.query.filter(
        WorkInterruption.work_session_id == session_id,
        WorkInterruption.resumed_at.is_(None)
    ).order_by(WorkInterruption.paused_at.desc()).first()
    
    if last_interruption:
        now = datetime.now()
        last_interruption.resumed_at = now
        last_interruption.duration_seconds = int((now - last_interruption.paused_at).total_seconds())
    
    session.status = 'working'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '已恢复工作',
        'session': session.to_dict()
    })


@app.route('/api/work-sessions/<int:session_id>/complete', methods=['POST'])
def complete_work_session(session_id):
    """完成工作会话"""
    session = WorkSession.query.get(session_id)
    if not session:
        return jsonify({
            'success': False,
            'message': '工作会话不存在'
        }), 404
    
    if session.status == 'completed':
        return jsonify({
            'success': False,
            'message': '任务已完成'
        })
    
    now = datetime.now()
    
    # 如果是工作中状态，计算最后一段工作时间
    if session.status == 'working' and session.started_at:
        last_resume = session.started_at
        
        # 找最后一次恢复时间
        last_interruption = WorkInterruption.query.filter(
            WorkInterruption.work_session_id == session_id,
            WorkInterruption.resumed_at.isnot(None)
        ).order_by(WorkInterruption.resumed_at.desc()).first()
        
        if last_interruption:
            last_resume = last_interruption.resumed_at
        
        worked_seconds = int((now - last_resume).total_seconds())
        session.total_worked_seconds += worked_seconds
    
    session.status = 'completed'
    session.completed_at = now
    db.session.commit()
    
    # 计算完成统计
    worked_hours = session.total_worked_seconds / 3600
    planned_hours = session.planned_hours
    efficiency = round(planned_hours / worked_hours * 100, 1) if worked_hours > 0 else 100
    
    return jsonify({
        'success': True,
        'message': '任务已完成',
        'session': session.to_dict(),
        'statistics': {
            'plannedHours': planned_hours,
            'workedHours': round(worked_hours, 2),
            'efficiency': efficiency,
            'interruptions': len(session.interruptions),
            'totalInterruptionMinutes': sum(i.duration_seconds for i in session.interruptions) / 60
        }
    })


@app.route('/api/work-sessions/<int:session_id>/update-time', methods=['POST'])
def update_work_session_time(session_id):
    """更新工作会话的实时工作时间（前端定时调用）"""
    data = request.json
    additional_seconds = data.get('additional_seconds', 0)
    
    session = WorkSession.query.get(session_id)
    if not session:
        return jsonify({'success': False, 'message': '会话不存在'}), 404
    
    if session.status != 'working':
        return jsonify({'success': False, 'message': '任务未在进行中'})
    
    # 累加工作时间
    session.total_worked_seconds += additional_seconds
    db.session.commit()
    
    return jsonify({
        'success': True,
        'session': session.to_dict()
    })


@app.route('/api/work-sessions/history/<int:employee_id>', methods=['GET'])
def get_work_session_history(employee_id):
    """获取员工的工作历史记录"""
    date = request.args.get('date')
    status = request.args.get('status')
    
    query = WorkSession.query.filter(WorkSession.employee_id == employee_id)
    
    if date:
        query = query.filter(WorkSession.date == date)
    if status:
        query = query.filter(WorkSession.status == status)
    
    sessions = query.order_by(WorkSession.date.desc(), WorkSession.created_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'sessions': [s.to_dict() for s in sessions]
    })


# ==================== 健康检查 ====================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'service': '任务分配系统',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected'
    })


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '资源未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)

