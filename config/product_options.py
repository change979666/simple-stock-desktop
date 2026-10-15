"""产品选项相关配置"""
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

# 导入resource_path工具
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.resource_path import get_app_data_path

# 配置文件路径
CONFIG_FILE = get_app_data_path('product_options.json')

# 默认选项顺序和映射
DEFAULT_OPTIONS = {
    "order": ["颜色", "尺寸"],  # 选项类型的顺序
    "type_options": {  # 每种选项类型下的选项值及其顺序
        "颜色": ["咖色", "驼色", "黑色", "棕色", "白色", "蓝色", "红色"],
        "尺寸": ["S", "M", "L", "XL", "XXL", "F"]
    },
    "mapping": {
        # 颜色映射
        "咖啡": "咖色",
        "咖啡色": "咖色",
        "驼色": "驼色",
        "黑色": "黑色",
        "棕色": "棕色",
        "驼咖": "驼色",
        "蓝": "蓝色",
        "黑": "黑色",
        "白": "白色",
        "红": "红色",
        # 尺寸映射
        "S码": "S",
        "M码": "M",
        "L码": "L",
        "XL码": "XL",
        "XXL码": "XXL",
        "均码": "F",
        "FREE": "F",
        "free": "F"
    }
}


def save_option_settings(settings: Dict) -> None:
    """保存选项设置到配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'保存选项配置失败: {e}')


def load_option_settings() -> Optional[Dict]:
    """从配置文件加载选项设置"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f'读取选项配置失败: {e}')
    return None


def get_option_settings() -> Dict:
    """获取选项设置,如果没有配置文件则返回默认设置"""
    return load_option_settings() or DEFAULT_OPTIONS


def get_option_types() -> List[str]:
    """获取选项类型的顺序列表（如["颜色", "尺寸"]）"""
    settings = get_option_settings()
    return settings['order']


def get_type_options(option_type: str) -> List[str]:
    """获取指定选项类型的选项值列表
    
    Args:
        option_type: 选项类型（如"颜色"或"尺寸"）
        
    Returns:
        该类型下的选项值列表
    """
    settings = get_option_settings()
    return settings['type_options'].get(option_type, [])


def get_option_mapping() -> Dict[str, str]:
    """获取选项名称映射"""
    settings = get_option_settings()
    return settings['mapping']


def standardize_option_name(option_str: str) -> str:
    """标准化选项组合字符串
    
    Args:
        option_str: 原始选项字符串（如"颜色:咖啡, 尺寸:L码"）
        
    Returns:
        标准化后的选项字符串（如"颜色:咖色, 尺寸:L"）
    """
    if not option_str or ':' not in option_str:
        return option_str
        
    mapping = get_option_mapping()
    parts = []
    
    for part in option_str.split(','):
        part = part.strip()
        if ':' not in part:
            parts.append(part)
            continue
            
        option_type, value = [x.strip() for x in part.split(':', 1)]
        value = mapping.get(value, value)
        parts.append(f"{option_type}:{value}")
        
    return ', '.join(parts)


def get_sort_key(option_str: str) -> List[int]:
    """获取选项组合的排序键值列表
    
    Args:
        option_str: 选项组合字符串（如"颜色:咖色, 尺寸:L"）
        
    Returns:
        排序键值列表，每个元素代表该位置选项在其类型中的顺序
        如果某个选项不存在，对应位置使用最大整数表示排在最后
    """
    if not option_str:
        return [float('inf')] * len(get_option_types())
        
    # 解析选项字符串为字典
    option_dict = {}
    for part in option_str.split(','):
        part = part.strip()
        if ':' in part:
            option_type, value = [x.strip() for x in part.split(':', 1)]
            option_dict[option_type] = standardize_option_name(value)
            
    # 获取每个选项类型的顺序
    sort_keys = []
    for option_type in get_option_types():
        value = option_dict.get(option_type, '')
        if not value:
            sort_keys.append(float('inf'))
            continue
            
        options = get_type_options(option_type)
        try:
            sort_keys.append(options.index(value))
        except ValueError:
            sort_keys.append(len(options))
            
    return sort_keys


def update_option_types(types: List[str]) -> None:
    """更新选项类型顺序
    
    Args:
        types: 新的选项类型顺序列表
    """
    settings = get_option_settings()
    settings['order'] = types
    save_option_settings(settings)


def update_type_options(type_options: Dict[str, List[str]]) -> None:
    """更新选项类型的选项值
    
    Args:
        type_options: 选项类型到选项值列表的映射
    """
    settings = get_option_settings()
    settings['type_options'] = type_options
    save_option_settings(settings)


def update_option_mapping(mapping: Dict[str, str]) -> None:
    """更新选项名称映射
    
    Args:
        mapping: 新的选项名称映射字典
    """
    settings = get_option_settings()
    settings['mapping'] = mapping
    save_option_settings(settings)