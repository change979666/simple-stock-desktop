"""
安全移除 config.ini 工具

此工具用于：
1. 备份 config.ini 到 config.ini.removed
2. 删除 config.ini
3. 确保系统完全使用 erp_settings.json

使用前请确保：
- 已运行 migrate_config.py 迁移配置
- erp_settings.json 包含所有必要配置
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import shutil
from utils.resource_path import get_app_data_path


def remove_config_ini():
    """安全移除 config.ini"""
    
    config_ini_path = Path(get_app_data_path('config.ini'))
    
    print("=" * 60)
    print("config.ini 移除工具")
    print("=" * 60)
    
    # 检查文件是否存在
    if not config_ini_path.exists():
        print("\n✅ config.ini 不存在，无需移除")
        return
    
    print(f"\n📁 找到 config.ini: {config_ini_path}")
    
    # 备份文件
    backup_path = config_ini_path.with_suffix('.ini.removed')
    print(f"\n📦 备份到: {backup_path}")
    
    try:
        shutil.copy2(config_ini_path, backup_path)
        print("   ✅ 备份成功")
    except Exception as e:
        print(f"   ❌ 备份失败: {e}")
        return
    
    # 删除原文件
    print(f"\n🗑️  删除 config.ini")
    try:
        config_ini_path.unlink()
        print("   ✅ 删除成功")
    except Exception as e:
        print(f"   ❌ 删除失败: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✅ config.ini 已成功移除！")
    print("=" * 60)
    print("\n📝 说明：")
    print("1. config.ini 已备份为 config.ini.removed")
    print("2. 系统现在完全使用 erp_settings.json")
    print("3. 如需恢复，可将 .removed 文件重命名为 .ini")
    print("\n⚠️  注意：")
    print("- 请重启客户端和服务端以应用更改")
    print("- 确保 erp_settings.json 包含所有必要配置")
    

def verify_erp_settings():
    """验证 erp_settings.json 是否包含必要配置"""
    
    import json
    
    settings_path = Path(get_app_data_path('erp_settings.json'))
    
    print("\n" + "=" * 60)
    print("验证 erp_settings.json")
    print("=" * 60)
    
    if not settings_path.exists():
        print("\n❌ erp_settings.json 不存在！")
        print("   请先运行 migrate_config.py 迁移配置")
        return False
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        # 检查必要的配置项
        required_configs = {
            'user_info': ['nickname', 'ip_address', 'role'],
            'inventory': ['default_warning_level', 'warning_enabled']
        }
        
        all_ok = True
        for section, keys in required_configs.items():
            if section not in settings:
                print(f"\n❌ 缺少配置节: {section}")
                all_ok = False
                continue
            
            for key in keys:
                if key in settings[section]:
                    value = settings[section][key]
                    print(f"✅ {section}.{key} = {value}")
                else:
                    print(f"⚠️  {section}.{key} 未设置（将使用默认值）")
        
        return all_ok
        
    except Exception as e:
        print(f"\n❌ 读取 erp_settings.json 失败: {e}")
        return False


if __name__ == '__main__':
    print("\n🚀 开始移除 config.ini\n")
    
    # 先验证 erp_settings.json
    if not verify_erp_settings():
        print("\n⚠️  警告：erp_settings.json 配置不完整")
        response = input("\n是否仍要继续移除 config.ini? (y/N): ")
        if response.lower() != 'y':
            print("\n❌ 操作已取消")
            exit(0)
    
    # 执行移除
    remove_config_ini()
