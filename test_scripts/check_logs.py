"""Check recent action logs"""
from database.session import get_db
from database.models import ActionLog

db = next(get_db())
logs = db.query(ActionLog).order_by(ActionLog.created_at.desc()).limit(10).all()

print("=" * 80)
print("Recent 10 Action Logs")
print("=" * 80)

for i, log in enumerate(logs, 1):
    time_str = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
    operator = repr(log.operator_info)
    action = log.action[:40] if len(log.action) > 40 else log.action
    
    print(f"\n{i}. Time: {time_str}")
    print(f"   Operator: {operator}")
    print(f"   Action: {action}")

print("\n" + "=" * 80)
