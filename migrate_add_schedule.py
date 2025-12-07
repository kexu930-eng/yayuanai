#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加日程制定功能相关字段和表
1. Assignment表添加 employee_importance 字段
2. SelfTask表添加 importance 字段
3. 新增 schedules 表
4. 新增 schedule_items 表
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task_distribution.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("开始迁移数据库...")
    
    # 1. 给 assignments 表添加 employee_importance 字段
    try:
        cursor.execute("ALTER TABLE assignments ADD COLUMN employee_importance INTEGER")
        print("✅ 已添加 assignments.employee_importance 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ assignments.employee_importance 字段已存在")
        else:
            raise e
    
    # 2. 给 self_tasks 表添加 importance 字段
    try:
        cursor.execute("ALTER TABLE self_tasks ADD COLUMN importance INTEGER DEFAULT 5")
        print("✅ 已添加 self_tasks.importance 字段")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ self_tasks.importance 字段已存在")
        else:
            raise e
    
    # 3. 创建 schedules 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            start_date VARCHAR(20) NOT NULL,
            end_date VARCHAR(20) NOT NULL,
            daily_hours FLOAT DEFAULT 8,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    """)
    print("✅ 已创建 schedules 表")
    
    # 4. 创建 schedule_items 表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            date VARCHAR(20) NOT NULL,
            task_type VARCHAR(20) NOT NULL,
            task_id INTEGER NOT NULL,
            task_name VARCHAR(200) NOT NULL,
            planned_hours FLOAT NOT NULL,
            priority_score FLOAT,
            deadline VARCHAR(50),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
        )
    """)
    print("✅ 已创建 schedule_items 表")
    
    # 5. 创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedules_employee_id ON schedules(employee_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_schedule_id ON schedule_items(schedule_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_items_date ON schedule_items(date)")
        print("✅ 已创建索引")
    except Exception as e:
        print(f"ℹ️ 创建索引时出错: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ 数据库迁移完成！")

if __name__ == '__main__':
    migrate()

