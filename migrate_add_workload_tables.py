#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建员工负载相关表（自主任务、不可用时间）
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行迁移"""
    print(f"开始迁移数据库: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("❌ 数据库文件不存在")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 创建 self_tasks 表（员工自主任务）
        print("\n创建 self_tasks 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS self_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                estimated_hours REAL NOT NULL,
                deadline VARCHAR(50),
                task_type VARCHAR(50) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        ''')
        print("✅ self_tasks 表创建成功")
        
        # 创建 unavailable_times 表（不可用时间）
        print("\n创建 unavailable_times 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unavailable_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                date VARCHAR(20) NOT NULL,
                start_time VARCHAR(10) NOT NULL,
                end_time VARCHAR(10) NOT NULL,
                reason_type VARCHAR(50) NOT NULL,
                note TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        ''')
        print("✅ unavailable_times 表创建成功")
        
        # 创建索引以提高查询性能
        print("\n创建索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_self_tasks_employee ON self_tasks(employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_self_tasks_deadline ON self_tasks(deadline)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_unavailable_times_employee ON unavailable_times(employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_unavailable_times_date ON unavailable_times(date)')
        print("✅ 索引创建成功")
        
        conn.commit()
        print("\n✅ 迁移完成！")
        
        # 验证表结构
        print("\n验证表结构：")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('self_tasks', 'unavailable_times')")
        tables = cursor.fetchall()
        print(f"创建的表: {[t[0] for t in tables]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

