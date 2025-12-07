#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加工作会话和中断记录表
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 创建工作会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                schedule_item_id INTEGER,
                task_type VARCHAR(20) NOT NULL,
                task_id INTEGER NOT NULL,
                task_name VARCHAR(200) NOT NULL,
                date VARCHAR(20) NOT NULL,
                planned_hours FLOAT NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                started_at DATETIME,
                completed_at DATETIME,
                total_worked_seconds INTEGER DEFAULT 0,
                is_today_only BOOLEAN DEFAULT 0,
                deadline VARCHAR(50),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (schedule_item_id) REFERENCES schedule_items(id)
            )
        ''')
        print("✅ 创建 work_sessions 表成功")
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_sessions_employee_id ON work_sessions(employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_sessions_date ON work_sessions(date)')
        print("✅ 创建 work_sessions 索引成功")
        
        # 创建工作中断记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_interruptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_session_id INTEGER NOT NULL,
                paused_at DATETIME NOT NULL,
                resumed_at DATETIME,
                reason TEXT NOT NULL,
                duration_seconds INTEGER DEFAULT 0,
                FOREIGN KEY (work_session_id) REFERENCES work_sessions(id)
            )
        ''')
        print("✅ 创建 work_interruptions 表成功")
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_interruptions_session_id ON work_interruptions(work_session_id)')
        print("✅ 创建 work_interruptions 索引成功")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

