#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Task(db.Model):
    """任务表"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.String(50), nullable=True)
    estimated_hours = db.Column(db.Float, nullable=True)  # 预计耗时（小时）
    importance = db.Column(db.Integer, default=5)  # 重要程度（1-10）
    importance_note = db.Column(db.Text, nullable=True)  # 重要度说明
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    assignments = db.relationship('Assignment', backref='task', lazy=True, cascade='all, delete-orphan')
    task_skills = db.relationship('TaskSkill', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        # 获取关联的技能
        skills = [ts.skill.to_dict() for ts in self.task_skills if ts.skill]
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'deadline': self.deadline,
            'estimated_hours': self.estimated_hours,
            'importance': self.importance,
            'importance_note': self.importance_note,
            'skills': skills,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Employee(db.Model):
    """员工表"""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dingtalk_id = db.Column(db.String(100), nullable=False, unique=True, index=True)  # 添加索引
    manager_dingtalk_id = db.Column(db.String(100), nullable=True, index=True)  # 添加索引
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    assignments = db.relationship('Assignment', backref='employee', lazy=True, cascade='all, delete-orphan')
    employee_skills = db.relationship('EmployeeSkill', backref='employee', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        # 获取员工技能
        skills_list = [es.to_dict() for es in self.employee_skills]
        
        return {
            'id': self.id,
            'name': self.name,
            'dingtalk_id': self.dingtalk_id,
            'manager_dingtalk_id': self.manager_dingtalk_id,
            'skills': skills_list,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Assignment(db.Model):
    """任务分配表"""
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    assigned_by_dingtalk_id = db.Column(db.String(100), nullable=True, index=True)
    assigned_by_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)  # pending/accepted/rejected/completed
    reject_reason = db.Column(db.Text, nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.now)
    responded_at = db.Column(db.DateTime, nullable=True)
    notification_sent = db.Column(db.Boolean, default=False)
    notification_error = db.Column(db.Text, nullable=True)
    employee_importance = db.Column(db.Integer, nullable=True)  # 员工评定的重要性（1-10）
    
    # 完成情况字段
    completed_at = db.Column(db.DateTime, nullable=True)  # 完成时间
    actual_hours = db.Column(db.Float, nullable=True)  # 实际用时（小时）
    completion_note = db.Column(db.Text, nullable=True)  # 员工填写的完成情况
    
    # 经理评价字段
    efficiency_rating = db.Column(db.Integer, nullable=True)  # 效率评分（1-10）
    quality_rating = db.Column(db.Integer, nullable=True)  # 质量评分（1-10）
    review_comment = db.Column(db.Text, nullable=True)  # 评审意见
    reviewed_at = db.Column(db.DateTime, nullable=True)  # 评价时间
    
    def to_dict(self):
        return {
            'id': self.id,
            'taskId': self.task_id,
            'taskName': self.task.name if self.task else '',
            'taskDescription': self.task.description if self.task else '',
            'taskDeadline': self.task.deadline if self.task else None,
            'taskEstimatedHours': self.task.estimated_hours if self.task else None,
            'managerImportance': self.task.importance if self.task else 5,  # 经理设定的重要性
            'employeeImportance': self.employee_importance,  # 员工评定的重要性
            'employeeId': self.employee_id,
            'employeeName': self.employee.name if self.employee else '',
            'employeeDingtalkId': self.employee.dingtalk_id if self.employee else '',
            'assignedByDingtalkId': self.assigned_by_dingtalk_id,
            'assignedByName': self.assigned_by_name,
            'status': self.status,
            'rejectReason': self.reject_reason,
            'assignedAt': self.assigned_at.isoformat() if self.assigned_at else None,
            'respondedAt': self.responded_at.isoformat() if self.responded_at else None,
            'notificationSent': self.notification_sent,
            'notificationError': self.notification_error,
            # 完成情况
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'actualHours': self.actual_hours,
            'completionNote': self.completion_note,
            # 经理评价
            'efficiencyRating': self.efficiency_rating,
            'qualityRating': self.quality_rating,
            'reviewComment': self.review_comment,
            'reviewedAt': self.reviewed_at.isoformat() if self.reviewed_at else None
        }


class Skill(db.Model):
    """技能表"""
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager_dingtalk_id = db.Column(db.String(100), nullable=True, index=True)  # 所属管理员的钉钉ID，添加索引
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系 - 添加级联删除
    task_skills = db.relationship('TaskSkill', backref='skill', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'manager_dingtalk_id': self.manager_dingtalk_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TaskSkill(db.Model):
    """任务-技能关联表（多对多）"""
    __tablename__ = 'task_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)  # 添加索引
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False, index=True)  # 添加索引
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'skill_id': self.skill_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class EmployeeSkill(db.Model):
    """员工-技能关联表（包含评分）"""
    __tablename__ = 'employee_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)  # 添加索引
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False, index=True)  # 添加索引和级联删除
    rating = db.Column(db.Integer, default=5)  # 评分 1-10
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系 - passive_deletes允许数据库级别的级联删除
    skill = db.relationship('Skill', backref=db.backref('employee_skills_rel', passive_deletes=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'skill_id': self.skill_id,
            'skill_name': self.skill.name if self.skill else '',
            'rating': self.rating,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SelfTask(db.Model):
    """员工自主任务表"""
    __tablename__ = 'self_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # 任务名称
    estimated_hours = db.Column(db.Float, nullable=False)  # 预计耗时（小时）
    deadline = db.Column(db.String(50), nullable=True)  # 截止日期
    task_type = db.Column(db.String(50), nullable=False)  # 任务类型：project/temporary/learning
    description = db.Column(db.Text, nullable=True)  # 任务描述
    importance = db.Column(db.Integer, default=5)  # 重要程度（1-10）
    status = db.Column(db.String(20), default='pending')  # 状态：pending/completed
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 完成记录字段
    actual_hours = db.Column(db.Float, nullable=True)  # 实际用时（小时）
    completion_note = db.Column(db.Text, nullable=True)  # 完成情况记录
    
    # 关系
    employee = db.relationship('Employee', backref=db.backref('self_tasks', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'employeeId': self.employee_id,
            'name': self.name,
            'estimatedHours': self.estimated_hours,
            'deadline': self.deadline,
            'taskType': self.task_type,
            'taskTypeLabel': self.get_task_type_label(),
            'description': self.description,
            'importance': self.importance,
            'status': self.status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'actualHours': self.actual_hours,
            'completionNote': self.completion_note
        }
    
    def get_task_type_label(self):
        """获取任务类型中文标签"""
        type_labels = {
            'project': '项目类任务',
            'temporary': '临时事务',
            'learning': '个人学习/准备'
        }
        return type_labels.get(self.task_type, self.task_type)


class UnavailableTime(db.Model):
    """员工不可用时间表"""
    __tablename__ = 'unavailable_times'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)  # 日期 YYYY-MM-DD
    start_time = db.Column(db.String(10), nullable=False)  # 开始时间 HH:MM
    end_time = db.Column(db.String(10), nullable=False)  # 结束时间 HH:MM
    reason_type = db.Column(db.String(50), nullable=False)  # 类型：meeting/travel/training/leave/other
    note = db.Column(db.Text, nullable=True)  # 备注说明
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    employee = db.relationship('Employee', backref=db.backref('unavailable_times', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        # 计算时长（小时）
        try:
            start_parts = self.start_time.split(':')
            end_parts = self.end_time.split(':')
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            duration_hours = (end_minutes - start_minutes) / 60
        except:
            duration_hours = 0
        
        return {
            'id': self.id,
            'employeeId': self.employee_id,
            'date': self.date,
            'startTime': self.start_time,
            'endTime': self.end_time,
            'durationHours': round(duration_hours, 2),
            'reasonType': self.reason_type,
            'reasonTypeLabel': self.get_reason_type_label(),
            'note': self.note,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_reason_type_label(self):
        """获取不可用原因类型中文标签"""
        type_labels = {
            'meeting': '会议',
            'travel': '出差',
            'training': '培训',
            'leave': '请假',
            'other': '其他'
        }
        return type_labels.get(self.reason_type, self.reason_type)


class Schedule(db.Model):
    """员工日程表（每次生成的排程记录）"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    start_date = db.Column(db.String(20), nullable=False)  # 排程开始日期
    end_date = db.Column(db.String(20), nullable=False)  # 排程结束日期
    daily_hours = db.Column(db.Float, default=8)  # 每日工作时长
    is_accepted = db.Column(db.Boolean, default=False)  # 是否已接受
    accepted_at = db.Column(db.DateTime, nullable=True)  # 接受时间
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    employee = db.relationship('Employee', backref=db.backref('schedules', lazy=True, cascade='all, delete-orphan'))
    items = db.relationship('ScheduleItem', backref='schedule', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'employeeId': self.employee_id,
            'employeeName': self.employee.name if self.employee else '',
            'startDate': self.start_date,
            'endDate': self.end_date,
            'dailyHours': self.daily_hours,
            'isAccepted': self.is_accepted,
            'acceptedAt': self.accepted_at.isoformat() if self.accepted_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items]
        }


