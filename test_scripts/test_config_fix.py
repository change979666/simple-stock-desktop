"""
测试配置文件修复
验证新的扁平格式配置能否正确加载
"""
import json
from pathlib import Path

def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("测试配置文件修复")
    print("=" * 60)
    
    # 1. 检查配置文件存在
    config_file = Path("erp_settings.json")
    if not config_file.exists():
        print("❌ 配置文件不存在: erp_settings.json")
        return False
    
    print(f"✅ 配置文件存在: {config_file}")
    
    # 2. 加载配置
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("✅ 配置文件格式正确")
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False
    
    # 3. 验证扁平格式字段
    print("\n配置内容:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 4. 测试server_address解析
    server_address = config.get('server_address', '')
    print(f"\n服务器地址: {server_address}")
    
    if ':' in server_address:
        host, port_str = server_address.split(':', 1)
        try:
            port = int(port_str)
            print(f"  ✅ 主机: {host}")
            print(f"  ✅ 端口: {port}")
        except ValueError:
            print(f"  ❌ 端口格式错误: {port_str}")
            return False
    else:
        print(f"  ❌ 地址格式错误，应为 'IP:端口'")
        return False
    
    # 5. 验证操作员名称
    operator = config.get('operator_name', '')
    print(f"\n操作员: {operator}")
    if operator:
        print(f"  ✅ 操作员名称已设置")
    else:
        print(f"  ⚠️  操作员名称为空")
    
    # 6. 验证其他配置
    print(f"\n其他配置:")
    print(f"  自动连接: {config.get('auto_connect', False)}")
    print(f"  预警等级: {config.get('default_warning_level', 96)}")
    print(f"  预警启用: {config.get('warning_enabled', True)}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


def test_imports():
    """测试导入修复"""
    print("\n\n" + "=" * 60)
    print("测试导入修复")
    print("=" * 60)
    
    try:
        from client.api_client import get_api_client
        print("✅ get_api_client 导入成功")
        
        api_client = get_api_client()
        print(f"✅ API客户端实例获取成功: {type(api_client)}")
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 导入测试通过！")
    print("=" * 60)
    return True


def test_config_system():
    """测试配置系统"""
    print("\n\n" + "=" * 60)
    print("测试配置系统")
    print("=" * 60)
    
    try:
        from config.settings import load_settings
        
        settings = load_settings()
        print("✅ 配置加载成功")
        
        # 验证扁平格式
        server_address = settings.get('server_address', '')
        operator_name = settings.get('operator_name', '')
        warning_level = settings.get('default_warning_level', 0)
        
        print(f"\n读取的配置:")
        print(f"  服务器地址: {server_address}")
        print(f"  操作员名称: {operator_name}")
        print(f"  预警等级: {warning_level}")
        
        if server_address and operator_name:
            print("\n✅ 扁平格式配置正确")
        else:
            print("\n❌ 扁平格式配置不完整")
            return False
        
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ 配置系统测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = True
    
    success = test_config_loading() and success
    success = test_imports() and success
    success = test_config_system() and success
    
    if success:
        print("\n\n" + "🎉" * 30)
        print("所有测试全部通过！可以打包了！")
        print("🎉" * 30)
    else:
        print("\n\n" + "❌" * 30)
        print("有测试失败，请检查错误信息")
        print("❌" * 30)
