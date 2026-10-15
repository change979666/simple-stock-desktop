"""
数据变更跟踪器 - 轻量级询问机制的核心
记录最后数据修改时间，用于减少客户端无效请求
"""
import time
from threading import Lock
from datetime import datetime


class DataChangeTracker:
    """
    数据变更跟踪器（单例）
    维护全局最后数据修改时间戳
    """
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._last_change_time = time.time()
        self._change_count = 0
        
        print(f"🔔 数据变更跟踪器已初始化 - 时间戳: {self._last_change_time}")
    
    def mark_data_changed(self, operation: str = "unknown"):
        """
        标记数据已变更
        
        Args:
            operation: 操作类型描述（用于调试）
        """
        with self._lock:
            self._last_change_time = time.time()
            self._change_count += 1
            
            print(f"🔔 数据变更 #{self._change_count}: {operation} "
                  f"(时间戳: {self._last_change_time:.3f})")
    
    def get_last_change_time(self) -> float:
        """
        获取最后数据变更时间戳
        
        Returns:
            Unix时间戳（秒）
        """
        with self._lock:
            return self._last_change_time
    
    def get_change_info(self) -> dict:
        """
        获取变更信息（用于状态接口）
        
        Returns:
            包含时间戳和变更次数的字典
        """
        with self._lock:
            readable_time = datetime.fromtimestamp(
                self._last_change_time
            ).strftime('%Y-%m-%d %H:%M:%S')
            return {
                "last_change": self._last_change_time,
                "change_count": self._change_count,
                "timestamp_readable": readable_time
            }


# 全局单例
_tracker = DataChangeTracker()


def mark_data_changed(operation: str = "unknown"):
    """
    全局函数：标记数据已变更
    
    在所有数据修改操作后调用此函数
    
    Args:
        operation: 操作描述（如：add_product, update_stock, delete_order）
    """
    _tracker.mark_data_changed(operation)


def get_last_change_time() -> float:
    """
    全局函数：获取最后数据变更时间戳
    
    Returns:
        Unix时间戳（秒）
    """
    return _tracker.get_last_change_time()


def get_change_info() -> dict:
    """
    全局函数：获取变更信息
    
    Returns:
        包含时间戳和变更次数的字典
    """
    return _tracker.get_change_info()
