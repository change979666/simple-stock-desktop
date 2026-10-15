from database.session import SessionLocal
from crud.inventory_logs import get_all_operation_logs
from datetime import datetime
from PyQt6.QtCore import QDate

db = SessionLocal()

# 模拟GUI中的日期选择
start_qdate = QDate(2025, 10, 9)  # 截图中的开始日期
end_qdate = QDate(2025, 10, 16)    # 截图中的结束日期

# 转换为Python datetime（模拟GUI中的代码）
start = datetime.combine(
    start_qdate.toPyDate(),
    datetime.min.time()
)
end = datetime.combine(
    end_qdate.toPyDate(),
    datetime.max.time()
)

print(f"查询日期范围:")
print(f"  开始: {start}")
print(f"  结束: {end}")
print("=" * 60)

logs = get_all_operation_logs(db, start_date=start, end_date=end)

print(f"\n找到 {len(logs)} 条记录")

if len(logs) > 0:
    print("\n前5条记录:")
    for i, log in enumerate(logs[:5], 1):
        print(f"\n{i}. 时间: {log['time']}")
        print(f"   类型: {log['operation_type']}")
        print(f"   操作员: {log['operator']}")
        print(f"   SKU: {log['sku']}")
else:
    print("\n❌ 没有找到记录！")
    print("\n检查数据库中的实际日期范围:")
    from database.models import ActionLog, StockLog
    from sqlalchemy import func
    
    min_action = db.query(func.min(ActionLog.created_at)).scalar()
    max_action = db.query(func.max(ActionLog.created_at)).scalar()
    min_stock = db.query(func.min(StockLog.created_at)).scalar()
    max_stock = db.query(func.max(StockLog.created_at)).scalar()
    
    print(f"  ActionLog: {min_action} 到 {max_action}")
    print(f"  StockLog: {min_stock} 到 {max_stock}")

db.close()
