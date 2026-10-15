"""为打包的exe初始化数据库"""
import os
import sys
import sqlite3

# 项目根目录与打包目录（按本机实际布局调整；默认基于本脚本所在位置推算）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PACKAGED_DIR = os.path.join(PROJECT_ROOT, 'dist', '库存管理系统')

# 切换到打包目录
os.chdir(PACKAGED_DIR)

# 添加项目路径
sys.path.insert(0, PROJECT_ROOT)

print("开始初始化数据库...")
print(f"目标路径: {os.getcwd()}")

# 删除旧数据库
if os.path.exists('database.db'):
    os.remove('database.db')
    print("✓ 已删除旧数据库")

# 使用init_db初始化
from database.init_db import init_db
init_db()

# 验证
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
conn.close()

print(f"\n✓ 数据库初始化完成!")
print(f"创建的表 ({len(tables)} 个):")
for table in tables:
    print(f"  - {table[0]}")

# 检查文件大小
size = os.path.getsize('database.db')
print(f"\n数据库文件大小: {size / 1024:.1f} KB")

if size > 0:
    print("\n✅ 数据库初始化成功!现在可以运行exe了。")
else:
    print("\n❌ 数据库文件为空,初始化失败!")
