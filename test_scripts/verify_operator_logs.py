"""验证新操作日志是否显示正确的昵称"""
from database.session import get_db
from crud.operations import create_action_log
from crud.inventory_logs import get_all_operation_logs, parse_operator_info
from utils.operator import get_operator_info
from datetime import datetime

print("=" * 80)
print("验证操作日志显示")
print("=" * 80)

db = next(get_db())

# 1. 获取当前操作员信息
op_info = get_operator_info()
print(f"\n[1] 当前操作员信息:")
print(f"    {op_info}")

# 2. 创建测试日志
test_action = f"测试操作 - {datetime.now().strftime('%H:%M:%S')}"
log = create_action_log(db, op_info, test_action)
print(f"\n[2] 创建测试日志:")
print(f"    保存的 operator_info: {repr(log.operator_info)}")
print(f"    操作: {log.action}")

# 3. 解析显示
parsed = parse_operator_info(log.operator_info)
print(f"\n[3] 解析后的显示:")
print(f"    {repr(parsed)}")

# 4. 获取最近的操作记录
logs = get_all_operation_logs(db, limit=5)
print(f"\n[4] 最近5条操作记录:")
for i, log_item in enumerate(logs, 1):
    print(f"    {i}. {log_item['time'].strftime('%H:%M:%S')} | "
          f"{log_item['operator']} | {log_item['notes'][:30]}")

print("\n" + "=" * 80)
print("✅ 如果看到您的昵称（胡歌），说明已修复成功！")
print("=" * 80)
