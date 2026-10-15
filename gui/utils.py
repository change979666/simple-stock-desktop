"""
通用工具函数模块
"""
import socket
from datetime import datetime
from config.settings import load_settings


def get_operator_info() -> dict:
    """获取操作者信息（昵称 + IP地址）
    
    从扁平格式配置文件 erp_settings.json 读取
    """
    # 从扁平格式配置读取操作员名称
    settings = load_settings()
    nickname = settings.get('operator_name', '未设置昵称')
    
    # 获取本机IP地址
    try:
        # 连接外部地址以获取真实的本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = 'localhost'
    
    # 返回字典格式，同时保持向后兼容
    return {
        'name': nickname,
        'ip': ip,
        'display': f'{nickname} ({ip})'
    }


def get_operator_display() -> str:
    """获取操作者显示文本（用于向后兼容）"""
    operator_info = get_operator_info()
    if isinstance(operator_info, dict):
        return operator_info['display']
    else:
        return str(operator_info)


def get_current_time() -> datetime:
    """获取当前本地时间"""
    return datetime.now()