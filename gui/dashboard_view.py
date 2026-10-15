from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from datetime import datetime, timedelta

from utils.data_access import dal  # 统一数据访问层
from config.settings import load_settings  # 读取配置
from config.column_width_manager import get_column_width_manager
from .styles import DASHBOARD_STYLE
from utils.cache import data_cache  # 全局缓存


class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        
        # 🔥 轻量级询问机制：跟踪服务端数据变更时间戳
        self.last_server_timestamp = 0
        self.window_has_focus = True
        
        self.init_ui()
        self.load_data()
        
        # 自动刷新定时器（改为询问机制）
        from PyQt6.QtCore import QTimer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_and_refresh)
        self.refresh_timer.start(60000)  # 60秒询问一次
        self.setStyleSheet(DASHBOARD_STYLE)

    def init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建销售统计布局
        sales_layout = QHBoxLayout()
        sales_layout.setSpacing(15)
        
        # 创建4个销售统计面板
        self.stats_panels = {
            'today': self.create_stats_panel('今日销售'),
            'yesterday': self.create_stats_panel('昨日销售'),
            'week': self.create_stats_panel('最近七天'),
            'month': self.create_stats_panel('最近三十天')
        }
        
        # 添加面板到布局
        for panel in self.stats_panels.values():
            sales_layout.addWidget(panel)
            
        layout.addLayout(sales_layout)
        
        # 创建警告面板
        warning_panel = QFrame()
        warning_panel.setProperty("warningPanel", True)
        warning_layout = QVBoxLayout(warning_panel)
        warning_layout.setSpacing(12)
        warning_layout.setContentsMargins(15, 15, 15, 15)
        
        # 警告标题栏
        warning_header = QWidget()
        warning_header_layout = QHBoxLayout(warning_header)
        warning_header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.warning_title = QLabel('库存预警')
        self.warning_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1a1a1a;
        """)
        warning_header_layout.addWidget(self.warning_title)
        warning_header_layout.addStretch()
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #0d6efd;
                color: white;
                font-size: 13px;
                font-weight: 500;
                border: none;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
        """)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        warning_header_layout.addWidget(self.refresh_button)
        
        # 智能刷新提示标签
        self.auto_refresh_label = QLabel()
        self.auto_refresh_label.setStyleSheet("""
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            color: #6c757d;
        """)
        self.auto_refresh_label.hide()  # 默认隐藏
        warning_header_layout.addWidget(self.auto_refresh_label)

        # 警告状态标签
        self.warning_status = QLabel()
        self.warning_status.setStyleSheet("""
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 500;
            margin-left: 8px;
        """)
        warning_header_layout.addWidget(self.warning_status)
        
        warning_layout.addWidget(warning_header)
        
        # 警告表格
        self.warning_table = QTableWidget()
        self.warning_table.setColumnCount(9)
        self.warning_table.setHorizontalHeaderLabels([
            '父SKU', '子SKU', '当前库存', '警告阈值', '状态',
            '今日销量', '昨日销量', '最近7天', '最近30天'
        ])
        
        # 设置表头字体大小
        header = self.warning_table.horizontalHeader()
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header.setFont(header_font)
        
        # 设置单元格间距
        self.warning_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #e5e5e5;
                border: 1px solid #e5e5e5;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
                font-size: 11pt;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                font-size: 11pt;
                border-bottom: 1px solid #e5e5e5;
            }
        """)
        self.warning_table.setAlternatingRowColors(False)
        self.warning_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.warning_table.setShowGrid(True)
        self.warning_table.verticalHeader().setVisible(False)
        
        # 加载保存的列宽
        width_manager = get_column_width_manager()
        saved_widths = width_manager.get_column_widths('dashboard_view')
        header = self.warning_table.horizontalHeader()
        
        # 设置默认列宽（9列）
        default_widths = [120, 182, 120, 120, 120, 128, 80, 103, 80]
        
        # 恢复保存的列宽或使用默认值
        if saved_widths and len(saved_widths) == 9:
            for i, width in enumerate(saved_widths):
                self.warning_table.setColumnWidth(i, width)
        else:
            for i, width in enumerate(default_widths):
                self.warning_table.setColumnWidth(i, width)
            
        # 监听列宽变化
        header.sectionResized.connect(self.on_warning_column_resized)
        
        # 设置每列的默认宽度
        header = self.warning_table.horizontalHeader()
        for i in range(self.warning_table.columnCount()):
            header.setDefaultSectionSize(120)
            
        # 设置表格样式
        self.warning_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e5e5e5;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f0f0f0;
                font-size: 13px;
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #f0f0f0;
                font-weight: 600;
                font-size: 13px;
                color: #333333;
                min-height: 35px;
            }
            QTableView::item {
                min-height: 35px;
            }
            QTableWidget::item:selected {
                background-color: #f5f5f5;
                color: #1a1a1a;
            }
        """)
        
        warning_layout.addWidget(self.warning_table)
        
        # 设置整个警告面板的样式
        warning_panel.setStyleSheet("""
            QFrame[warningPanel="true"] {
                background-color: #ffffff;
                border: 1px solid #e5e5e5;
                border-radius: 8px;
            }
        """)        # 添加到主布局
        layout.addWidget(warning_panel)
        
    def create_stats_panel(self, title: str) -> QFrame:
        """创建一个销售统计面板"""
        panel = QFrame()
        panel.setProperty("dashboard", True)
        panel.setMinimumWidth(250)  # 设置最小宽度
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        
        title_label = QLabel(title)
        title_label.setProperty("dashboardTitle", True)
        
        sales_label = QLabel()
        sales_label.setProperty("statsLabel", True)
        
        orders_label = QLabel()
        orders_label.setProperty("statsLabel", True)
        
        layout.addWidget(title_label)
        layout.addWidget(sales_label)
        layout.addWidget(orders_label)
        
        # 保存标签的引用以便更新数据
        panel.title_label = title_label
        panel.sales_label = sales_label
        panel.orders_label = orders_label
        
        # 点击处理
        panel.mousePressEvent = lambda e: self.on_panel_clicked(panel)
        
        return panel
        
    def update_stats_panel(self, panel: QFrame, stats: dict):
        """更新统计面板的数据"""
        # 兼容两种字段名: total_sales(旧) 和 total_amount(新)
        sales_amount = stats.get("total_amount", stats.get("total_sales", 0))
        orders_count = stats.get("total_orders", 0)
        
        # 更新销售金额
        panel.sales_label.setText(f'¥{sales_amount:,.2f}')
        panel.sales_label.setStyleSheet('''
            font-size: 24px;
            color: #198754;
            font-weight: bold;
        ''')
        
        # 更新订单数量
        panel.orders_label.setText(f'{orders_count} 笔订单')
        panel.orders_label.setStyleSheet('''
            font-size: 18px;
            color: #0d6efd;
        ''')
        
        # 保存统计数据以便跳转使用
        panel.stats_data = stats
        
    def on_warning_column_resized(self, column, _, new_width):
        """保存列宽到配置文件"""
        try:
            # 获取所有列的宽度
            widths = []
            for i in range(self.warning_table.columnCount()):
                widths.append(self.warning_table.columnWidth(i))
            
            # 使用统一的列宽管理器保存
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('dashboard_view', widths)
        except Exception as e:
            print(f"保存列宽配置失败: {e}")
    
    def event(self, event):
        """窗口事件过滤器：检测窗口激活/失焦"""
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.WindowActivate:
            if not self.window_has_focus:
                self.window_has_focus = True
                print("✅ 仪表盘窗口激活：恢复自动刷新")
                self.check_and_refresh()
        elif event.type() == QEvent.Type.WindowDeactivate:
            if self.window_has_focus:
                self.window_has_focus = False
                print("😴 仪表盘窗口失焦：暂停自动刷新")
        
        return super().event(event)
    
    def check_and_refresh(self):
        """轻量级询问机制：先问服务端数据是否变化"""
        if not self.window_has_focus:
            return
        
        try:
            status = dal.api_client.get_server_status()
            server_timestamp = status.get('last_change', 0)
            
            if server_timestamp > self.last_server_timestamp:
                print("🔔 仪表盘数据变化，开始刷新...")
                self.last_server_timestamp = server_timestamp
                self.load_data(trigger='smart')
            else:
                print("✅ 仪表盘数据无变化，跳过刷新")
        except Exception as e:
            print(f"⚠️ 询问服务端状态失败: {e}")

    def on_refresh_clicked(self):
        """刷新按钮点击处理（手动刷新）"""
        # 禁用按钮，显示加载中状态
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("加载中...")
        
        # 强制处理UI事件，让按钮状态立即更新
        QApplication.processEvents()
        
        # 加载数据（手动刷新）
        self.load_data(trigger='manual')
        
        # 恢复按钮状态
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("刷新")
    
    def load_data(self, trigger='auto'):
        """加载仪表盘数据（使用批量API优化）
        
        Args:
            trigger: 触发方式 ('auto'=定时器, 'manual'=手动点击, 'smart'=订单变化)
        """
        try:
            # 显示智能刷新提示
            if trigger == 'smart':
                self.show_smart_refresh_hint()
            
            # 检查缓存（1分钟内的数据直接使用）
            cached = data_cache.get('dashboard_stats')
            if cached and trigger != 'manual':  # 手动刷新时强制重新加载
                print("✅ 使用缓存的仪表盘数据")
                batch_data = cached
            else:
                # 使用批量API一次性获取所有数据（5次API调用 → 1次）
                batch_data = dal.get_batch_dashboard_data(threshold=1.0)
                # 缓存60秒（仪表盘数据更新频率高，使用较短TTL）
                data_cache.set('dashboard_stats', batch_data, ttl=60)
                refresh_type = "手动刷新" if trigger == 'manual' else "智能刷新" if trigger == 'smart' else "自动刷新"
                print(f"📥 {refresh_type}: 从服务端加载仪表盘数据并缓存")
            
            # 提取统计数据
            stats = batch_data.get('stats', {})
            today_stats = stats.get('today', {})
            yesterday_stats = stats.get('yesterday', {})
            week_stats = stats.get('week', {})
            month_stats = stats.get('month', {})
            
            # 更新销售统计面板
            self.update_stats_panel(
                self.stats_panels['today'], today_stats)
            self.update_stats_panel(
                self.stats_panels['yesterday'], yesterday_stats)
            self.update_stats_panel(
                self.stats_panels['week'], week_stats)
            self.update_stats_panel(
                self.stats_panels['month'], month_stats)
            
            # 提取库存警告
            warnings = batch_data.get('warnings', [])
            
            # 从客户端配置读取全局预警值（优先级高于服务端返回值）
            client_settings = load_settings()
            global_warning_level = client_settings.get('default_warning_level', 96)
            
            if warnings:
                self.warning_table.setRowCount(len(warnings))
                self.warning_status.setText(
                    f'发现 {len(warnings)} 个预警'
                )
                self.warning_status.setStyleSheet("""
                    background-color: #fee2e2;
                    color: #dc2626;
                    border: 1px solid #fecaca;
                """)
                
                for row, warning in enumerate(warnings):
                    # 从API返回的数据中获取销量统计
                    sales_stats = warning.get('sales_stats', {})
                    
                    # 使用客户端配置的预警值，覆盖服务端返回的值
                    # 优先使用产品自己的预警值，如果没有则使用全局配置
                    product_warning = warning.get('product_warning_level')
                    if product_warning is not None:
                        warning_level = product_warning
                    else:
                        warning_level = global_warning_level
                    
                    # 重新计算库存比例（使用客户端配置的预警值）
                    current_stock = warning['current_stock']
                    stock_ratio = (current_stock / warning_level 
                                  if warning_level > 0 else 0)
                    if warning['current_stock'] == 0:
                        status = '缺货'
                        status_color = '#fee2e2'  # 浅红色背景
                        text_color = '#dc2626'    # 红色文字
                        badge_color = '#dc2626'   # 红色角标
                    elif stock_ratio <= 0.3:
                        status = '紧缺'
                        status_color = '#fef3c7'  # 浅黄色背景
                        text_color = '#d97706'    # 橙色文字
                        badge_color = '#d97706'   # 橙色角标
                    elif stock_ratio <= 0.5:
                        status = '偏低'
                        status_color = '#f3f4f6'  # 浅灰色背景
                        text_color = '#4b5563'    # 深灰色文字
                        badge_color = '#4b5563'   # 深灰色角标
                    else:
                        status = '注意'
                        status_color = '#f0fdf4'  # 浅绿色背景
                        text_color = '#047857'    # 绿色文字
                        badge_color = '#047857'   # 绿色角标
                    
                    # 创建并设置单元格
                    # 重新排序显示的数据
                    cells = [
                        warning['parent_sku'],        # 父SKU
                        warning['variant_sku'],       # 子SKU
                        str(current_stock),           # 当前库存
                        str(warning_level),           # 使用客户端配置的预警阈值
                        status,                       # 状态
                        str(sales_stats.get('today', 0)),      # 今日销量
                        str(sales_stats.get('yesterday', 0)),  # 昨日销量
                        str(sales_stats.get('week', 0)),       # 最近7天
                        str(sales_stats.get('month', 0))       # 最近30天
                    ]
                    
                    for col, value in enumerate(cells):
                        item = QTableWidgetItem(value)
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignCenter
                        )
                        # 只对状态列应用特殊样式
                        if col == 3:  # 当前库存列
                            item.setBackground(QColor(status_color))
                            item.setForeground(QColor(text_color))
                            item.setToolTip(
                                f'库存水平: {stock_ratio:.1%}\n'
                                f'状态: {status}'
                            )
                        else:
                            item.setForeground(QColor('#1a1a1a'))
                        self.warning_table.setItem(row, col, item)
                        
            else:
                # 如果没有警告，显示友好提示
                self.warning_table.setRowCount(1)
                self.warning_status.setText('库存状态正常 ✓')
                self.warning_status.setStyleSheet("""
                    background-color: #ecfdf5;
                    color: #047857;
                    border: 1px solid #d1fae5;
                """)
                
                message = QTableWidgetItem('当前没有库存警告 ✓')
                message.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter |
                    Qt.AlignmentFlag.AlignVCenter
                )
                self.warning_table.setSpan(0, 0, 1, 6)
                self.warning_table.setItem(0, 0, message)
            
            # 恢复保存的列宽
            width_manager = get_column_width_manager()
            saved_widths = width_manager.get_column_widths('dashboard_view')
            if saved_widths:
                for i, width in enumerate(saved_widths):
                    if i < self.warning_table.columnCount():
                        self.warning_table.setColumnWidth(i, width)
            
        except Exception as e:
            print(f"加载仪表盘数据失败: {str(e)}")
            QMessageBox.warning(
                self,
                "数据加载失败",
                f"无法从服务器加载仪表盘数据:\n{str(e)}\n\n"
                "请检查网络连接和服务器状态。"
            )
        
    def on_panel_clicked(self, panel: QFrame):
        """处理点击统计面板的事件"""
        from .models import shared_state
        from datetime import datetime
        
        # 切换到销售管理标签页
        tab_widget = shared_state.main_window.tab_widget
        sales_index = tab_widget.indexOf(shared_state.main_window.sales_view)
        if sales_index >= 0:
            # 设置销售管理页面的日期范围
            sales_view = shared_state.main_window.sales_view
            stats = panel.stats_data
            
            # 处理日期: 可能是datetime对象或ISO字符串
            period = stats.get('period', {})
            start_date = period.get('start')
            end_date = period.get('end')
            
            # 转换为date对象
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date).date()
            elif hasattr(start_date, 'date'):
                start_date = start_date.date()
            
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date).date()
            elif hasattr(end_date, 'date'):
                end_date = end_date.date()
            
            # 设置日期范围并切换标签页
            if start_date and end_date:
                sales_view.set_date_range(start_date, end_date)
            
            # 切换到销售管理标签页
            tab_widget.setCurrentIndex(sales_index)
    
    def show_smart_refresh_hint(self):
        """显示智能刷新提示"""
        from PyQt6.QtCore import QTimer
        
        # 显示提示标签
        self.auto_refresh_label.setText("🔄 检测到订单变化，正在刷新...")
        self.auto_refresh_label.setStyleSheet("""
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            background-color: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        """)
        self.auto_refresh_label.show()
        
        # 2秒后隐藏提示
        QTimer.singleShot(2000, self.hide_smart_refresh_hint)
    
    def hide_smart_refresh_hint(self):
        """隐藏智能刷新提示"""
        self.auto_refresh_label.hide()