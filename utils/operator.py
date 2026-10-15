"""
操作者信息获取模块
用于避免GUI和CRUD模块之间的循环导入
"""
import socket
from datetime import datetime
from typing import Dict, Union
from config.settings import load_settings


def get_operator_info() -> Dict[str, str]:
    """
    获取操作者信息（昵称 + IP地址）
    
    从扁平格式配置文件 erp_settings.json 读取
    
    Returns:
        Dict[str, str]: 包含以下键的字典
            - name: 操作者昵称
            - ip: 操作者IP地址
            - display: 显示文本（格式：昵称 (IP)）
    
    Example:
        >>> info = get_operator_info()
        >>> print(info['display'])
        '张三 (192.168.1.100)'
    """
    # 从扁平格式配置文件读取操作员名称
    settings = load_settings()
    nickname = settings.get('operator_name', '未设置昵称')

    # 获取本机IP地址
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = 'localhost'

    return {
        'name': nickname,
        'ip': ip,
        'display': f'{nickname} ({ip})'
    }


def get_operator_display() -> str:
    """
    获取操作者显示文本（用于向后兼容）
    
    Returns:
        str: 格式化的操作者信息文本
    
    Example:
        >>> print(get_operator_display())
        '张三 (192.168.1.100)'
    """
    operator_info = get_operator_info()
    return operator_info['display']


def format_operator_info(operator_info: Union[str, Dict]) -> str:
    """
    格式化操作者信息为字符串
    支持字符串和字典两种输入格式
    
    Args:
        operator_info: 操作者信息，可以是字符串或字典
    
    Returns:
        str: 格式化后的字符串
    """
    if isinstance(operator_info, dict):
        return operator_info.get('display', str(operator_info))
    else:
        return str(operator_info)


def get_current_time() -> datetime:
    """
    获取当前本地时间
    
    Returns:
        datetime: 当前时间对象
    """
    return datetime.now()
