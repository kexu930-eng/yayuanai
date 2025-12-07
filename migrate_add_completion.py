#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加任务完成情况和评价字段
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 添加 assignments 表的完成情况字段
        columns_to_add_assignments = [
            ('completed_at', 'DATETIME'),
            ('actual_hours', 'FLOAT'),
            ('completion_note', 'TEXT'),
            ('efficiency_rating', 'INTEGER'),
            ('quality_rating', 'INTEGER'),
            ('review_comment', 'TEXT'),
            ('reviewed_at', 'DATETIME')
        ]
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(assignments)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in columns_to_add_assignments:
            if col_name not in existing_columns:
                cursor.execute(f'ALTER TABLE assignments ADD COLUMN {col_name} {col_type}')
                print(f"✅ assignments 表添加字段 {col_name} 成功")
            else:
                print(f"⏭️  assignments 表字段 {col_name} 已存在，跳过")
        
        # 添加 self_tasks 表的完成记录字段
        columns_to_add_self_tasks = [
            ('actual_hours', 'FLOAT'),
            ('completion_note', 'TEXT')
        ]
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(self_tasks)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in columns_to_add_self_tasks:
            if col_name not in existing_columns:
                cursor.execute(f'ALTER TABLE self_tasks ADD COLUMN {col_name} {col_type}')
                print(f"✅ self_tasks 表添加字段 {col_name} 成功")
            else:
                print(f"⏭️  self_tasks 表字段 {col_name} 已存在，跳过")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

