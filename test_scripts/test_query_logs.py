from database.session import SessionLocal
from crud.inventory_logs import get_all_operation_logs
from datetime import datetime, timedelta

db = SessionLocal()

# 查询最近7天的记录
start_date = datetime.now() - timedelta(days=7)
end_date = datetime.now()

print(f"查询范围: {start_date} 到 {end_date}")
print("=" * 60)

logs = get_all_operation_logs(db, start_date=start_date, end_date=end_date)

print(f"找到 {len(logs)} 条记录\n")

for i, log in enumerate(logs[:10], 1):  # 只显示前10条
    print(f"{i}. {log['time']}")
    print(f"   类型: {log['operation_type']}")
    print(f"   操作员: {log['operator']}")
    print(f"   SKU: {log['sku']}")
    print(f"   备注: {log['notes']}")
    print()

db.close()
