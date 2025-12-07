#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加员工技能关联表
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'task_distribution.db')

def migrate():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始数据库迁移 - 添加员工技能关联表...")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 创建 employee_skills 表
        print("\n📝 创建 employee_skills 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                rating INTEGER DEFAULT 5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (skill_id) REFERENCES skills (id)
            )
        """)
        print("✅ employee_skills 表创建成功")
        
        # 创建索引
        print("\n📝 创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_employee_skills_employee 
            ON employee_skills(employee_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_employee_skills_skill 
            ON employee_skills(skill_id)
        """)
        print("✅ 索引创建成功")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ 数据库迁移完成！")
        print("=" * 60)
        
        # 显示表结构
        print("\n📊 employee_skills 表结构:")
        cursor.execute("PRAGMA table_info(employee_skills)")
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

