import json
import os
import sys
from pathlib import Path

# 导入resource_path工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.resource_path import get_app_data_path

# 配置文件路径 - 使用exe所在目录
CONFIG_FILE = Path(get_app_data_path('erp_settings.json'))

DEFAULT_SETTINGS = {
    # 服务器配置 - 扁平格式
    'server_address': '192.168.1.3:8001',
    'operator_name': '666',
    'auto_connect': True,
    'remember_window_size': True,
    'default_warning_level': 96,
    'warning_enabled': True,
    'notification_enabled': True,
    
    # 数据库配置
    'database': {
        'filename': 'database.db'
    },
    
    # 列宽设置
    'column_widths': {
        'product_view': {
            'parent_sku': 150,
            'sku': 200,
            'option': 200,
            'price': 100
        },
        'inventory_view': {
            'sku': 200,
            'stock': 80,
            'warning': 80,
            'status': 100
        }
    },
    
    # 表格样式
    'table_style': {
        'show_grid': True,
        'alternate_colors': True,
        'row_height': 30
    },
    
    # 导航顺序
    'navigation_order': [
        'dashboard',
        'products',
        'inventory',
        'transit',
        'sales',
        'inventory_logs',
        'settings'
    ]
}

def load_settings():
    """加载用户设置
    
    Returns:
        dict: 合并了默认值的设置字典
        
    这个函数会：
    1. 尝试从配置文件加载设置
    2. 递归合并默认设置，确保所有设置项都存在且格式正确
    3. 保留用户配置中的额外配置节（如 server, database 等）
    4. 如果配置文件不存在或损坏，返回默认设置
    """
    import copy
    
    def deep_merge(base, updates):
        """深度合并字典，保留两边的所有键"""
        result = copy.deepcopy(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 两边都是字典，递归合并
                result[key] = deep_merge(result[key], value)
            else:
                # 使用用户的值
                result[key] = copy.deepcopy(value)
        return result
    
    if not CONFIG_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    
    if not os.access(CONFIG_FILE, os.R_OK):
        print(f'无法读取配置文件: {CONFIG_FILE}')
        return DEFAULT_SETTINGS.copy()
        
    try:
        # 尝试加载用户配置
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_settings = json.load(f)
            
        # 以默认设置为基础，合并用户设置（保留用户的额外配置）
        settings = deep_merge(DEFAULT_SETTINGS, user_settings)
            
        return settings
        
    except json.JSONDecodeError as e:
        print(f'配置文件格式错误: {e}')
        return DEFAULT_SETTINGS.copy()
    except Exception as e:
        print(f'加载设置失败: {e}')
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """保存用户设置
    
    Args:
        settings: 要保存的设置字典
        
    Returns:
        bool: 是否保存成功
        
    这个函数会：
    1. 确保配置目录存在并可写
    2. 备份现有配置（如果存在）
    3. 安全地写入新配置，并确保文件被正确刷新到磁盘
    4. 在出错时回滚到备份
    """
    try:
        # 确保配置目录存在并可写
        config_dir = CONFIG_FILE.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(config_dir, os.W_OK):
            raise PermissionError(f'无法写入配置目录: {config_dir}')
        
        # 如果存在旧配置，创建备份
        backup_file = None
        if CONFIG_FILE.exists():
            if not os.access(CONFIG_FILE, os.W_OK):
                raise PermissionError(f'无法写入配置文件: {CONFIG_FILE}')
            backup_file = CONFIG_FILE.with_suffix('.json.bak')
            CONFIG_FILE.rename(backup_file)
            
        # 写入新配置，确保立即刷新到磁盘
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
            f.flush()  # 刷新文件缓冲区
            os.fsync(f.fileno())  # 确保写入磁盘
            
        # 如果成功，删除备份
        if backup_file and backup_file.exists():
            backup_file.unlink()
            
        return True
        
    except Exception as e:
        # 出错时，如果有备份则恢复
        if backup_file and backup_file.exists():
            if CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            backup_file.rename(CONFIG_FILE)
        print(f'保存设置失败: {e}')
        return False

def get_column_width(view_name, column_name):
    """获取列宽设置"""
    settings = load_settings()
    try:
        return settings['column_widths'][view_name][column_name]
    except KeyError:
        return DEFAULT_SETTINGS['column_widths'][view_name][column_name]


def update_column_width(view_name, column_name, width):
    """更新列宽设置"""
    settings = load_settings()
    if 'column_widths' not in settings:
        settings['column_widths'] = {}
    if view_name not in settings['column_widths']:
        settings['column_widths'][view_name] = {}
    
    settings['column_widths'][view_name][column_name] = width
    save_settings(settings)


def update_setting(category, key, value):
    """更新任意设置项"""
    settings = load_settings()
    if category not in settings:
        settings[category] = {}
    settings[category][key] = value
    save_settings(settings)


def get_setting(category, key, default=None):
    """获取设置值"""
    settings = load_settings()
    try:
        return settings[category][key]
    except KeyError:
        if default is not None:
            return default
        return DEFAULT_SETTINGS[category][key]
