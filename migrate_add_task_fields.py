#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为任务表添加预计耗时、重要程度、重要度说明字段
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
        # 检查 tasks 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        if not cursor.fetchone():
            print("❌ tasks 表不存在")
            return False
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"现有列: {columns}")
        
        # 添加 estimated_hours 列（预计耗时）
        if 'estimated_hours' not in columns:
            print("添加 estimated_hours 列...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN estimated_hours REAL")
            print("✅ estimated_hours 列添加成功")
        else:
            print("⚠️ estimated_hours 列已存在")
        
        # 添加 importance 列（重要程度 1-10）
        if 'importance' not in columns:
            print("添加 importance 列...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN importance INTEGER DEFAULT 5")
            print("✅ importance 列添加成功")
        else:
            print("⚠️ importance 列已存在")
        
        # 添加 importance_note 列（重要度说明）
        if 'importance_note' not in columns:
            print("添加 importance_note 列...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN importance_note TEXT")
            print("✅ importance_note 列添加成功")
        else:
            print("⚠️ importance_note 列已存在")
        
        conn.commit()
        print("\n✅ 迁移完成！")
        
        # 验证
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"迁移后的列: {columns}")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

