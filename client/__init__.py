"""
客户端模块
提供API客户端和相关UI组件
"""
from .api_client import api_client, configure_client, set_operator_info, test_connection

__all__ = [
    'api_client',
    'configure_client',
    'set_operator_info',
    'test_connection',
]
