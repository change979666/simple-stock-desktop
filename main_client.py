"""
SimpleStock 库存管理系统 - 纯客户端版本
所有数据操作通过API服务器完成，客户端不直接访问数据库
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from client.api_client import api_client, test_connection
from gui.main_window import MainWindow
from utils.app_mode import app_mode  # 导入运行模式管理
from config.settings import load_settings, get_setting


# ===================== 后台预加载线程 =====================
class DataPreloadThread(QThread):
    """后台数据预加载线程（不阻塞UI）"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal(bool)  # 完成信号（成功/失败）
    
    def run(self):
        """在后台线程执行数据预加载"""
        try:
            from utils.data_access import dal
            from utils.cache import data_cache
            import time
            
            start_time = time.time()
            self.progress.emit("正在预加载产品数据...")
            
            # 1. 预加载产品列表（只加载前100条，快速响应）
            try:
                # 使用分页API，只获取第一页（注意：这个缓存仅用于启动加速，不影响业务逻辑）
                response = dal.get_products_paginated(page=1, page_size=100)
                products = response.get('items', [])
                # 使用独立的缓存键，避免与主缓存products_list_full冲突
                data_cache.set('products_list_startup', products, ttl=1800)  # 30分钟（白天频繁查询但数据稳定）
                self.progress.emit(f"✅ 产品数据加载完成 ({len(products)}个)")
            except Exception as e:
                self.progress.emit(f"⚠️ 产品数据加载失败: {e}")
            
            # 2. 预加载仪表盘数据
            self.progress.emit("正在预加载仪表盘统计...")
            try:
                dashboard_data = dal.get_batch_dashboard_data(threshold=1.0)
                data_cache.set('dashboard_stats', dashboard_data, ttl=300)  # 5分钟（只在导入后查看）
                self.progress.emit("✅ 仪表盘统计加载完成")
            except Exception as e:
                self.progress.emit(f"⚠️ 仪表盘加载失败: {e}")
            
            # 3. 库存数据由库存管理页面首次访问时加载，不需要预加载
            # （避免启动时加载过多数据）
            
            elapsed = time.time() - start_time
            self.progress.emit(f"🎉 所有数据预加载完成 (耗时 {elapsed:.2f}秒)")
            self.finished.emit(True)
            
        except Exception as e:
            self.progress.emit(f"❌ 预加载失败: {e}")
            self.finished.emit(False)


def initialize_database():
    """初始化数据库表结构
    
    如果数据库不存在或表不完整,自动创建所有表
    """
    try:
        # 使用已有的init_db函数
        from database.init_db import init_db
        
        print("正在创建数据库表...")
        init_db()
        print("✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_config() -> dict:
    """从统一配置文件加载配置
    
    Returns:
        配置字典，如果配置不完整则返回None
    """
    try:
        # 从 erp_settings.json 加载配置
        settings = load_settings()
        
        # 解析 server_address (格式: "192.168.1.3:8001")
        server_address = settings.get('server_address', '').strip()
        if not server_address:
            print("❌ 配置文件中缺少服务器地址 (server_address)")
            return None
        
        # 分离主机和端口
        if ':' in server_address:
            host, port_str = server_address.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 8001
        else:
            host = server_address
            port = 8001
        
        # 获取操作员名称
        operator = settings.get('operator_name', '').strip()
        if not operator:
            print("⚠️  未设置操作员昵称，使用默认值")
            operator = '未设置昵称'
        
        return {
            'host': host,
            'port': port,
            'operator': operator
        }
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None


def start_background_cache_refresh(window):
    """启动后台缓存刷新定时器
    
    定期在后台刷新缓存数据，避免缓存过期时用户等待
    
    Args:
        window: 主窗口对象，用于绑定定时器
    """
    from PyQt6.QtCore import QTimer
    from utils.data_access import dal
    from utils.cache import data_cache
    
    def refresh_cache():
        """后台刷新缓存数据"""
        try:
            # 仅在缓存即将过期时刷新（避免过度刷新）
            
            # 1. 刷新产品列表（如果缓存已过期）
            cached = data_cache.get('products_list_startup')
            if cached is None:  # 已过期
                try:
                    response = dal.get_products_paginated(page=1, page_size=100)
                    products = response.get('items', [])
                    data_cache.set('products_list_startup', products, ttl=1800)  # 30分钟
                    print("🔄 后台刷新: 产品列表")
                except:
                    pass
            
            # 2. 刷新仪表盘数据（如果已过期）
            cached = data_cache.get('dashboard_stats')
            if cached is None:
                try:
                    dashboard_data = dal.get_batch_dashboard_data(threshold=1.0)
                    data_cache.set('dashboard_stats', dashboard_data, ttl=300)  # 5分钟
                    print("🔄 后台刷新: 仪表盘统计")
                except:
                    pass
                    
        except Exception as e:
            # 静默失败，不影响用户使用
            pass
    
    # 创建定时器（每10分钟刷新一次）
    refresh_timer = QTimer(window)
    refresh_timer.timeout.connect(refresh_cache)
    refresh_timer.start(600000)  # 10分钟 = 600000毫秒
    
    print("🔄 后台缓存刷新已启动 (每10分钟)")


def preload_common_data():
    """预加载常用数据到缓存（已废弃 - 改用后台线程）
    
    注意：此函数已被 DataPreloadThread 替代，不再使用
    保留仅为兼容性，避免其他地方调用时报错
    """
    print("⚠️ preload_common_data 已废弃，请使用 DataPreloadThread")
    pass


def initialize_client(config: dict) -> bool:
    """初始化API客户端（快速初始化，不做繁重操作）
    
    Args:
        config: 配置字典
        
    Returns:
        True: 初始化成功
        False: 初始化失败
    """

    try:
        # 获取操作员信息（使用统一的获取方法）
        from utils.operator import get_operator_info
        op_info = get_operator_info()
        operator_display = op_info['display']
        
        # 配置客户端
        api_client.configure(
            host=config['host'],
            port=config['port'],
            operator_info=operator_display
        )
        
        print("API客户端已配置:")
        print(f"  服务器: {config['host']}:{config['port']}")
        print(f"  操作者: {operator_display}")
        
        # 快速连接测试（3秒超时）
        print("正在测试服务器连接...")
        original_timeout = api_client._timeout
        api_client._timeout = 3  # 临时缩短超时时间用于快速测试
        if not test_connection():
            raise Exception("服务器连接测试失败")
        
        api_client._timeout = original_timeout  # 恢复原始超时
        print("✅ 服务器连接成功")
        
        # 不再在这里预加载数据（改为后台线程）
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        
        # 显示错误对话框
        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None,
                "连接失败",
                f"无法连接到服务器\n\n"
                f"服务器: {config['host']}:{config['port']}\n"
                f"错误: {str(e)}\n\n"
                f"请检查:\n"
                f"1. 服务器IP地址是否正确\n"
                f"2. 服务器程序是否已启动 (启动服务端.bat)\n"
                f"3. 网络连接是否正常\n"
                f"4. 防火墙是否允许连接\n\n"
                f"提示: 您可以在设置中重新配置服务器连接。"
            )
        
        return False


