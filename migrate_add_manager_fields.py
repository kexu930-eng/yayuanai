#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加管理员关联字段
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始数据库迁移...")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 检查 employees 表是否已有 manager_dingtalk_id 字段
        cursor.execute("PRAGMA table_info(employees)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'manager_dingtalk_id' not in columns:
            print("\n📝 添加 employees.manager_dingtalk_id 字段...")
            cursor.execute("""
                ALTER TABLE employees 
                ADD COLUMN manager_dingtalk_id VARCHAR(100)
            """)
            print("✅ 字段添加成功")
        else:
            print("\n✓ employees.manager_dingtalk_id 字段已存在")
        
        # 2. 检查 assignments 表是否已有分配人字段
        cursor.execute("PRAGMA table_info(assignments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'assigned_by_dingtalk_id' not in columns:
            print("\n📝 添加 assignments.assigned_by_dingtalk_id 字段...")
            cursor.execute("""
                ALTER TABLE assignments 
                ADD COLUMN assigned_by_dingtalk_id VARCHAR(100)
            """)
            print("✅ 字段添加成功")
        else:
            print("\n✓ assignments.assigned_by_dingtalk_id 字段已存在")
        
        if 'assigned_by_name' not in columns:
            print("\n📝 添加 assignments.assigned_by_name 字段...")
            cursor.execute("""
                ALTER TABLE assignments 
                ADD COLUMN assigned_by_name VARCHAR(100)
            """)
            print("✅ 字段添加成功")
        else:
            print("\n✓ assignments.assigned_by_name 字段已存在")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移完成！")
        print("=" * 60)
        
        # 显示表结构
        print("\n📊 employees 表结构:")
        cursor.execute("PRAGMA table_info(employees)")
        for col in cursor.fetchall():
            print(f"   - {col[1]}: {col[2]}")
        
        print("\n📊 assignments 表结构:")
        cursor.execute("PRAGMA table_info(assignments)")
        for col in cursor.fetchall():
            print(f"   - {col[1]}: {col[2]}")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

