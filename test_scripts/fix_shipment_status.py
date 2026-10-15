"""统一发货表中的状态值格式为小写下划线"""
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("=" * 60)
print("统一发货记录状态值格式")
print("=" * 60)

# 状态映射：大写名称 -> 小写值
STATUS_MAPPING = {
    'PENDING': 'pending',
    'IN_TRANSIT': 'in_transit',
    'ARRIVED': 'arrived',
    'SHELVED': 'shelved',
    'CANCELLED': 'cancelled'
}

# 查询当前状态分布
print("\n=== 修复前的状态分布 ===")
cursor.execute("""
    SELECT status, COUNT(*)
    FROM inventory_shipments
    GROUP BY status
""")
for status, count in cursor.fetchall():
    print(f"  {status}: {count} 条")

# 修复每个状态
total_fixed = 0
for old_status, new_status in STATUS_MAPPING.items():
    cursor.execute("""
        SELECT COUNT(*)
        FROM inventory_shipments
        WHERE status = ?
    """, (old_status,))
    
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"\n修复 '{old_status}' -> '{new_status}' ({count}条记录)")
        
        cursor.execute("""
            UPDATE inventory_shipments
            SET status = ?
            WHERE status = ?
        """, (new_status, old_status))
        
        total_fixed += count

# 提交更改
conn.commit()

# 验证结果
print("\n=== 修复后的状态分布 ===")
cursor.execute("""
    SELECT status, COUNT(*)
    FROM inventory_shipments
    GROUP BY status
""")
status_counts = cursor.fetchall()
for status, count in status_counts:
    print(f"  {status}: {count} 条")

# 检查是否有无效值
valid_statuses = list(STATUS_MAPPING.values())
invalid_count = 0
for status, _ in status_counts:
    if status not in valid_statuses:
        print(f"  ⚠️  警告: '{status}' 不是有效的状态值")
        invalid_count += 1

print("\n" + "=" * 60)
if invalid_count == 0:
    print(f"✅ 修复完成! 共修复 {total_fixed} 条记录")
    print("   所有状态值已统一为小写下划线格式")
else:
    print(f"⚠️  修复完成，但有 {invalid_count} 个无效状态值")
print("=" * 60)

conn.close()

