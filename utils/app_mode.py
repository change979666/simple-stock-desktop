"""
应用运行模式管理
统一使用客户端模式（API客户端-服务器架构）
"""


class AppMode:
    """应用运行模式单例"""
    _instance = None
    _is_client_mode = True  # 默认客户端模式（已废弃本地模式）
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def set_client_mode(self, is_client: bool):
        """设置为客户端模式
        
        Args:
            is_client: True=客户端模式(使用API), False=本地模式(使用数据库)
        """
        self._is_client_mode = is_client
        
    def is_client_mode(self) -> bool:
        """检查是否为客户端模式"""
        return self._is_client_mode
    
    def is_local_mode(self) -> bool:
        """检查是否为本地模式"""
        return not self._is_client_mode


# 全局单例
app_mode = AppMode()
