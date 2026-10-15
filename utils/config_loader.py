"""
统一配置加载模块
集中管理所有配置项，避免硬编码
"""
import configparser
import os


class ConfigLoader:
    """配置加载器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置"""
        if self._config is None:
            self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        from utils.file_encoding import read_ini_file
        self._config = configparser.ConfigParser()
        config_path = self._get_config_path()
        
        if os.path.exists(config_path):
            self._config = read_ini_file(config_path)
        else:
            # 创建默认配置
            self._create_default_config(config_path)
    
    def _get_config_path(self):
        """获取配置文件路径"""
        from utils.resource_path import get_app_data_path
        return get_app_data_path('config.ini')
    
    def _create_default_config(self, config_path):
        """创建默认配置文件"""
        from utils.file_encoding import write_ini_file
        
        self._config['USER'] = {
            'nickname': '未设置昵称'
        }
        self._config['Server'] = {
            'host': '127.0.0.1',
            'port': '8001'
        }
        self._config['Database'] = {
            'filename': 'database.db'
        }
        
        # 使用统一编码工具写入（UTF-8 无 BOM）
        write_ini_file(config_path, self._config)
    
    def get_server_host(self):
        """获取服务器主机地址"""
        return self._config.get('Server', 'host_ip', fallback='127.0.0.1')
    
    def get_server_port(self):
        """获取服务器端口"""
        return self._config.getint('Server', 'port', fallback=8001)
    
    def get_database_filename(self):
        """获取数据库文件名"""
        return self._config.get('Database', 'filename', fallback='database.db')
    
    def get_user_nickname(self):
        """获取用户昵称"""
        return self._config.get('USER', 'nickname', fallback='未设置昵称')
    
    def get_database_path(self):
        """获取完整的数据库路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        filename = self.get_database_filename()
        return os.path.join(root_dir, filename)
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        self._load_config()


# 全局配置实例
config = ConfigLoader()


def get_server_url():
    """获取完整的服务器URL"""
    host = config.get_server_host()
    port = config.get_server_port()
    return f"http://{host}:{port}"


def get_database_path():
    """获取数据库路径（快捷函数）"""
    return config.get_database_path()
