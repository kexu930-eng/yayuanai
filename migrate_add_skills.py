#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加技能相关表
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始数据库迁移 - 添加技能管理功能...")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 创建 skills 表
        print("\n📝 创建 skills 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                manager_dingtalk_id VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ skills 表创建成功")
        
        # 2. 创建 task_skills 表（任务-技能关联表）
        print("\n📝 创建 task_skills 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (skill_id) REFERENCES skills (id)
            )
        """)
        print("✅ task_skills 表创建成功")
        
        # 3. 创建索引以提高查询性能
        print("\n📝 创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_skills_manager 
            ON skills(manager_dingtalk_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_skills_task 
            ON task_skills(task_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_skills_skill 
            ON task_skills(skill_id)
        """)
        print("✅ 索引创建成功")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移完成！")
        print("=" * 60)
        
        # 显示所有表
        print("\n📊 当前数据库表列表:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for table in cursor.fetchall():
            print(f"   - {table[0]}")
        
        # 显示 skills 表结构
        print("\n📊 skills 表结构:")
        cursor.execute("PRAGMA table_info(skills)")
        for col in cursor.fetchall():
            print(f"   - {col[1]}: {col[2]}")
        
        # 显示 task_skills 表结构
        print("\n📊 task_skills 表结构:")
        cursor.execute("PRAGMA table_info(task_skills)")
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

