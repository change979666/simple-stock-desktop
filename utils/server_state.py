from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ServerState:
    """服务端全局状态管理器"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 初始化为当前时间戳
            cls._instance.last_data_change = datetime.now().timestamp()
        return cls._instance

    def mark_data_changed(self):
        """标记数据已发生变化"""
        self.last_data_change = datetime.now().timestamp()
        # logger.debug(f"数据状态已更新: {self.last_data_change}")

    def get_last_change_timestamp(self):
        """获取最后数据变化的时间戳"""
        return self.last_data_change


# 全局单例
server_state = ServerState()
