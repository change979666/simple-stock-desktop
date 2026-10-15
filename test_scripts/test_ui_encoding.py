"""测试UI中修改昵称的编码问题"""
import sys
import configparser
from PyQt6.QtWidgets import QApplication
from gui.settings_view import SettingsView


def test_ui_save_encoding():
    """测试UI保存中文昵称的编码"""
    app = QApplication(sys.argv)
    view = SettingsView()
    
    print(f"1. 当前加载的昵称: {view.nickname_input.text()}")
    
    # 测试各种中文昵称
    test_names = ["张三", "李四", "王小明", "赵C墨"]
    
    for test_name in test_names:
        print(f"\n测试昵称: {test_name}")
        view.nickname_input.setText(test_name)
        
        # 保存
        success = view._save_nickname_to_config(test_name)
        print(f"  保存结果: {'成功' if success else '失败'}")
        
        # 读取验证
        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')
        saved = config.get('Server', 'operator_name')
        print(f"  读取验证: {saved}")
        print(f"  是否一致: {'✅' if saved == test_name else '❌'}")
        
        # 检查文件编码
        with open('config.ini', 'rb') as f:
            first_bytes = f.read(3)
            has_bom = first_bytes == b'\xef\xbb\xbf'
            print(f"  是否有BOM: {'是' if has_bom else '否'}")
    
    return 0


if __name__ == '__main__':
    sys.exit(test_ui_save_encoding())
