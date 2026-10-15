"""
配置迁移工具
将 config.ini 的配置迁移到 erp_settings.json
"""
import configparser
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.resource_path import get_app_data_path


def migrate_config_ini_to_json():
    """迁移 config.ini 到 erp_settings.json"""
    
    config_ini_path = Path(get_app_data_path('config.ini'))
    settings_json_path = Path(get_app_data_path('erp_settings.json'))
    
    print("=" * 60)
    print("配置迁移工具")
    print("=" * 60)
    
    # 检查 config.ini 是否存在
    if not config_ini_path.exists():
        print("❌ config.ini 不存在，无需迁移")
        return
    
    # 读取 config.ini
    print(f"\n📖 读取 config.ini: {config_ini_path}")
    config = configparser.ConfigParser()
    try:
        config.read(config_ini_path, encoding='utf-8')
    except Exception as e:
        print(f"❌ 读取 config.ini 失败: {e}")
        return
    
    # 读取现有的 erp_settings.json
    print(f"📖 读取 erp_settings.json: {settings_json_path}")
    if settings_json_path.exists():
        try:
            with open(settings_json_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception as e:
            print(f"⚠️  读取 erp_settings.json 失败: {e}，将创建新文件")
            settings = {}
    else:
        settings = {}
    
    # 迁移配置
    print("\n🔄 开始迁移配置...")
    
    # 1. Server 配置
    if 'Server' in config:
        if 'server' not in settings:
            settings['server'] = {}
        
        if config.has_option('Server', 'host_ip'):
            settings['server']['host_ip'] = config.get('Server', 'host_ip')
            print(f"  ✅ server.host_ip = {settings['server']['host_ip']}")
        
        if config.has_option('Server', 'port'):
            settings['server']['port'] = config.getint('Server', 'port')
            print(f"  ✅ server.port = {settings['server']['port']}")
        
        if config.has_option('Server', 'operator_name'):
            operator_name = config.get('Server', 'operator_name')
            if 'user_info' not in settings:
                settings['user_info'] = {}
            settings['user_info']['nickname'] = operator_name
            # 同时设置 IP 地址
            if 'host_ip' in settings['server']:
                settings['user_info']['ip_address'] = settings['server']['host_ip']
            print(f"  ✅ user_info.nickname = {operator_name}")
    
    # 2. Database 配置
    if 'Database' in config:
        if 'database' not in settings:
            settings['database'] = {}
        
        if config.has_option('Database', 'filename'):
            settings['database']['filename'] = config.get('Database', 'filename')
            print(f"  ✅ database.filename = {settings['database']['filename']}")
    
    # 3. Inventory 配置
    if 'Inventory' in config:
        if 'inventory' not in settings:
            settings['inventory'] = {}
        
        if config.has_option('Inventory', 'default_warning_level'):
            warning_level = config.getint('Inventory', 'default_warning_level')
            settings['inventory']['default_warning_level'] = warning_level
            print(f"  ✅ inventory.default_warning_level = {warning_level}")
    
    # 保存到 erp_settings.json
    print(f"\n💾 保存到 erp_settings.json...")
    try:
        with open(settings_json_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        print(f"✅ 配置已成功迁移到: {settings_json_path}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return
    
    # 备份 config.ini
    backup_path = config_ini_path.with_suffix('.ini.backup')
    print(f"\n📦 备份 config.ini 到: {backup_path}")
    try:
        import shutil
        shutil.copy2(config_ini_path, backup_path)
        print("✅ 备份成功")
    except Exception as e:
        print(f"⚠️  备份失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 配置迁移完成！")
    print("=" * 60)
    print("\n📝 下一步操作:")
    print("1. 检查 erp_settings.json 中的配置是否正确")
    print("2. 重启服务端和客户端程序")
    print("3. 如果一切正常，可以删除 config.ini（已备份为 .ini.backup）")
    print()


def verify_migration():
    """验证迁移结果"""
    settings_json_path = Path(get_app_data_path('erp_settings.json'))
    
    print("=" * 60)
    print("验证配置迁移结果")
    print("=" * 60)
    
    if not settings_json_path.exists():
        print("❌ erp_settings.json 不存在")
        return
    
    try:
        with open(settings_json_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        print("\n✅ 配置文件格式正确")
        print("\n📋 当前配置:")
        print(json.dumps(settings, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify_migration()
    else:
        migrate_config_ini_to_json()
