"""
配置文件验证和修复工具

用于确保 erp_settings.json 包含所有必要的配置项
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.resource_path import get_app_data_path


# 默认配置模板
DEFAULT_CONFIG = {
    "server": {
        "host_ip": "192.168.1.3",
        "port": 8001,
        "auto_connect": True,
        "timeout": 30
    },
    "user_info": {
        "nickname": "未设置昵称",
        "ip_address": "192.168.1.3",
        "role": "操作员"
    },
    "database": {
        "filename": "database.db"
    },
    "inventory": {
        "default_warning_level": 100,
        "warning_enabled": True,
        "notification_enabled": False
    },
    "column_widths": {
        "product_view": {
            "parent_sku": 150,
            "sku": 200,
            "option": 200,
            "price": 100
        },
        "inventory_view": {
            "sku": 200,
            "stock": 80,
            "warning": 80,
            "status": 100
        }
    },
    "table_style": {
        "show_grid": True,
        "alternate_colors": True,
        "row_height": 30
    },
    "navigation_order": [
        "dashboard",
        "products",
        "inventory",
        "transit",
        "sales",
        "inventory_logs",
        "settings"
    ]
}


def merge_config(current, default):
    """递归合并配置，保留现有值，补充缺失的默认值"""
    result = current.copy()
    
    for key, default_value in default.items():
        if key not in result:
            # 缺失的键，使用默认值
            result[key] = default_value
        elif isinstance(default_value, dict) and isinstance(result[key], dict):
            # 两边都是字典，递归合并
            result[key] = merge_config(result[key], default_value)
    
    return result


def verify_and_fix_config():
    """验证并修复配置文件"""
    
    settings_path = Path(get_app_data_path('erp_settings.json'))
    
    print("=" * 60)
    print("配置文件验证和修复工具")
    print("=" * 60)
    
    # 检查文件是否存在
    if not settings_path.exists():
        print(f"\n❌ erp_settings.json 不存在")
        print(f"   路径: {settings_path}")
        print("\n正在创建默认配置文件...")
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 已创建默认配置文件: {settings_path}")
        return
    
    # 读取现有配置
    print(f"\n📖 读取配置文件: {settings_path}")
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
    except Exception as e:
        print(f"\n❌ 读取配置文件失败: {e}")
        print("\n正在创建默认配置文件...")
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 已创建默认配置文件")
        return
    
    # 检查并补充缺失的配置
    print("\n🔍 检查配置完整性...")
    
    missing_keys = []
    
    def check_keys(current, default, path=""):
        for key, default_value in default.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in current:
                missing_keys.append(current_path)
                print(f"  ⚠️  缺少配置: {current_path}")
            elif isinstance(default_value, dict) and isinstance(current.get(key), dict):
                check_keys(current[key], default_value, current_path)
    
    check_keys(current_config, DEFAULT_CONFIG)
    
    if missing_keys:
        print(f"\n发现 {len(missing_keys)} 个缺失的配置项")
        print("\n正在合并默认配置...")
        
        # 合并配置
        merged_config = merge_config(current_config, DEFAULT_CONFIG)
        
        # 保存
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(merged_config, f, ensure_ascii=False, indent=4)
        
        print("✅ 配置已修复并保存")
        
        # 显示补充的配置
        print("\n📝 已补充的配置:")
        for key in missing_keys:
            parts = key.split('.')
            value = merged_config
            for part in parts:
                value = value[part]
            print(f"  ✓ {key} = {value}")
    else:
        print("\n✅ 配置完整，无需修复")
    
    # 显示关键配置
    print("\n" + "=" * 60)
    print("关键配置项")
    print("=" * 60)
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n服务器配置:")
        print(f"  host_ip: {config.get('server', {}).get('host_ip', '未设置')}")
        print(f"  port: {config.get('server', {}).get('port', '未设置')}")
        
        print(f"\n用户信息:")
        print(f"  nickname: {config.get('user_info', {}).get('nickname', '未设置')}")
        print(f"  ip_address: {config.get('user_info', {}).get('ip_address', '未设置')}")
        
        print(f"\n库存配置:")
        print(f"  default_warning_level: {config.get('inventory', {}).get('default_warning_level', '未设置')}")
        print(f"  warning_enabled: {config.get('inventory', {}).get('warning_enabled', '未设置')}")
        
    except Exception as e:
        print(f"\n❌ 读取配置失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 配置验证完成")
    print("=" * 60)


if __name__ == '__main__':
    verify_and_fix_config()
