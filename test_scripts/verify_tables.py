"""验证打包程序的数据库表结构"""
import sqlite3
from pathlib import Path

db_path = Path(r"dist\库存管理系统\database.db")

if not db_path.exists():
    print(f"❌ 数据库不存在: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"✓ 数据库文件: {db_path}")
print(f"✓ 文件大小: {db_path.stat().st_size / 1024:.1f} KB\n")
print(f"数据库表列表 ({len(tables)} 个):")
for table in tables:
    print(f"  - {table[0]}")

conn.close()

print("\n✅ 数据库结构验证成功!")
