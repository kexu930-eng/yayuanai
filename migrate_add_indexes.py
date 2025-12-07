#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加索引优化查询性能
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def add_indexes():
    """添加索引"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 定义需要添加的索引
    indexes = [
        # 员工表索引
        ('idx_employees_dingtalk_id', 'employees', 'dingtalk_id'),
        ('idx_employees_manager_dingtalk_id', 'employees', 'manager_dingtalk_id'),
        
        # 技能表索引
        ('idx_skills_manager_dingtalk_id', 'skills', 'manager_dingtalk_id'),
        
        # 任务分配表索引
        ('idx_assignments_task_id', 'assignments', 'task_id'),
        ('idx_assignments_employee_id', 'assignments', 'employee_id'),
        ('idx_assignments_assigned_by', 'assignments', 'assigned_by_dingtalk_id'),
        ('idx_assignments_status', 'assignments', 'status'),
        
        # 任务技能关联表索引
        ('idx_task_skills_task_id', 'task_skills', 'task_id'),
        ('idx_task_skills_skill_id', 'task_skills', 'skill_id'),
        
        # 员工技能关联表索引
        ('idx_employee_skills_employee_id', 'employee_skills', 'employee_id'),
        ('idx_employee_skills_skill_id', 'employee_skills', 'skill_id'),
        
        # 自主任务表索引
        ('idx_self_tasks_employee_id', 'self_tasks', 'employee_id'),
        ('idx_self_tasks_status', 'self_tasks', 'status'),
        
        # 不可用时间表索引
        ('idx_unavailable_times_employee_id', 'unavailable_times', 'employee_id'),
        ('idx_unavailable_times_date', 'unavailable_times', 'date'),
    ]
    
    print("=" * 60)
    print("🔧 开始添加数据库索引...")
    print("=" * 60)
    
    success_count = 0
    skip_count = 0
    
    for index_name, table_name, column_name in indexes:
        try:
            # 检查索引是否已存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
            if cursor.fetchone():
                print(f"⏭️  索引已存在，跳过: {index_name}")
                skip_count += 1
                continue
            
            # 创建索引
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            cursor.execute(sql)
            print(f"✅ 创建索引成功: {index_name} ON {table_name}({column_name})")
            success_count += 1
        except Exception as e:
            print(f"❌ 创建索引失败 {index_name}: {str(e)}")
    
    conn.commit()
    conn.close()
    
    print("=" * 60)
    print(f"✅ 索引迁移完成!")
    print(f"   新增索引: {success_count} 个")
    print(f"   跳过已存在: {skip_count} 个")
    print("=" * 60)

def optimize_database():
    """优化数据库（执行VACUUM和ANALYZE）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n🔧 优化数据库...")
    
    try:
        # 分析表统计信息，帮助查询优化器
        cursor.execute("ANALYZE")
        print("✅ ANALYZE 执行成功")
        
        # 整理数据库文件，回收空间
        cursor.execute("VACUUM")
        print("✅ VACUUM 执行成功")
        
    except Exception as e:
        print(f"❌ 数据库优化失败: {str(e)}")
    
    conn.close()
    print("✅ 数据库优化完成!\n")

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("📊 任务分配系统 - 数据库索引迁移脚本")
    print("=" * 60 + "\n")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        exit(1)
    
    add_indexes()
    optimize_database()
    
    print("🎉 所有操作完成!")

