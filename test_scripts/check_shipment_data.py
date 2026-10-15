"""检查数据库中的shipment status值"""
import sqlite3

db_path = r'h:\cursor\ERP开发\simple-stock-desktop\inventory.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 先查看所有表
print("=== 数据库中的所有表 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")

# 查看所有不同的status值
print("\n=== inventory_shipments 表结构 ===")
try:
    cursor.execute("PRAGMA table_info(inventory_shipments)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    print("\n=== 数据库中的 shipment status 值 ===")
    cursor.execute("SELECT DISTINCT status FROM inventory_shipments")
    statuses = cursor.fetchall()
    for status in statuses:
        print(f"  - '{status[0]}'")

    # 查看具体记录
    print("\n=== 前10条记录 ===")
    cursor.execute(
        "SELECT id, batch_number, status FROM inventory_shipments LIMIT 10"
    )
    records = cursor.fetchall()
    for record in records:
        print(f"  ID: {record[0]}, Batch: {record[1]}, Status: '{record[2]}'")

    # 查看transit logs中的status值
    print("\n=== transit_logs 中的 status 值 ===")
    cursor.execute(
        "SELECT DISTINCT old_status, new_status FROM inventory_transit_logs"
    )
    transit_statuses = cursor.fetchall()
    for old_s, new_s in transit_statuses:
        print(f"  old: '{old_s}' -> new: '{new_s}'")
except Exception as e:
    print(f"错误: {e}")

conn.close()