class ScheduleItem(db.Model):
    """日程项（每天的任务安排）"""
    __tablename__ = 'schedule_items'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False, index=True)
    date = db.Column(db.String(20), nullable=False)  # 日期
    task_type = db.Column(db.String(20), nullable=False)  # 任务类型：manager/self
    task_id = db.Column(db.Integer, nullable=False)  # 任务ID（assignment_id 或 self_task_id）
    task_name = db.Column(db.String(200), nullable=False)  # 任务名称
    planned_hours = db.Column(db.Float, nullable=False)  # 当天计划工时
    priority_score = db.Column(db.Float, nullable=True)  # 优先级得分
    deadline = db.Column(db.String(50), nullable=True)  # 截止时间
    is_locked = db.Column(db.Boolean, default=False)  # 是否被用户锁定/保留
    
    def to_dict(self):
        return {
            'id': self.id,
            'scheduleId': self.schedule_id,
            'date': self.date,
            'taskType': self.task_type,
            'taskTypeLabel': '经理任务' if self.task_type == 'manager' else '自主任务',
            'taskId': self.task_id,
            'taskName': self.task_name,
            'plannedHours': self.planned_hours,
            'priorityScore': self.priority_score,
            'deadline': self.deadline,
            'isLocked': self.is_locked
        }


