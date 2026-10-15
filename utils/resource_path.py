"""
资源路径处理模块
确保在开发环境和PyInstaller打包后都能正确找到资源文件
"""
import sys
import os


def resource_path(relative_path):
    """
    获取资源的绝对路径，兼容开发环境和打包后的环境
    
    Args:
        relative_path: 相对路径(如 "config.ini", "assets/icon.png")
    
    Returns:
        资源的绝对路径
        
    使用示例:
        icon_path = resource_path("assets/icon.png")
        config_path = resource_path("config.ini")
    """
    try:
        # PyInstaller 会创建一个临时文件夹 _MEIPASS，并把资源放在那里
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境,使用项目根目录
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_app_data_path(relative_path=""):
    """
    获取应用数据目录的路径(用于存储配置文件、数据库等)
    
    打包后,这些文件保存在exe所在目录,方便用户访问和修改
    
    Args:
        relative_path: 相对路径
        
    Returns:
        应用数据目录的绝对路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境,使用exe所在目录
        app_path = os.path.dirname(sys.executable)
    else:
        # 开发环境,使用项目根目录
        app_path = os.path.abspath(".")
    
    if relative_path:
        return os.path.join(app_path, relative_path)
    return app_path
