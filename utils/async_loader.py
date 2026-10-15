"""
异步数据加载框架

使用QThread在后台加载数据，避免UI冻结
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Optional
import traceback


class DataLoaderWorker(QThread):
    """数据加载工作线程
    
    在后台线程中执行数据加载操作，完成后通过信号通知主线程
    """
    
    # 信号定义
    finished = pyqtSignal(object)  # 加载完成，传递结果数据
    error = pyqtSignal(str)  # 加载失败，传递错误信息
    progress = pyqtSignal(int)  # 加载进度（0-100）
    
    def __init__(self, load_func: Callable, *args, **kwargs):
        """初始化Worker
        
        Args:
            load_func: 要执行的加载函数
            *args, **kwargs: 传递给load_func的参数
        """
        super().__init__()
        self.load_func = load_func
        self.args = args
        self.kwargs = kwargs
        self._is_cancelled = False
    
    def run(self):
        """执行加载任务（在后台线程中运行）"""
        try:
            # 执行加载函数
            result = self.load_func(*self.args, **self.kwargs)
            
            # 检查是否被取消
            if self._is_cancelled:
                return
            
            # 发送完成信号
            self.finished.emit(result)
            
        except Exception as e:
            # 捕获异常并发送错误信号
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
    
    def cancel(self):
        """取消加载任务"""
        self._is_cancelled = True


class AsyncDataLoader:
    """异步数据加载器
    
    提供简单的API用于异步加载数据
    
    使用示例:
        loader = AsyncDataLoader()
        loader.load_data(
            load_func=dal.get_all_products,
            on_success=self.on_products_loaded,
            on_error=self.on_load_error
        )
    """
    
    def __init__(self):
        self.current_worker: Optional[DataLoaderWorker] = None
    
    def load_data(self,
                  load_func: Callable,
                  on_success: Callable[[Any], None],
                  on_error: Optional[Callable[[str], None]] = None,
                  on_progress: Optional[Callable[[int], None]] = None,
                  *args, **kwargs):
        """异步加载数据
        
        Args:
            load_func: 数据加载函数
            on_success: 成功回调函数，接收加载的数据
            on_error: 错误回调函数（可选），接收错误信息
            on_progress: 进度回调函数（可选），接收进度值0-100
            *args, **kwargs: 传递给load_func的参数
        """
        # 取消之前的加载任务
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
        
        # 创建新的Worker
        self.current_worker = DataLoaderWorker(load_func, *args, **kwargs)
        
        # 连接信号
        self.current_worker.finished.connect(on_success)
        if on_error:
            self.current_worker.error.connect(on_error)
        if on_progress:
            self.current_worker.progress.connect(on_progress)
        
        # 启动Worker
        self.current_worker.start()
    
    def cancel(self):
        """取消当前加载任务"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
    
    def is_loading(self) -> bool:
        """检查是否正在加载"""
        return self.current_worker is not None and \
               self.current_worker.isRunning()


class BatchDataLoaderWorker(QThread):
    """批量数据加载Worker
    
    支持加载多个数据源，逐个发送结果
    """
    
    # 信号定义
    item_loaded = pyqtSignal(str, object)  # 单项加载完成 (name, data)
    all_finished = pyqtSignal(dict)  # 全部完成 {name: data}
    error = pyqtSignal(str, str)  # 加载失败 (name, error_msg)
    progress = pyqtSignal(int, int)  # 进度 (current, total)
    
    def __init__(self, load_tasks: dict):
        """初始化批量加载Worker
        
        Args:
            load_tasks: {name: (load_func, args, kwargs)}
        """
        super().__init__()
        self.load_tasks = load_tasks
        self._is_cancelled = False
    
    def run(self):
        """执行批量加载任务"""
        results = {}
        total = len(self.load_tasks)
        current = 0
        
        for name, (load_func, args, kwargs) in self.load_tasks.items():
            if self._is_cancelled:
                break
            
            try:
                # 执行加载
                result = load_func(*args, **kwargs)
                results[name] = result
                
                # 发送单项完成信号
                self.item_loaded.emit(name, result)
                
            except Exception as e:
                # 发送错误信号
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(name, error_msg)
            
            # 更新进度
            current += 1
            self.progress.emit(current, total)
        
        # 发送全部完成信号
        if not self._is_cancelled:
            self.all_finished.emit(results)
    
    def cancel(self):
        """取消加载"""
        self._is_cancelled = True


class BatchAsyncDataLoader:
    """批量异步数据加载器
    
    用于同时加载多个数据源
    
    使用示例:
        loader = BatchAsyncDataLoader()
        loader.load_batch({
            'products': (dal.get_all_products, (), {}),
            'inventory': (dal.get_inventory, (), {})
        },
        on_item_loaded=self.on_item_loaded,
        on_all_finished=self.on_all_loaded
        )
    """
    
    def __init__(self):
        self.current_worker: Optional[BatchDataLoaderWorker] = None
    
    def load_batch(self,
                   load_tasks: dict,
                   on_item_loaded: Optional[Callable[[str, Any], None]] = None,
                   on_all_finished: Optional[Callable[[dict], None]] = None,
                   on_error: Optional[Callable[[str, str], None]] = None,
                   on_progress: Optional[Callable[[int, int], None]] = None):
        """批量加载数据
        
        Args:
            load_tasks: {name: (load_func, args, kwargs)}
            on_item_loaded: 单项完成回调 (name, data)
            on_all_finished: 全部完成回调 {name: data}
            on_error: 错误回调 (name, error_msg)
            on_progress: 进度回调 (current, total)
        """
        # 取消之前的任务
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
        
        # 创建新Worker
        self.current_worker = BatchDataLoaderWorker(load_tasks)
        
        # 连接信号
        if on_item_loaded:
            self.current_worker.item_loaded.connect(on_item_loaded)
        if on_all_finished:
            self.current_worker.all_finished.connect(on_all_finished)
        if on_error:
            self.current_worker.error.connect(on_error)
        if on_progress:
            self.current_worker.progress.connect(on_progress)
        
        # 启动Worker
        self.current_worker.start()
    
    def cancel(self):
        """取消加载"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
    
    def is_loading(self) -> bool:
        """检查是否正在加载"""
        return self.current_worker is not None and \
               self.current_worker.isRunning()
