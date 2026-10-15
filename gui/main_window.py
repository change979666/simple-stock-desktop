from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QStatusBar
)
from PyQt6.QtCore import Qt

from .dashboard_view import DashboardView
from .product_view import ProductView
from .sales_view import SalesView
from .sku_sales_stats_view import SkuSalesStatsView
from .analytics_view import AnalyticsView
from .inventory_view import InventoryView
from .shipment_view import ShipmentView
from .inventory_log_view import OperationLogView
from .settings_view import SettingsView
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout,
    QWidget, QStatusBar, QLabel, QHBoxLayout,
    QMessageBox
)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QIcon

from utils.operator import get_operator_info, get_operator_display
from client.api_client import api_client
from .models import shared_state
from .styles import MAIN_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 保存到共享状态
        shared_state.main_window = self
        
        # 设置窗口标题和大小
        self.setWindowTitle('库存管理系统 v5.2.0')
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)  # 设置最小尺寸
        # 允许窗口调整大小
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        # 创建并设置中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        
        # 设置窗口样式
        self.setStyleSheet(MAIN_STYLE)
        
        # 添加各个视图
        # 创建所有视图（传递API客户端给需要的视图）
        self.dashboard_view = DashboardView()
        self.product_view = ProductView()
        self.inventory_view = InventoryView(api_client)
        self.sales_view = SalesView()
        self.sku_sales_stats_view = SkuSalesStatsView()
        self.analytics_view = AnalyticsView(api_client)
        self.shipment_view = ShipmentView()
        self.inventory_log_view = OperationLogView()
        self.settings_view = SettingsView()
        
        # 按指定顺序添加标签页
        self.tab_widget.addTab(self.dashboard_view, '📊 仪表盘')
        self.tab_widget.addTab(self.product_view, '📦 产品管理')
        self.tab_widget.addTab(self.inventory_view, '📋 库存管理')
        self.tab_widget.addTab(self.sales_view, '💰 销售管理')
        self.tab_widget.addTab(self.sku_sales_stats_view, '📈 SKU销量')
        self.tab_widget.addTab(self.analytics_view, '📊 数据分析')
        self.tab_widget.addTab(self.shipment_view, '🚚 发货管理')
        self.tab_widget.addTab(self.inventory_log_view, '📝 操作记录')
        self.tab_widget.addTab(self.settings_view, '⚙️ 设置')
        
        self.layout.addWidget(self.tab_widget)
        
        # 创建状态栏并显示操作者和服务端信息
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建状态栏标签
        self.operator_label = QLabel()
        self.server_status_label = QLabel()
        
        # 创建居中的消息标签
        self.center_message_label = QLabel()
        self.center_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_message_label.setStyleSheet("""
            QLabel {
                color: #52c41a;
                font-weight: bold;
                font-size: 13px;
                padding: 2px 10px;
            }
        """)
        
        self.status_bar.addWidget(self.operator_label)
        self.status_bar.addWidget(self.center_message_label, 1)  # 居中标签占据剩余空间
        self.status_bar.addPermanentWidget(self.server_status_label)
        
        # 初始化服务端配置
        self.load_server_config()
        
        # 更新操作者信息
        self.update_operator_info()
        
        # 启动服务端状态检查定时器
        self.server_check_timer = QTimer()
        self.server_check_timer.timeout.connect(self.check_server_status)
        self.server_check_timer.start(5000)  # 每5秒检查一次
        
        # 立即检查一次服务端状态
        self.check_server_status()
        
        # 连接设置保存信号到刷新方法
        self.settings_view.settings_saved.connect(self.on_settings_saved)
        
        # 连接销售订单导入信号到库存页面刷新
        self.sales_view.orders_imported.connect(self.on_orders_imported)
    
    def on_orders_imported(self):
        """订单导入/变化后智能刷新页面"""
        # 刷新库存视图（销量统计需要更新）
        self.inventory_view.load_inventory()
        
        # 智能刷新仪表盘（销售统计需要更新）
        self.dashboard_view.load_data(trigger='smart')
    
    def load_server_config(self):
        """加载服务端配置（从erp_settings.json）"""
        from config.settings import load_settings
        settings = load_settings()
        server_address = settings.get('server_address', '127.0.0.1:8001')
        
        if ':' in server_address:
            self.server_host, port_str = server_address.split(':', 1)
            self.server_port = int(port_str)
        else:
            self.server_host = server_address
            self.server_port = 8001
    
    def check_server_status(self):
        """检查服务端连接状态（使用api_client）"""
        try:
            # 使用已配置的api_client进行健康检查
            result = api_client.health_check()
            if result and result.get('status') == 'ok':
                self.server_status_label.setText(
                    f'🟢 服务端: {self.server_host}:{self.server_port}'
                )
                self.server_status_label.setStyleSheet("color: green;")
            else:
                self.server_status_label.setText(
                    f'🟡 服务端: {self.server_host}:{self.server_port} (状态异常)'
                )
                self.server_status_label.setStyleSheet("color: orange;")
        except Exception:
            self.server_status_label.setText(
                f'🔴 服务端: {self.server_host}:{self.server_port} (未连接)'
            )
            self.server_status_label.setStyleSheet("color: red;")
    
    def update_operator_info(self):
        """更新状态栏中的操作者信息"""
        display_text = get_operator_display()
        self.operator_label.setText(f'操作者: {display_text}')
    
    def on_settings_saved(self):
        """设置保存后的处理 - 刷新相关视图"""
        # 刷新库存视图（预警值可能已更改）
        self.inventory_view.load_inventory()
        
        # 刷新仪表盘（预警值可能已更改）
        self.dashboard_view.load_data()
        
        # 更新操作员信息（昵称可能已更改）
        self.update_operator_info()
    
