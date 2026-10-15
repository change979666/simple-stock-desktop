"""Test complete operator info flow""""""完整测试：从UI修改昵称到显示"""

print("=" * 80)import sys

print("Complete Operator Info Test")import configparser

print("=" * 80)from PyQt6.QtWidgets import QApplication

from gui.settings_view import SettingsView

# 1. Test operator modulefrom gui.utils import get_operator_info

print("\n[1] Testing utils.operator module:")

from utils.operator import get_operator_info

info = get_operator_info()def test_complete_flow():

print(f"   Name: {info['name']}")    """测试完整流程：加载 → 修改 → 保存 → 读取"""

print(f"   IP: {info['ip']}")    app = QApplication(sys.argv)

print(f"   Display: {info['display']}")    

    print("=" * 60)

# 2. Test database logging    print("测试完整流程：昵称同步")

print("\n[2] Testing database logging:")    print("=" * 60)

from database.session import get_db    

from crud.operations import create_action_log    # 1. 从设置界面加载当前昵称

    print("\n[步骤1] 从设置界面加载昵称")

db = next(get_db())    view = SettingsView()

log = create_action_log(db, info, "Complete flow test")    current_nickname = view.nickname_input.text()

print(f"   Saved operator_info: {repr(log.operator_info)}")    print(f"  UI显示的昵称: {current_nickname}")

    

# 3. Test parsing    # 2. 检查操作者信息

print("\n[3] Testing operator info parsing:")    print("\n[步骤2] 检查操作者信息函数")

from crud.inventory_logs import parse_operator_info    operator_info = get_operator_info()

parsed = parse_operator_info(log.operator_info)    print(f"  操作者姓名: {operator_info['name']}")

print(f"   Parsed result: {repr(parsed)}")    print(f"  操作者IP: {operator_info['ip']}")

    print(f"  显示文本: {operator_info['display']}")

# 4. Verify in recent logs    

print("\n[4] Recent operation logs:")    # 3. 修改昵称

from crud.inventory_logs import get_all_operation_logs    print("\n[步骤3] 在UI中修改昵称")

logs = get_all_operation_logs(db, limit=3)    new_nickname = "张三测试"

for i, log_item in enumerate(logs, 1):    view.nickname_input.setText(new_nickname)

    print(f"   {i}. {log_item['time'].strftime('%H:%M:%S')} | "    print(f"  设置新昵称: {new_nickname}")

          f"Operator: {log_item['operator']} | "    

          f"Notes: {log_item['notes'][:30]}")    # 4. 保存到配置文件

    print("\n[步骤4] 保存到 config.ini")

print("\n" + "=" * 80)    success = view._save_nickname_to_config(new_nickname)

if parsed == info['name']:    print(f"  保存结果: {'✅ 成功' if success else '❌ 失败'}")

    print("SUCCESS: All tests passed!")    

    print(f"Your operations will show as: {info['name']}")    # 5. 验证配置文件

else:    print("\n[步骤5] 验证 config.ini 内容")

    print(f"FAIL: Expected '{info['name']}', got '{parsed}'")    config = configparser.ConfigParser()

print("=" * 80)    config.read('config.ini', encoding='utf-8')

    saved_nickname = config.get('Server', 'operator_name')
    print(f"  config.ini中的昵称: {saved_nickname}")
    print(f"  是否匹配: {'✅' if saved_nickname == new_nickname else '❌'}")
    
    # 6. 重新加载操作者信息
    print("\n[步骤6] 重新加载操作者信息")
    # 需要重新导入以刷新
    from gui.utils import get_operator_info as get_op_info_fresh
    fresh_info = get_op_info_fresh()
    print(f"  刷新后的姓名: {fresh_info['name']}")
    print(f"  刷新后显示: {fresh_info['display']}")
    print(f"  是否匹配: {'✅' if fresh_info['name'] == new_nickname else '❌'}")
    
    # 7. 恢复原始昵称
    print("\n[步骤7] 恢复原始昵称")
    view._save_nickname_to_config(current_nickname)
    print(f"  已恢复为: {current_nickname}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(test_complete_flow())