class WorkSession(db.Model):
    """工作会话表（记录任务执行时间）"""
    __tablename__ = 'work_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False, index=True)
    schedule_item_id = db.Column(db.Integer, db.ForeignKey('schedule_items.id'), nullable=True)  # 关联日程项
    task_type = db.Column(db.String(20), nullable=False)  # 任务类型：manager/self
    task_id = db.Column(db.Integer, nullable=False)  # 原始任务ID
    task_name = db.Column(db.String(200), nullable=False)  # 任务名称
    date = db.Column(db.String(20), nullable=False, index=True)  # 工作日期
    planned_hours = db.Column(db.Float, nullable=False)  # 今日计划工时
    status = db.Column(db.String(20), default='pending')  # 状态：pending/working/paused/completed
    started_at = db.Column(db.DateTime, nullable=True)  # 开始时间
    completed_at = db.Column(db.DateTime, nullable=True)  # 完成时间
    total_worked_seconds = db.Column(db.Integer, default=0)  # 总工作时间（秒）
    is_today_only = db.Column(db.Boolean, default=False)  # 是否今天应该完成的任务
    deadline = db.Column(db.String(50), nullable=True)  # 截止日期
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关系
    employee = db.relationship('Employee', backref=db.backref('work_sessions', lazy=True, cascade='all, delete-orphan'))
    schedule_item = db.relationship('ScheduleItem', backref=db.backref('work_sessions', lazy=True))
    interruptions = db.relationship('WorkInterruption', backref='work_session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        worked_hours = self.total_worked_seconds / 3600 if self.total_worked_seconds else 0
        planned_seconds = self.planned_hours * 3600
        
        # 计算状态标签
        status_label = {
            'pending': '待开始',
            'working': '进行中',
            'paused': '已暂停',
            'completed': '已完成'
        }.get(self.status, self.status)
        
        # 判断是否超时/加班
        overtime_status = None
        if self.status == 'working' and self.total_worked_seconds > planned_seconds:
            if self.is_today_only:
                overtime_status = 'overtime'  # 已超时
            else:
                overtime_status = 'overwork'  # 正在加班
        
        return {
            'id': self.id,
            'employeeId': self.employee_id,
            'scheduleItemId': self.schedule_item_id,
            'taskType': self.task_type,
            'taskTypeLabel': '经理任务' if self.task_type == 'manager' else '自主任务',
            'taskId': self.task_id,
            'taskName': self.task_name,
            'date': self.date,
            'plannedHours': self.planned_hours,
            'plannedSeconds': int(planned_seconds),
            'status': self.status,
            'statusLabel': status_label,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'totalWorkedSeconds': self.total_worked_seconds,
            'workedHours': round(worked_hours, 2),
            'isTodayOnly': self.is_today_only,
            'deadline': self.deadline,
            'overtimeStatus': overtime_status,
            'interruptions': [i.to_dict() for i in self.interruptions],
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class WorkInterruption(db.Model):
    """工作中断记录表"""
    __tablename__ = 'work_interruptions'
    
    id = db.Column(db.Integer, primary_key=True)
    work_session_id = db.Column(db.Integer, db.ForeignKey('work_sessions.id'), nullable=False, index=True)
    paused_at = db.Column(db.DateTime, nullable=False)  # 暂停时间
    resumed_at = db.Column(db.DateTime, nullable=True)  # 恢复时间
    reason = db.Column(db.Text, nullable=False)  # 中断原因
    duration_seconds = db.Column(db.Integer, default=0)  # 中断时长（秒）
    
    def to_dict(self):
        return {
            'id': self.id,
            'workSessionId': self.work_session_id,
            'pausedAt': self.paused_at.isoformat() if self.paused_at else None,
            'resumedAt': self.resumed_at.isoformat() if self.resumed_at else None,
            'reason': self.reason,
            'durationSeconds': self.duration_seconds,
            'durationMinutes': round(self.duration_seconds / 60, 1) if self.duration_seconds else 0
        }

