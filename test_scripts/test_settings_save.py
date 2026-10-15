"""测试设置界面保存功能"""
import sys
import configparser
from PyQt6.QtWidgets import QApplication
from gui.settings_view import SettingsView


def test_save_nickname():
    """测试保存昵称到config.ini"""
    app = QApplication(sys.argv)
    view = SettingsView()
    
    print(f"当前昵称: {view.nickname_input.text()}")
    
    # 修改昵称
    new_nickname = "测试用户2024"
    view.nickname_input.setText(new_nickname)
    print(f"设置新昵称: {new_nickname}")
    
    # 调用保存方法中的核心逻辑
    success = view._save_nickname_to_config(new_nickname)
    
    if success:
        print("✅ 保存成功")
        
        # 验证是否正确保存
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        saved_nickname = config.get('Server', 'operator_name')
        
        print(f"✅ 验证读取: {saved_nickname}")
        
        if saved_nickname == new_nickname:
            print("✅✅✅ 测试通过：昵称同步成功！")
        else:
            print(f"❌ 测试失败：期望 {new_nickname}，实际 {saved_nickname}")
    else:
        print("❌ 保存失败")
    
    return 0


if __name__ == '__main__':
    sys.exit(test_save_nickname())
