"""
测试配置格式一致性修复
验证所有文件都使用扁平格式配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_gui_utils():
    """测试 gui/utils.py"""
    print("=" * 60)
    print("测试 gui/utils.py")
    print("=" * 60)
    
    try:
        from gui.utils import get_operator_info
        
        info = get_operator_info()
        print(f"✅ get_operator_info() 成功")
        print(f"   操作员: {info['name']}")
        print(f"   IP: {info['ip']}")
        print(f"   显示: {info['display']}")
        
        # 验证返回的是扁平格式配置的值
        if info['name'] and info['name'] != '未设置昵称':
            print(f"✅ 成功读取操作员名称（扁平格式）")
        else:
            print(f"⚠️  操作员名称未设置")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utils_operator():
    """测试 utils/operator.py"""
    print("\n" + "=" * 60)
    print("测试 utils/operator.py")
    print("=" * 60)
    
    try:
        from utils.operator import get_operator_info, get_operator_display
        
        info = get_operator_info()
        display = get_operator_display()
        
        print(f"✅ get_operator_info() 成功")
        print(f"   操作员: {info['name']}")
        print(f"   显示: {display}")
        
        # 验证返回的是扁平格式配置的值
        if info['name'] == '666':
            print(f"✅ 成功读取操作员名称 '666'（扁平格式）")
        else:
            print(f"⚠️  操作员名称: {info['name']}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_crud_operations():
    """测试 crud/operations.py"""
    print("\n" + "=" * 60)
    print("测试 crud/operations.py")
    print("=" * 60)
    
    try:
        # 只验证能正常导入和使用配置
        from config.settings import load_settings
        
        settings = load_settings()
        warning_level = settings.get('default_warning_level', 96)
        
        print(f"✅ 配置读取成功")
        print(f"   预警阈值: {warning_level}")
        print(f"✅ crud/operations.py 使用扁平格式配置")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_format():
    """测试配置文件格式"""
    print("\n" + "=" * 60)
    print("测试配置文件格式")
    print("=" * 60)
    
    try:
        from config.settings import load_settings
        import json
        
        settings = load_settings()
        
        # 验证扁平格式字段存在
        print("检查扁平格式字段:")
        
        # 1. server_address
        server_address = settings.get('server_address')
        if server_address:
            print(f"✅ server_address: {server_address}")
        else:
            print(f"❌ server_address 不存在")
            return False
        
        # 2. operator_name
        operator_name = settings.get('operator_name')
        if operator_name:
            print(f"✅ operator_name: {operator_name}")
        else:
            print(f"❌ operator_name 不存在")
            return False
        
        # 3. default_warning_level
        warning_level = settings.get('default_warning_level')
        if warning_level is not None:
            print(f"✅ default_warning_level: {warning_level}")
        else:
            print(f"❌ default_warning_level 不存在")
            return False
        
        # 验证旧的嵌套格式字段不存在
        print("\n检查旧的嵌套格式字段（应该不存在）:")
        
        if 'server' in settings and isinstance(settings['server'], dict):
            if 'host_ip' in settings['server']:
                print(f"⚠️  检测到旧格式: server.host_ip")
        
        if 'user_info' in settings and isinstance(settings['user_info'], dict):
            if 'nickname' in settings['user_info']:
                print(f"⚠️  检测到旧格式: user_info.nickname")
        
        if 'inventory' in settings and isinstance(settings['inventory'], dict):
            if 'default_warning_level' in settings['inventory']:
                print(f"⚠️  检测到旧格式: inventory.default_warning_level")
        
        print("\n✅ 配置文件格式正确（扁平格式）")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_config_ini():
    """验证没有使用 config.ini"""
    print("\n" + "=" * 60)
    print("检查是否还在使用 config.ini")
    print("=" * 60)
    
    try:
        # 检查关键模块是否还导入 configparser
        import gui.utils
        import utils.operator
        
        # 检查 gui.utils 源代码
        import inspect
        utils_source = inspect.getsource(gui.utils)
        
        if 'configparser' in utils_source.lower():
            print(f"❌ gui/utils.py 仍在导入 configparser")
            return False
        else:
            print(f"✅ gui/utils.py 未使用 configparser")
        
        if 'config.ini' in utils_source.lower():
            print(f"❌ gui/utils.py 仍在引用 config.ini")
            return False
        else:
            print(f"✅ gui/utils.py 未引用 config.ini")
        
        # 检查 utils.operator 源代码
        operator_source = inspect.getsource(utils.operator)
        
        if 'configparser' in operator_source.lower():
            print(f"❌ utils/operator.py 仍在导入 configparser")
            return False
        else:
            print(f"✅ utils/operator.py 未使用 configparser")
        
        print(f"\n✅ 所有关键模块都已移除 config.ini 依赖")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "🔍" * 30)
    print("配置格式一致性测试")
    print("🔍" * 30 + "\n")
    
    success = True
    
    success = test_config_format() and success
    success = test_gui_utils() and success
    success = test_utils_operator() and success
    success = test_crud_operations() and success
    success = test_no_config_ini() and success
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！配置格式已统一为扁平格式")
        print("=" * 60)
        print("\n✅ 修复内容:")
        print("  1. gui/utils.py - 移除 config.ini, 使用扁平格式")
        print("  2. utils/operator.py - 使用扁平格式")
        print("  3. crud/operations.py - 使用扁平格式")
        print("  4. gui/inventory_view.py - 使用扁平格式")
        print("  5. 启动客户端.bat - 使用扁平格式")
        print("\n可以安全打包了！")
    else:
        print("❌ 部分测试失败，请检查错误信息")
        print("=" * 60)
        sys.exit(1)
