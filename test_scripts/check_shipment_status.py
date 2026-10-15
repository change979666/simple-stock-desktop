"""检查发货表中的状态值"""
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=" * 60)
print("发货记录状态检查")
print("=" * 60)

# 查询所有发货记录的状态
cursor.execute("""
    SELECT id, batch_number, status, created_at
    FROM inventory_shipments
    ORDER BY id
""")

rows = cursor.fetchall()
print(f"\n总共 {len(rows)} 条发货记录:\n")

for row in rows:
    print(f"ID: {row[0]:<5} 批次号: {row[1]:<20} 状态: {row[2]:<15} 创建时间: {row[3]}")

# 统计各状态的数量
cursor.execute("""
    SELECT status, COUNT(*)
    FROM inventory_shipments
    GROUP BY status
""")

status_counts = cursor.fetchall()
print("\n" + "=" * 60)
print("状态统计:")
print("=" * 60)
for status, count in status_counts:
    print(f"{status}: {count} 条")

conn.close()
