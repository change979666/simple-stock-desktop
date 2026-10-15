"""
全局数据缓存管理器
支持TTL(Time To Live)、按key缓存、缓存失效等功能
"""
import time
from typing import Any, Optional, Dict
from threading import Lock


class DataCache:
    """全局数据缓存管理器
    
    Features:
        - TTL缓存: 支持设置缓存过期时间
        - 线程安全: 使用锁保护缓存操作
        - 按key缓存: 支持按key存储和获取
        - 批量失效: 支持清除单个key或全部缓存
        - 缓存统计: 支持查看缓存命中率
    
    Example:
        >>> cache = DataCache()
        >>> cache.set('products', products_data, ttl=300)
        >>> data = cache.get('products')
        >>> cache.invalidate('products')
    """
    
    def __init__(self, default_ttl: int = 300):
        """初始化缓存管理器
        
        Args:
            default_ttl: 默认缓存时间(秒)，默认5分钟
        """
        self.cache: Dict[str, Any] = {}
        self.cache_time: Dict[str, float] = {}
        self.cache_ttl: Dict[str, int] = {}
        self.default_ttl = default_ttl
        self._lock = Lock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """获取缓存数据
        
        Args:
            key: 缓存键
            default: 缓存不存在时的默认值
            
        Returns:
            缓存的数据，如果不存在或已过期则返回default
        """
        with self._lock:
            if key not in self.cache:
                self.misses += 1
                return default
            
            # 检查是否过期
            cache_time = self.cache_time.get(key, 0)
            ttl = self.cache_ttl.get(key, self.default_ttl)
            
            if time.time() - cache_time > ttl:
                # 缓存过期，删除并返回None
                self._remove_cache(key)
                self.misses += 1
                return default
            
            # 缓存命中
            self.hits += 1
            return self.cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存时间(秒)，None表示使用默认TTL
        """
        with self._lock:
            self.cache[key] = value
            self.cache_time[key] = time.time()
            self.cache_ttl[key] = ttl if ttl is not None else self.default_ttl
    
    def invalidate(self, key: Optional[str] = None):
        """清除缓存
        
        Args:
            key: 要清除的缓存键，None表示清除全部缓存
        """
        with self._lock:
            if key:
                self._remove_cache(key)
            else:
                # 清除全部缓存
                self.cache.clear()
                self.cache_time.clear()
                self.cache_ttl.clear()
    
    def invalidate_pattern(self, pattern: str):
        """清除匹配模式的缓存
        
        Args:
            pattern: 键名模式（支持简单的通配符 *）
        """
        with self._lock:
            # 找出所有匹配的key
            keys_to_remove = []
            for key in list(self.cache.keys()):
                if self._match_pattern(key, pattern):
                    keys_to_remove.append(key)
            
            # 删除匹配的key
            for key in keys_to_remove:
                self._remove_cache(key)
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的模式匹配
        
        Args:
            key: 键名
            pattern: 模式（支持 * 通配符）
            
        Returns:
            是否匹配
        """
        if '*' not in pattern:
            return key == pattern
        
        # 简单实现: 只支持 prefix* 和 *suffix 模式
        if pattern.startswith('*') and pattern.endswith('*'):
            return pattern[1:-1] in key
        elif pattern.startswith('*'):
            return key.endswith(pattern[1:])
        elif pattern.endswith('*'):
            return key.startswith(pattern[:-1])
        else:
            # 包含*但不在开头或结尾，暂不支持
            return key == pattern
    
    def _remove_cache(self, key: str):
        """删除指定缓存（内部方法，不加锁）
        
        Args:
            key: 缓存键
        """
        self.cache.pop(key, None)
        self.cache_time.pop(key, None)
        self.cache_ttl.pop(key, None)
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            缓存是否存在
        """
        return self.get(key) is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            {
                'total_keys': 缓存键数量,
                'hits': 命中次数,
                'misses': 未命中次数,
                'hit_rate': 命中率,
                'cache_keys': 缓存键列表
            }
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'total_keys': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f'{hit_rate:.2f}%',
            'cache_keys': list(self.cache.keys())
        }
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self.hits = 0
            self.misses = 0
    
    def clear(self):
        """清空所有缓存（别名方法）"""
        self.invalidate()
    
    def size(self) -> int:
        """获取缓存键数量"""
        return len(self.cache)


# 全局缓存实例
data_cache = DataCache(default_ttl=300)  # 默认5分钟TTL


def get_cache() -> DataCache:
    """获取全局缓存实例
    
    Returns:
        全局缓存管理器实例
    """
    return data_cache


# 便捷函数
def cache_get(key: str, default: Any = None) -> Optional[Any]:
    """获取缓存（便捷函数）"""
    return data_cache.get(key, default)


def cache_set(key: str, value: Any, ttl: Optional[int] = None):
    """设置缓存（便捷函数）"""
    data_cache.set(key, value, ttl)


def cache_invalidate(key: Optional[str] = None):
    """清除缓存（便捷函数）"""
    data_cache.invalidate(key)


def cache_clear():
    """清空所有缓存（便捷函数）"""
    data_cache.clear()