def main():
    """主函数 - 纯客户端模式"""
    # 设置为客户端模式(使用API而不是本地数据库)
    app_mode.set_client_mode(True)
    
    # 设置控制台编码为UTF-8，避免Windows下的编码问题
    import sys
    import io
    if sys.platform == 'win32':
        # 在windowed模式下,stdout/stderr可能是None,需要检查
        if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("SimpleStock 库存管理系统 - 客户端")
    print("="*60)
    print("📡 客户端模式: 所有数据通过API服务器访问")
    print("-"*60)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("SimpleStock Client")
    
    # 加载配置
    config = load_config()
    
    # 如果配置不存在或不完整，提示错误并退出
    if config is None:
        QMessageBox.critical(
            None,
            "配置错误",
            "未找到有效的配置文件！\n\n"
            "请确保 erp_settings.json 文件存在并包含以下配置:\n\n"
            "{\n"
            '  "server": {\n'
            '    "host_ip": "服务器IP地址",\n'
            '    "port": 8001\n'
            "  },\n"
            '  "user_info": {\n'
            '    "nickname": "您的昵称"\n'
            "  }\n"
            "}\n\n"
            "提示: 您可以在设置界面配置服务器连接和操作员信息"
        )
        print("❌ 配置错误，程序退出")
        return
    else:
        print("✅ 加载配置成功")
    
    # 初始化API客户端
    if not initialize_client(config):
        QMessageBox.critical(
            None,
            "连接失败",
            f"无法连接到服务器\n\n"
            f"服务器: {config['host']}:{config['port']}\n\n"
            f"请检查:\n"
            f"1. 服务器IP地址是否正确\n"
            f"2. 服务器程序是否已启动 (启动服务端.bat)\n"
            f"3. 网络连接是否正常\n"
            f"4. 防火墙是否允许连接"
        )
        print("❌ 无法连接到服务器，程序退出")
        return
    
    # 启动主窗口
    print("-"*60)
    print("🚀 启动主界面...")
    
    # 客户端模式下不需要初始化本地数据库
    # 所有数据操作都通过API完成
    print("⚠️ 客户端模式: 不使用本地数据库,所有操作通过API")
    
    try:
        # ========== 关键优化：先显示界面，数据后台加载 ==========
        window = MainWindow()
        window.show()
        
        print("✅ 界面启动成功（数据将在后台加载）")
        print("="*60)
        
        # ========== 延迟200ms后启动后台预加载 ==========
        def start_preload():
            print("\n🔄 开始后台预加载数据...")
            preload_thread = DataPreloadThread()
            
            # 连接进度信号到状态栏
            preload_thread.progress.connect(
                lambda msg: window.status_bar.showMessage(msg, 3000)
            )
            
            # 连接完成信号
            def on_preload_finished(success):
                if success:
                    window.status_bar.showMessage("✅ 数据加载完成", 5000)
                    # 刷新仪表盘（如果用户在仪表盘页面）
                    if window.tab_widget.currentWidget() == window.dashboard_view:
                        window.dashboard_view.load_data()
                else:
                    window.status_bar.showMessage("⚠️ 部分数据加载失败", 5000)
            
            preload_thread.finished.connect(on_preload_finished)
            preload_thread.start()
            
            # 保存线程引用，防止被垃圾回收
            window._preload_thread = preload_thread
        
        QTimer.singleShot(200, start_preload)
        
        # 启动后台缓存刷新定时器
        start_background_cache_refresh(window)
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        
        QMessageBox.critical(
            None,
            "启动失败",
            f"程序启动失败:\n\n{str(e)}\n\n"
            f"请查看控制台输出获取详细信息。"
        )


if __name__ == "__main__":
    main()
