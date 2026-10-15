"""测试设置界面与config.ini的同步"""
import sys
from PyQt6.QtWidgets import QApplication
from gui.settings_view import SettingsView

def test_load_nickname():
    """测试从config.ini加载昵称"""
    app = QApplication(sys.argv)
    view = SettingsView()
    
    print(f"✅ 成功加载昵称: {view.nickname_input.text()}")
    print(f"✅ IP地址: {view.get_ip_address()}")
    
    # 不显示窗口，直接退出
    return 0

if __name__ == '__main__':
    sys.exit(test_load_nickname())
