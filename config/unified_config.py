"""
统一配置管理模块
提供配置的统一访问接口，支持本地和远程配置
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional
from utils.resource_path import get_app_data_path


class UnifiedConfigManager:
    """统一配置管理器（单例）"""
    
    _instance = None
    _config: Dict[str, Any] = None
    _config_file = "erp_settings.json"
    
    # 默认配置模板
    DEFAULT_CONFIG = {
        "server": {
            "host_ip": "127.0.0.1",
            "port": 8001,
            "auto_connect": True,
            "timeout": 30
        },
        "user_info": {
            "nickname": "未设置昵称",
            "ip_address": "0.0.0.0",
            "role": "操作员"
        },
        "database": {
            "filename": "database.db"
        },
        "inventory": {
            "default_warning_level": 100,
            "warning_enabled": True,
            "notification_enabled": True
        },
        "column_widths": {
            "product_view": {
                "parent_sku": 150,
                "sku": 200,
                "option": 200,
                "price": 100
            },
            "inventory_view": {
                "sku": 200,
                "stock": 80,
                "warning": 80,
                "status": 100
            }
        },
        "table_style": {
            "show_grid": True,
            "alternate_colors": True,
            "row_height": 30
        },
        "navigation_order": [
            "dashboard",
            "products",
            "inventory",
            "transit",
            "sales",
            "inventory_logs",
            "settings"
        ]
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _get_config_path(self) -> Path:
        """获取配置文件路径"""
        return Path(get_app_data_path(self._config_file))
    
    def _load_config(self):
        """加载配置文件"""
        config_path = self._get_config_path()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                # 合并默认配置（确保所有必需键存在）
                self._merge_defaults()
            except Exception as e:
                print(f"加载配置失败: {e}，使用默认配置")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            # 创建默认配置
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()
    
    def _merge_defaults(self):
        """合并默认配置，确保所有键存在"""
        def deep_merge(default: dict, current: dict) -> dict:
            """递归合并字典"""
            result = default.copy()
            for key, value in current.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = deep_merge(self.DEFAULT_CONFIG, self._config)
    
    def save(self):
        """保存配置到文件"""
        config_path = self._get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, *keys: str, default=None) -> Any:
        """获取配置值
        
        Args:
            *keys: 配置键路径，例如 get('server', 'host_ip')
            default: 默认值
            
        Returns:
            配置值
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, *keys: str, value: Any):
        """设置配置值
        
        Args:
            *keys: 配置键路径，最后一个参数是要设置的值
            value: 要设置的值
        """
        if len(keys) == 0:
            return
        
        # 确保路径存在
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 设置值
        current[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()
    
    def update(self, config: Dict[str, Any]):
        """更新配置"""
        self._config.update(config)
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        self._load_config()


# 全局配置管理器实例
config_manager = UnifiedConfigManager()


# 便捷函数
def get_config(*keys: str, default=None) -> Any:
    """获取配置值"""
    return config_manager.get(*keys, default=default)


def set_config(*keys: str, value: Any):
    """设置配置值"""
    config_manager.set(*keys, value=value)


def save_config() -> bool:
    """保存配置"""
    return config_manager.save()


def reload_config():
    """重新加载配置"""
    config_manager.reload()


def get_all_config() -> Dict[str, Any]:
    """获取所有配置"""
    return config_manager.get_all()
