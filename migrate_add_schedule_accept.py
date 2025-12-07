#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加日程接受和锁定字段
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 添加 schedules 表的字段
        cursor.execute("PRAGMA table_info(schedules)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        if 'is_accepted' not in existing_columns:
            cursor.execute('ALTER TABLE schedules ADD COLUMN is_accepted BOOLEAN DEFAULT 0')
            print("✅ schedules 表添加字段 is_accepted 成功")
        else:
            print("⏭️  schedules 表字段 is_accepted 已存在，跳过")
        
        if 'accepted_at' not in existing_columns:
            cursor.execute('ALTER TABLE schedules ADD COLUMN accepted_at DATETIME')
            print("✅ schedules 表添加字段 accepted_at 成功")
        else:
            print("⏭️  schedules 表字段 accepted_at 已存在，跳过")
        
        # 添加 schedule_items 表的字段
        cursor.execute("PRAGMA table_info(schedule_items)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        if 'is_locked' not in existing_columns:
            cursor.execute('ALTER TABLE schedule_items ADD COLUMN is_locked BOOLEAN DEFAULT 0')
            print("✅ schedule_items 表添加字段 is_locked 成功")
        else:
            print("⏭️  schedule_items 表字段 is_locked 已存在，跳过")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

