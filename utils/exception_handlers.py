"""
异常处理装饰器和工具函数
提供统一的异常保护和用户友好的错误提示
"""
import functools
import logging
from typing import Callable, Any, Optional
from PyQt6.QtWidgets import QMessageBox, QWidget

# 配置日志
logger = logging.getLogger(__name__)


def safe_gui_operation(
    error_title: str = "操作失败",
    error_message: str = "操作执行失败，请重试",
    show_dialog: bool = True,
    parent: Optional[QWidget] = None
):
    """
    GUI操作异常保护装饰器
    
    Args:
        error_title: 错误对话框标题
        error_message: 错误消息前缀
        show_dialog: 是否显示错误对话框
        parent: 父窗口（用于对话框）
    
    Usage:
        @safe_gui_operation("加载失败", "无法加载数据")
        def load_data(self):
            # 可能抛出异常的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                logger.error(f"{func.__name__} 执行失败: {e}", exc_info=True)
                
                # 显示用户友好的错误提示
                if show_dialog:
                    # 尝试从args中获取self（如果是方法）
                    widget = parent
                    if not widget and args and isinstance(args[0], QWidget):
                        widget = args[0]
                    
                    QMessageBox.critical(
                        widget,
                        error_title,
                        f'{error_message}\n\n'
                        f'错误详情: {str(e)}\n\n'
                        '可能原因:\n'
                        '• 网络连接中断\n'
                        '• 服务器未响应\n'
                        '• 数据格式错误\n\n'
                        '请检查网络连接和服务器状态后重试'
                    )
                
                return None
        return wrapper
    return decorator


def safe_api_call(
    error_title: str = "API调用失败",
    error_message: str = "无法连接到服务器",
    show_dialog: bool = True,
    parent: Optional[QWidget] = None,
    return_on_error: Any = None
):
    """
    API调用异常保护装饰器
    
    Args:
        error_title: 错误对话框标题
        error_message: 错误消息前缀
        show_dialog: 是否显示错误对话框
        parent: 父窗口（用于对话框）
        return_on_error: 异常时返回的默认值
    
    Usage:
        @safe_api_call("获取数据失败", return_on_error=[])
        def get_products(self):
            return self.dal.get_all_products()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                logger.error(f"{func.__name__} API调用失败: {e}", exc_info=True)
                
                # 显示用户友好的错误提示
                if show_dialog:
                    # 尝试从args中获取self（如果是方法）
                    widget = parent
                    if not widget and args and isinstance(args[0], QWidget):
                        widget = args[0]
                    
                    QMessageBox.critical(
                        widget,
                        error_title,
                        f'{error_message}\n\n'
                        f'错误详情: {str(e)}\n\n'
                        '可能原因:\n'
                        '• 服务器未启动\n'
                        '• 网络连接异常\n'
                        '• API接口错误\n\n'
                        '请确保服务端正常运行并检查网络连接'
                    )
                
                return return_on_error
        return wrapper
    return decorator


def safe_database_operation(
    error_title: str = "数据库操作失败",
    error_message: str = "数据库操作执行失败",
    show_dialog: bool = True,
    parent: Optional[QWidget] = None,
    return_on_error: Any = None
):
    """
    数据库操作异常保护装饰器
    
    Args:
        error_title: 错误对话框标题
        error_message: 错误消息前缀
        show_dialog: 是否显示错误对话框
        parent: 父窗口（用于对话框）
        return_on_error: 异常时返回的默认值
    
    Usage:
        @safe_database_operation("保存失败", return_on_error=False)
        def save_data(self, data):
            self.session.add(data)
            self.session.commit()
            return True
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 记录日志
                logger.error(f"{func.__name__} 数据库操作失败: {e}", exc_info=True)
                
                # 显示用户友好的错误提示
                if show_dialog:
                    # 尝试从args中获取self（如果是方法）
                    widget = parent
                    if not widget and args and isinstance(args[0], QWidget):
                        widget = args[0]
                    
                    QMessageBox.critical(
                        widget,
                        error_title,
                        f'{error_message}\n\n'
                        f'错误详情: {str(e)}\n\n'
                        '可能原因:\n'
                        '• 数据库连接失败\n'
                        '• 数据约束冲突\n'
                        '• 数据格式错误\n\n'
                        '请检查数据完整性后重试'
                    )
                
                return return_on_error
        return wrapper
    return decorator


def safe_batch_operation(func: Callable) -> Callable:
    """
    批量操作异常保护装饰器
    自动跳过失败项，继续处理剩余数据
    
    Usage:
        @safe_batch_operation
        def process_items(self, items):
            results = []
            for item in items:
                # 如果单项处理失败，会被捕获并记录，但不影响其他项
                result = self.process_single(item)
                results.append(result)
            return results
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{func.__name__} 批量操作失败: {e}", exc_info=True)
            # 批量操作失败时，返回空列表
            return []
    return wrapper


def safe_item_operation(func: Callable) -> Callable:
    """
    单项操作异常保护装饰器
    用于批量操作中的单项处理
    
    Usage:
        @safe_item_operation
        def process_single(self, item):
            # 处理单个项目
            return processed_item
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 记录错误但不抛出，让批量操作继续
            logger.warning(f"{func.__name__} 单项操作失败: {e}")
            return None
    return wrapper


class SafeContext:
    """
    上下文管理器，用于安全的资源管理
    
    Usage:
        with SafeContext("打开文件", self) as ctx:
            with open(file_path) as f:
                data = f.read()
    """
    def __init__(
        self,
        operation_name: str = "操作",
        parent: Optional[QWidget] = None,
        show_error: bool = True
    ):
        self.operation_name = operation_name
        self.parent = parent
        self.show_error = show_error
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"{self.operation_name} 失败: {exc_val}", exc_info=True)
            
            if self.show_error:
                QMessageBox.critical(
                    self.parent,
                    f"{self.operation_name}失败",
                    f'{self.operation_name}执行失败\n\n'
                    f'错误详情: {str(exc_val)}\n\n'
                    '请检查操作参数后重试'
                )
            
            # 返回True表示异常已处理，不再传播
            return True


# 便捷函数：显示错误消息
def show_error(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
):
    """
    显示错误对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 错误消息
        details: 详细错误信息
    """
    full_message = message
    if details:
        full_message += f'\n\n错误详情:\n{details}'
    
    QMessageBox.critical(parent, title, full_message)


# 便捷函数：显示警告消息
def show_warning(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None
):
    """
    显示警告对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 警告消息
        details: 详细信息
    """
    full_message = message
    if details:
        full_message += f'\n\n详细信息:\n{details}'
    
    QMessageBox.warning(parent, title, full_message)
