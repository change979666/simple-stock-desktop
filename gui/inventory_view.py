from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QDialog, QLabel,
    QMessageBox, QComboBox, QLineEdit,
    QHeaderView, QStyle, QFrame, QFileDialog,
    QMenu, QApplication, QTabWidget, QScrollArea
)
from PyQt6.QtGui import (
    QColor, QIcon, QFont, QKeySequence,
    QShortcut
)
from PyQt6.QtCore import Qt, QTimer, QSettings
import pandas as pd
import re

from config.settings import load_settings
from utils.type_safe import safe_get_attr


def natural_sort_key(text: str) -> list:
    """
    将字符串转换为自然排序键，用于正确排序包含数字的字符串。
    
    示例:
        - 'BD55-2' -> ['BD', 55, '-', 2, '']
        - 'BD55-10' -> ['BD', 55, '-', 10, '']
        - 'BD55-104' -> ['BD', 55, '-', 104, '']
    
    排序结果: BD55-2 < BD55-10 < BD55-104
    """
    if not text:
        return ['']
    
    # 使用正则表达式分割字符串中的数字和非数字部分
    parts = re.split(r'(\d+)', str(text))
    
    result = []
    for part in parts:
        if part.isdigit():
            # 将数字部分转换为整数，以便按数值排序
            result.append(int(part))
        else:
            # 保持非数字部分为字符串
            result.append(part)
    
    return result
from utils.operator import get_operator_info, get_operator_display
from config.column_width_manager import get_column_width_manager
from client.api_client import APIClient
from utils.async_loader import AsyncDataLoader
from gui.natural_sort_tree_item import HybridSortTreeWidgetItem


class StockAdjustmentDialog(QDialog):
    def __init__(self, variant_id, variant_sku, current_stock, parent=None):
        super().__init__(parent)
        self.variant_id = variant_id
        self.variant_sku = variant_sku
        self.current_stock = current_stock
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('库存调整')
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        
        # 显示当前信息
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QVBoxLayout(info_frame)
        
        sku_label = QLabel(f'SKU: {self.variant_sku}')
        current_stock_label = QLabel(f'当前库存: {self.current_stock}')
        for label in (sku_label, current_stock_label):
            label.setStyleSheet('font-size: 12pt;')
            info_layout.addWidget(label)
            
        layout.addWidget(info_frame)
        
        # 调整类型
        adjustment_layout = QHBoxLayout()
        adjustment_layout.addWidget(QLabel('调整类型:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['入库', '出库'])
        self.type_combo.setStyleSheet('''
            QComboBox {
                padding: 5px;
                border: 1px solid #CCC;
                border-radius: 3px;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        ''')
        adjustment_layout.addWidget(self.type_combo)
        layout.addLayout(adjustment_layout)
        
        # 数量调整
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel('调整数量:'))
        self.quantity_edit = QLineEdit()
        self.quantity_edit.setPlaceholderText('请输入数量')
        self.quantity_edit.setStyleSheet('''
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCC;
                border-radius: 4px;
                background: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        ''')
        quantity_layout.addWidget(self.quantity_edit)
        layout.addLayout(quantity_layout)
        
        # 备注
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel('备注:'))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText('输入调整原因（选填）')
        self.notes_edit.setStyleSheet('''
            QLineEdit {
                padding: 5px;
                border: 1px solid #CCC;
                border-radius: 3px;
                background: white;
            }
        ''')
        notes_layout.addWidget(self.notes_edit)
        layout.addLayout(notes_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(self.save_adjustment)
        save_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        ''')
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 15px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        ''')
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
    def save_adjustment(self):
        # 获取并验证数量输入
        quantity_text = self.quantity_edit.text().strip()
        if not quantity_text:
            QMessageBox.warning(self, '错误', '请输入调整数量！')
            return
            
        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                QMessageBox.warning(self, '错误', '调整数量必须大于0！')
                return
        except ValueError:
            QMessageBox.warning(self, '错误', '请输入有效的数字！')
            return
        
        if self.type_combo.currentText() == '出库':
            quantity = -quantity
            
        if self.current_stock + quantity < 0:
            QMessageBox.warning(self, '错误', '库存不足，无法出库！')
            return
            
        notes = self.notes_edit.text().strip()
        if not notes:
            notes = '手动' + self.type_combo.currentText()  # 默认备注
            
        try:
            # 使用DAL层调整库存
            from utils.data_access import dal
            from utils.operator import get_operator_info
            
            operator_info = get_operator_info()
            result = dal.adjust_inventory(
                sku=self.variant_sku,
                quantity=quantity,
                notes=notes,
                operator_info=operator_info
            )
            
            # 保存结果供父窗口使用
            self.adjustment_result = {
                'quantity': quantity,
                'notes': notes,
                'result': result
            }
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败: {str(e)}')


class InventoryView(QWidget):
    def __init__(self, api_client=None):
        super().__init__()
        # 初始化API客户端（统一使用客户端模式）
        self.api_client = api_client or APIClient()
        self.async_loader = AsyncDataLoader()  # 异步加载器
        
        # 🆕 添加分页状态
        self.current_page = 1
        self.page_size = 50
        self.total_items = 0
        self.total_pages = 1
        self.search_keyword = ''  # 搜索关键词
        self.global_stats_cache = None  # 全局统计缓存
        
        # 🔥 轻量级询问机制：跟踪服务端数据变更时间戳
        self.last_server_timestamp = 0  # 服务端最后变更时间
        self.window_has_focus = True  # 窗口是否激活
        
        self.init_ui()
        self.load_inventory()  # 初始加载一次数据
        
        # 自动刷新定时器（改为询问机制）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_and_refresh)
        
        # [Cache Control] 读取配置的刷新频率
        from config.settings import get_setting
        refresh_interval = get_setting('client', 'refresh_interval', 60000)
        if refresh_interval > 0:
            self.refresh_timer.start(refresh_interval)
        # 0 表示不自动刷新
        
    def on_column_resized(self, column: int, _, new_width: int):
        """保存列宽到配置文件，并确保在限制范围内"""
        # 确保新宽度在限制范围内
        width = max(
            min(new_width, self.column_max_widths[column]),
            self.column_min_widths[column]
        )
        
        # 如果宽度超出限制，重新设置为有效值
        if width != new_width:
            self.inventory_tree.setColumnWidth(column, width)
        
        # 获取所有列的宽度并保存到配置文件
        column_count = self.inventory_tree.columnCount()
        widths = []
        for i in range(column_count):
            widths.append(self.inventory_tree.columnWidth(i))
        
        # 保存到配置文件
        width_manager = get_column_width_manager()
        width_manager.save_column_widths('inventory_view', widths)
    
    def event(self, event):
        """
        窗口事件过滤器：检测窗口激活/失焦
        实现方案一：专注模式锁
        """
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.WindowActivate:
            # 窗口被激活（用户切回来了）
            if not self.window_has_focus:
                self.window_has_focus = True
                print("✅ 窗口激活：恢复自动刷新")
                # 立即触发一次检查
                self.check_and_refresh()
        
        elif event.type() == QEvent.Type.WindowDeactivate:
            # 窗口失焦（用户切走了）
            if self.window_has_focus:
                self.window_has_focus = False
                print("😴 窗口失焦：暂停自动刷新")
        
        return super().event(event)
    
    def check_and_refresh(self):
        """
        轻量级询问机制：先问服务端数据是否变化
        实现方案二：时间戳比对锁
        """
        # 第一道锁：窗口未激活时，直接跳过
        if not self.window_has_focus:
            return
        
        try:
            # 第二道锁：发送极小的询问请求（几字节）
            status = self.api_client.get_server_status()
            server_timestamp = status.get('last_change', 0)
            
            # 比对时间戳
            if server_timestamp > self.last_server_timestamp:
                # 数据有变化，执行完整刷新
                print(f"🔔 服务端数据变化：{status.get('timestamp_readable')} "
                      f"(变更#{status.get('change_count')})。开始刷新...")
                self.last_server_timestamp = server_timestamp
                self.load_inventory()
            else:
                # 无变化，不做任何操作（节省资源）
                print("✅ 数据无变化，跳过刷新")
        
        except Exception as e:
            # 如果询问失败，静默忽略（避免频繁报错）
            print(f"⚠️ 询问服务端状态失败: {e}")
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建现代化工具栏
        toolbar_container = self._create_modern_toolbar()
        layout.addWidget(toolbar_container)
        
        # 创建表格容器
        table_container = self._create_table_container()
        layout.addWidget(table_container)
    
    def _create_modern_toolbar(self):
        """创建现代化工具栏 - 白色简洁风格"""
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbarFrame")
        toolbar_frame.setStyleSheet('''
            QFrame#toolbarFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 10px;
            }
        ''')
        
        toolbar_layout = QHBoxLayout(toolbar_frame)  # 使用水平布局
        toolbar_layout.setContentsMargins(20, 12, 20, 12)
        toolbar_layout.setSpacing(12)
        
        # ===== 左侧按钮区域（两行布局）=====
        left_buttons_container = QVBoxLayout()
        left_buttons_container.setSpacing(10)
        
        # 第一行按钮
        first_row = QHBoxLayout()
        first_row.setSpacing(10)
        
        # 刷新按钮
        self.refresh_btn = QPushButton('🔄 刷新')
        self.refresh_btn.setFixedSize(115, 32)
        self.refresh_btn.clicked.connect(self.refresh_inventory)
        self.refresh_btn.setStyleSheet('''
            QPushButton {
                background-color: #52c41a;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #73d13d; }
            QPushButton:pressed { background-color: #389e0d; }
        ''')
        self.refresh_btn.setToolTip('从服务器获取最新库存数据')
        first_row.addWidget(self.refresh_btn)
        
        # 修改库存按钮
        self.edit_btn = QPushButton('✏️ 修改库存')
        self.edit_btn.setFixedSize(115, 32)
        self.edit_btn.clicked.connect(self.edit_selected_stock)
        self.edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #722ed1;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #9254de; }
            QPushButton:pressed { background-color: #531dab; }
        ''')
        first_row.addWidget(self.edit_btn)
        
        left_buttons_container.addLayout(first_row)
        
        # 第二行按钮
        second_row = QHBoxLayout()
        second_row.setSpacing(10)
        
        # 导出按钮
        self.export_btn = QPushButton('📤 导出')
        self.export_btn.setFixedSize(115, 32)
        self.export_btn.clicked.connect(self.export_inventory)
        self.export_btn.setStyleSheet('''
            QPushButton {
                background-color: #13c2c2;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #36cfc9; }
            QPushButton:pressed { background-color: #08979c; }
        ''')
        second_row.addWidget(self.export_btn)
        
        # 批量修改按钮
        self.batch_edit_btn = QPushButton('📝 批量修改')
        self.batch_edit_btn.setFixedSize(115, 32)
        self.batch_edit_btn.clicked.connect(self.batch_edit_stock)
        self.batch_edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #fa8c16;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #ffa940; }
            QPushButton:pressed { background-color: #d46b08; }
        ''')
        second_row.addWidget(self.batch_edit_btn)
        
        left_buttons_container.addLayout(second_row)
        toolbar_layout.addLayout(left_buttons_container)
        
        # 导入按钮（大按钮，占两行高度）
        self.import_btn = QPushButton('📥 导入')
        self.import_btn.setFixedSize(115, 74)  # 两行总高度 32*2 + 10间距
        self.import_btn.clicked.connect(self.import_stock)
        self.import_btn.setStyleSheet('''
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #40a9ff; }
            QPushButton:pressed { background-color: #096dd9; }
        ''')
        toolbar_layout.addWidget(self.import_btn)
        
        # 添加弹性空间
        toolbar_layout.addStretch(1)
        
        # ===== 中间统计标签区域（上下两行）=====
        stats_container = QVBoxLayout()
        stats_container.setSpacing(10)
        
        # 总库存标签
        self.total_stock_label = QLabel('📦 总库存: 57,928 件')
        self.total_stock_label.setFixedHeight(32)
        self.total_stock_label.setStyleSheet('''
            QLabel {
                color: #0958d9;
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e6f4ff, stop:1 #d6e4ff);
                border-radius: 6px;
                border: 2px solid #4096ff;
            }
        ''')
        stats_container.addWidget(self.total_stock_label)
        
        # 有货SKU标签
        self.in_stock_sku_label = QLabel('✅ 有货SKU: 359 个')
        self.in_stock_sku_label.setFixedHeight(32)
        self.in_stock_sku_label.setStyleSheet('''
            QLabel {
                color: #389e0d;
                font-size: 13px;
                font-weight: 700;
                padding: 0 14px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f6ffed, stop:1 #d9f7be);
                border-radius: 6px;
                border: 2px solid #73d13d;
            }
        ''')
        stats_container.addWidget(self.in_stock_sku_label)
        
        toolbar_layout.addLayout(stats_container)
        
        toolbar_layout.addSpacing(15)
        
        # ===== 右侧搜索框 =====
        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_container.setFixedHeight(74)  # 与导入按钮同高
        search_container.setStyleSheet('''
            QFrame#searchContainer {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 20px;
            }
            QFrame#searchContainer:hover {
                border-color: #adb5bd;
                background-color: #ffffff;
            }
        ''')
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 0, 15, 0)
        search_layout.setSpacing(10)
        
        # 搜索图标
        search_icon = QLabel('🔍')
        search_icon.setStyleSheet('color: #6c757d; font-size: 16px;')
        search_layout.addWidget(search_icon)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索产品SKU（按回车全局搜索）')
        self.search_input.returnPressed.connect(self.on_search)
        self.search_input.setStyleSheet('''
            QLineEdit {
                background: transparent;
                border: none;
                font-size: 14px;
                color: #212529;
                min-width: 200px;
            }
            QLineEdit::placeholder {
                color: #adb5bd;
                font-style: italic;
            }
        ''')
        search_layout.addWidget(self.search_input)
        
        # 清空搜索按钮
        clear_search_btn = QPushButton('✕')
        clear_search_btn.setFixedSize(28, 28)
        clear_search_btn.setToolTip('清空搜索')
        clear_search_btn.setStyleSheet('''
            QPushButton {
                background: transparent;
                border: none;
                color: #adb5bd;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff4444;
                background: rgba(255, 68, 68, 0.1);
                border-radius: 14px;
            }
        ''')
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        toolbar_layout.addWidget(search_container)
        
        return toolbar_frame
    
    def _create_table_container(self):
        """创建表格容器"""
        container = QFrame()
        container.setStyleSheet('''
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #e8e8e8;
            }
        ''')
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建库存表格
        self.inventory_tree = QTreeWidget()
        self.inventory_tree.setHeaderLabels([
            '产品/SKU', '库存', '预警', '在途库存', '状态',
            '今日销量', '昨日销量', '7天销量', '30天销量', '今年销量'
        ])
        
        # 设置表格样式
        self.inventory_tree.setStyleSheet(self._get_tree_style())
        
        # 表格配置
        self.inventory_tree.setAlternatingRowColors(True)
        self.inventory_tree.itemDoubleClicked.connect(self.show_adjustment_dialog)
        self.inventory_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # 配置快捷键和右键菜单
        copy_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self.inventory_tree)
        copy_shortcut.activated.connect(self.copy_selected_items)
        self.inventory_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.inventory_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置列宽
        self._setup_column_widths()
        
        layout.addWidget(self.inventory_tree)
        
        # 🆕 添加分页控件
        from gui.widgets.pagination import PaginationWidget
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self.on_page_changed)
        layout.addWidget(self.pagination)
        
        return container
    
    def _get_modern_button_style(self, color):
        """获取现代化按钮样式"""
        return f'''
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: {color}dd;
            }}
            QPushButton:pressed {{
                background: {color}aa;
            }}
        '''
    
    def _get_tree_style(self):
        """获取表格样式"""
        return '''
            QTreeWidget {
                border: none;
                background: white;
                alternate-background-color: #fafbfc;
                selection-background-color: #e6f7ff;
                font-size: 14px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 8px;
                border: none;
                min-height: 35px;
            }
            QTreeWidget::item:selected {
                background: linear-gradient(90deg, #e6f7ff 0%, #bae7ff 100%);
                color: #1890ff;
            }
            QTreeWidget::item:hover {
                background: #f0f8ff;
            }
            QHeaderView::section {
                background: linear-gradient(90deg, #f0f2f5 0%, #e8e8e8 100%);
                color: #333;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #d9d9d9;
                border-bottom: 2px solid #1890ff;
                font-weight: bold;
                font-size: 14px;
            }
            QHeaderView::section:hover {
                background: linear-gradient(90deg, #e8e8e8 0%, #d9d9d9 100%);
            }
        '''
    
    def _setup_column_widths(self):
        """设置列宽"""
        header = self.inventory_tree.header()
        self.column_min_widths = [120, 60, 70, 80, 80, 80, 80, 80, 80, 80]  # 10列
        self.column_max_widths = [300, 100, 120, 120, 120, 120, 120, 120, 120, 120]  # 10列
        self.column_default_widths = [253, 80, 90, 90, 120, 100, 100, 100, 89, 120]  # 10列
        
        # 使用统一的列宽配置管理器
        width_manager = get_column_width_manager()
        saved_widths = width_manager.get_column_widths('inventory_view')
        
        # 如果有保存的配置，使用保存的配置；否则使用默认值
        if saved_widths and len(saved_widths) == len(self.column_default_widths):
            for i, width in enumerate(saved_widths):
                # 确保宽度在合理范围内
                width = max(min(width, self.column_max_widths[i]),
                           self.column_min_widths[i])
                self.inventory_tree.setColumnWidth(i, width)
        else:
            # 使用默认宽度
            for i, width in enumerate(self.column_default_widths):
                self.inventory_tree.setColumnWidth(i, width)
        
        # 设置列宽调整模式
        for i in range(len(self.column_default_widths)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # 监听列宽变化
        header.sectionResized.connect(self.on_column_resized)
    
    def refresh_inventory(self):
        """刷新按钮点击时，强制清除缓存并重新加载"""
        from utils.cache import data_cache
        
        # 清除缓存，确保获取最新数据
        data_cache.invalidate('inventory_data')
        self.global_stats_cache = None  # 清除全局统计缓存
        print("🗑️ 已清除库存缓存，强制从服务端获取最新数据")
        
        # 🆕 重置到第一页
        self.current_page = 1
        
        # 重新加载数据
        self.load_inventory()
        
    def load_inventory(self):
        """加载库存数据（分页模式）"""
        # 显示加载状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText('⏳ 加载中...')
        
        # 清空库存树
        self.inventory_tree.clear()
        
        def load_data():
            """后台加载库存数据（分页）"""
            from utils.data_access import dal
            
            print(f"📄 加载第 {self.current_page} 页库存数据 (每页{self.page_size}条)...")
            
            # 🆕 使用分页API获取当前页数据
            response = dal.get_products_paginated(
                page=self.current_page,
                page_size=self.page_size,
                search=self.search_keyword if self.search_keyword else None
            )
            
            products = response['items']
            self.total_items = response['total']
            self.total_pages = response['total_pages']
            
            print(f"✅ 加载了 {len(products)} 个产品 (总计{self.total_items}个)")
            
            # 🆕 查询全部产品的统计信息（用于顶部统计标签）
            # 使用缓存，避免每次翻页都查询
            all_stats = self.global_stats_cache
            if all_stats is None or self.current_page == 1:
                try:
                    # 🚀 优化: 使用专门的统计方法，避免传输大量数据
                    # 如果有搜索关键词，则统计当前搜索结果
                    # 如果没有搜索，使用全局缓存的统计
                    if self.search_keyword:
                        # 有搜索时，只统计搜索结果（已在response中）
                        all_stats = {
                            'total_stock': 0,
                            'in_stock_count': 0
                        }
                        for prod in products:
                            variants = (prod.get('variants', [])
                                       if isinstance(prod, dict)
                                       else prod.variants)
                            for variant in variants:
                                stock = (variant.get('current_stock', 0)
                                        if isinstance(variant, dict)
                                        else variant.current_stock)
                                all_stats['total_stock'] += stock
                                if stock > 0:
                                    all_stats['in_stock_count'] += 1
                        # 搜索模式下的统计不缓存
                        self.global_stats_cache = None
                    else:
                        # 无搜索时，从DAL获取全局统计（会被缓存）
                        all_stats = dal.get_inventory_stats()
                        # 缓存全局统计数据
                        self.global_stats_cache = all_stats
                    
                    print(f"📊 统计: 总库存{all_stats['total_stock']}件, "
                          f"有货SKU {all_stats['in_stock_count']}个")
                except Exception as e:
                    print(f"⚠️ 获取统计失败: {e}")
                    all_stats = None
            else:
                print(f"✅ 使用缓存的统计数据")
            
            # 🚀 只收集当前页产品的SKU，大幅提升性能
            all_skus = []
            for product in products:
                variants = (product.get('variants', [])
                           if isinstance(product, dict)
                           else product.variants)
                for variant in variants:
                    variant_sku = (variant.get('sku')
                                  if isinstance(variant, dict)
                                  else variant.sku)
                    all_skus.append(variant_sku)
            
            print(f"📊 当前页共 {len(all_skus)} 个SKU，开始批量查询销量和在途库存...")
            
            # 批量获取销量数据（仅当前页）
            sales_data = {}
            try:
                if all_skus:
                    sales_data = self.api_client.get_batch_variant_sales_stats(
                        all_skus
                    )
                    print(f"✅ 批量获取了 {len(sales_data)} 个SKU的销量数据")
            except Exception as e:
                print(f"⚠️ 批量获取销量失败: {e}")
                for sku in all_skus:
                    sales_data[sku] = {
                        'today': 0, 'yesterday': 0,
                        'week': 0, 'month': 0, 'year': 0
                    }
            
            # 批量获取在途库存数据（仅当前页SKU）
            in_transit_data = {}
            try:
                if all_skus:
                    # 获取所有在途库存，然后筛选当前页
                    all_in_transit = dal.get_in_transit_inventory()
                    # 只保留当前页SKU的在途数据
                    in_transit_data = {
                        sku: qty for sku, qty in all_in_transit.items()
                        if sku in all_skus
                    }
                    print(f"✅ 当前页有 {len(in_transit_data)} 个SKU有在途库存")
            except Exception as e:
                print(f"⚠️ 批量获取在途库存失败: {e}")
            
            # 返回当前页数据（不再缓存全部数据，提升性能）
            inventory_data = {
                'products': products,
                'sales_data': sales_data,
                'in_transit_data': in_transit_data,
                'all_stats': all_stats  # 🆕 添加全局统计
            }
            print(f"✅ 第{self.current_page}页数据加载完成")
            return inventory_data
        
        # 启动异步加载
        self.async_loader.load_data(
            load_func=load_data,
            on_success=self._on_inventory_loaded,
            on_error=self._on_load_error
        )
    
    def _on_inventory_loaded(self, inventory_data):
        """库存数据加载成功回调（分批渲染优化）"""
        try:
            products = inventory_data['products']
            sales_data = inventory_data['sales_data']
            in_transit_data = inventory_data.get('in_transit_data', {})
            
            # 调试输出
            print(f"\n🔍 _on_inventory_loaded 调试信息:")
            print(f"   在途库存数据条数: {len(in_transit_data)}")
            if in_transit_data:
                print(f"   在途库存详情:")
                for sku, qty in sorted(in_transit_data.items())[:5]:
                    print(f"      {sku}: {qty} 件")
            else:
                print(f"   ⚠️ 在途库存数据为空！")
            
            # 从扁平格式配置获取全局预警阈值（作为默认值）
            settings = load_settings()
            warning_key = 'default_warning_level'
            global_warning_level = settings.get(warning_key, 96)
            
            # 收集所有SKU（用于后续消息显示）
            all_skus = []
            for product in products:
                variants = (product.get('variants', [])
                           if isinstance(product, dict)
                           else product.variants)
                for variant in variants:
                    variant_sku = (variant.get('sku')
                                  if isinstance(variant, dict)
                                  else variant.sku)
                    all_skus.append(variant_sku)
            
            for product in products:
                # 兼容字典和ORM对象
                if isinstance(product, dict):
                    parent_sku = product.get('parent_sku')
                    variants = product.get('variants', [])
                    product_warning_level = (
                        product.get('stock_warning_level') or
                        global_warning_level
                    )
                else:
                    parent_sku = product.parent_sku
                    variants = product.variants
                    product_warning_level = (
                        product.stock_warning_level or
                        global_warning_level
                    )
                
                # 创建父产品项
                product_item = QTreeWidgetItem([f'{parent_sku}', '', '', '', ''])
                flags = product_item.flags() & ~Qt.ItemFlag.ItemIsSelectable
                product_item.setFlags(flags)
                product_item.setBackground(0, QColor('#f8f9fa'))
                product_item.setFont(0, QFont('', -1, QFont.Weight.Bold))
                
                # 添加子SKU项（按SKU自然排序）
                variants = sorted(
                    variants,
                    key=lambda x: natural_sort_key(
                        safe_get_attr(x, 'sku', '')
                    )
                )
                for variant in variants:
                        # 兼容字典和ORM对象
                        if isinstance(variant, dict):
                            variant_id = variant['id']
                            variant_sku = variant['sku']
                            stock = variant.get('current_stock', 0)
                        else:
                            variant_id = variant.id
                            variant_sku = variant.sku
                            stock = variant.current_stock
                        
                        # 使用产品的预警值
                        warning_level = product_warning_level
                        
                        # 获取在途库存数量
                        in_transit_qty = in_transit_data.get(variant_sku, 0)
                        if in_transit_qty > 0:
                            print(f"   📦 SKU {variant_sku} 在途库存: {in_transit_qty} 件")
                        
                        # 从批量查询结果获取销售数据
                        sku_sales = sales_data.get(variant_sku, {
                            'today': 0,
                            'yesterday': 0,
                            'week': 0,
                            'month': 0,
                            'year': 0
                        })
                        sales_stats = [
                            sku_sales.get('today', 0),
                            sku_sales.get('yesterday', 0),
                            sku_sales.get('week', 0),
                            sku_sales.get('month', 0),
                            sku_sales.get('year', 0)
                        ]
                        
                        # 创建SKU项（使用智能排序）
                        variant_item = HybridSortTreeWidgetItem([
                            variant_sku,
                            str(stock),
                            str(warning_level),
                            str(in_transit_qty),
                            self.get_stock_status(stock, warning_level),
                            *map(str, sales_stats)
                        ])
                        
                        # 设置列类型和数值
                        variant_item.set_column_type(0, 'natural')  # SKU自然排序
                        variant_item.set_numeric_value(1, stock)  # 库存数量
                        variant_item.set_numeric_value(2, warning_level)  # 预警值
                        variant_item.set_numeric_value(3, in_transit_qty)  # 在途库存
                        # 销量列
                        for i, sales_val in enumerate(sales_stats, 5):
                            variant_item.set_numeric_value(i, sales_val)
                        
                        # 设置所有列为居中对齐
                        align_center = Qt.AlignmentFlag.AlignCenter
                        for i in range(0, 10):  # 所有列都居中（包括SKU列）
                            variant_item.setTextAlignment(i, align_center)
                        
                        # 设置SKU项的字体和颜色样式
                        for col in range(10):  # 更新为10列
                            font = QFont()
                            font.setPointSize(13)
                            variant_item.setFont(col, font)
                        
                        # 设置SKU编码样式
                        variant_item.setForeground(0, QColor('#595959'))
                        sku_font = QFont()
                        sku_font.setPointSize(13)
                        sku_font.setBold(True)
                        variant_item.setFont(0, sku_font)
                        
                        # 设置库存数量颜色（根据库存状态）
                        if stock <= 0:
                            stock_color = '#ff4d4f'  # 红色 - 无库存
                        elif stock <= warning_level:
                            stock_color = '#faad14'  # 橙色 - 低库存
                        else:
                            stock_color = '#52c41a'  # 绿色 - 正常库存
                            
                        variant_item.setForeground(1, QColor(stock_color))
                        stock_font = QFont()
                        stock_font.setPointSize(14)
                        stock_font.setBold(True)
                        variant_item.setFont(1, stock_font)
                        
                        # 设置预警阈值样式
                        variant_item.setForeground(2, QColor('#722ed1'))
                        
                        # 设置在途库存样式
                        if in_transit_qty > 0:
                            variant_item.setForeground(3, QColor('#1890ff'))
                            transit_font = QFont()
                            transit_font.setPointSize(13)
                            transit_font.setBold(True)
                            variant_item.setFont(3, transit_font)
                        else:
                            variant_item.setForeground(3, QColor('#d9d9d9'))
                        
                        # 设置状态样式
                        variant_item.setForeground(4, QColor(stock_color))
                        status_font = QFont()
                        status_font.setBold(True)
                        variant_item.setFont(4, status_font)
                        
                        # 设置销量数据颜色
                        colors = ['#1890ff', '#40a9ff', '#69c0ff',
                                 '#91d5ff', '#1890ff']
                        sales_colors = colors
                        for i, color in enumerate(sales_colors, 5):
                            variant_item.setForeground(i, QColor(color))
                            if sales_stats[i-5] > 0:  # 如果有销量，设置粗体
                                sales_font = QFont()
                                sales_font.setBold(True)
                                variant_item.setFont(i, sales_font)
                        
                        # 保存引用数据
                        user_role = Qt.ItemDataRole.UserRole
                        variant_item.setData(0, user_role, variant_id)
                        variant_item.setData(1, user_role, stock)
                        variant_item.setData(2, user_role, variant_sku)
                        
                        product_item.addChild(variant_item)
                
                self.inventory_tree.addTopLevelItem(product_item)
                product_item.setExpanded(True)
                    
            # 如果没有数据，显示提示信息
            if self.inventory_tree.topLevelItemCount() == 0:
                empty_item = QTreeWidgetItem(['暂无库存数据'])
                empty_item.setTextAlignment(0, Qt.AlignmentFlag.AlignCenter)
                self.inventory_tree.addTopLevelItem(empty_item)
            
            # 重新应用搜索过滤（如果有搜索文本）
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self.filter_inventory()
            
            # 在状态栏居中显示刷新成功消息
            if hasattr(self, 'refresh_btn') and self.sender() == self.refresh_btn:
                product_count = len(products)
                sku_count = len(all_skus)
                sales_count = len(sales_data)
                main_window = self.window()
                if hasattr(main_window, 'center_message_label'):
                    msg = (f'✅ 数据刷新成功 - '
                           f'{product_count} 个产品，'
                           f'{sku_count} 个SKU，'
                           f'{sales_count} 个销量数据')
                    main_window.center_message_label.setText(msg)
                    # 3秒后清除消息
                    QTimer.singleShot(
                        3000,
                        lambda: main_window.center_message_label.setText('')
                    )
            
            # 重新应用搜索过滤（如果有搜索文本）
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self.filter_inventory()
            
            # 更新统计信息（使用全局统计数据）
            all_stats = inventory_data.get('all_stats')
            if all_stats:
                self._update_statistics_from_global(all_stats)
            else:
                # 降级：使用当前页数据统计
                self._update_statistics(products, sales_data)
            
            # 🆕 更新分页控件
            if hasattr(self, 'pagination'):
                self.pagination.set_page_info(
                    current_page=self.current_page,
                    total_pages=self.total_pages,
                    total_items=self.total_items,
                    page_size=self.page_size
                )
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'渲染库存数据失败: {str(e)}')
        finally:
            # 恢复刷新按钮状态
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText('🔄 刷新')
    
    
    def on_page_changed(self, new_page: int):
        """页码切换回调"""
        print(f"📄 切换到第 {new_page} 页")
        self.current_page = new_page
        self.load_inventory()
    
    def on_search(self):
        """搜索回调：重新从后端查询匹配的数据"""
        if hasattr(self, 'search_input'):
            new_keyword = self.search_input.text().strip()
            
            # 如果搜索关键词改变，重置到第一页
            if new_keyword != self.search_keyword:
                self.search_keyword = new_keyword
                self.current_page = 1
                self.global_stats_cache = None  # 清除全局统计缓存
                
                # 搜索模式提示
                if self.search_keyword:
                    print(f"🔍 搜索: '{self.search_keyword}'")
                else:
                    print("🔄 清空搜索，恢复全部数据")
                
                self.load_inventory()
    
    def clear_search(self):
        """清空搜索框并恢复全部数据"""
        self.search_input.clear()
        self.search_keyword = ''
        self.current_page = 1
        self.global_stats_cache = None  # 清除全局统计缓存
        print("🔄 清空搜索，恢复全部数据")
        self.load_inventory()
    
    def _on_load_error(self, error_msg):
        """库存数据加载失败回调"""
        QMessageBox.critical(
            self,
            '加载失败',
            f'无法加载库存数据:\n\n{error_msg}\n\n'
            '可能原因:\n'
            '• 网络连接中断\n'
            '• 服务器未响应\n'
            '• 数据库错误\n\n'
            '请检查网络连接和服务器状态后重试'
        )
        
        # 恢复刷新按钮状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText('🔄 刷新')
    
    def _update_statistics(self, products, sales_data):
        """更新统计信息（基于当前页数据）"""
        total_stock = 0
        in_stock_count = 0
        
        for product in products:
            variants = (product.get('variants', [])
                       if isinstance(product, dict)
                       else product.variants)
            
            for variant in variants:
                # 获取库存
                if isinstance(variant, dict):
                    stock = variant.get('current_stock', 0)
                else:
                    stock = variant.current_stock
                
                total_stock += stock
                if stock > 0:
                    in_stock_count += 1
        
        # 更新标签
        if hasattr(self, 'total_stock_label'):
            self.total_stock_label.setText(f'📦 总库存: {total_stock:,} 件')
        
        if hasattr(self, 'in_stock_sku_label'):
            self.in_stock_sku_label.setText(f'✅ 有货SKU: {in_stock_count} 个')
    
    def _update_statistics_from_global(self, all_stats):
        """更新统计信息（基于全局统计数据）"""
        total_stock = all_stats.get('total_stock', 0)
        in_stock_count = all_stats.get('in_stock_count', 0)
        
        # 更新标签
        if hasattr(self, 'total_stock_label'):
            self.total_stock_label.setText(f'📦 总库存: {total_stock:,} 件')
        
        if hasattr(self, 'in_stock_sku_label'):
            self.in_stock_sku_label.setText(f'✅ 有货SKU: {in_stock_count} 个')
    
    def get_stock_status(self, stock: int, warning_level: int) -> str:
        if stock <= 0:
            return '⚠️ 无库存'
        elif stock <= warning_level:
            return '⚠️ 库存不足'
        else:
            return '✅ 正常'
    
    def edit_selected_stock(self):
        """修改选中的库存项"""
        selected_items = self.inventory_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(
                self, '提示', '请先选择要修改的库存项！'
            )
            return
        
        # 只处理第一个选中的子项
        for item in selected_items:
            if item.parent():  # 确保是子项（子SKU）
                variant_id = item.data(0, Qt.ItemDataRole.UserRole)
                current_stock = item.data(1, Qt.ItemDataRole.UserRole)
                variant_sku = item.data(2, Qt.ItemDataRole.UserRole)
                
                dialog = StockAdjustmentDialog(
                    variant_id, variant_sku, current_stock, self
                )
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # 先清除缓存
                    from utils.cache import data_cache
                    data_cache.invalidate('inventory_data')
                    data_cache.invalidate('dashboard_stats')
                    print("🗑️ 库存调整成功，已清除缓存")
                    
                    # 显示成功提示
                    if hasattr(dialog, 'adjustment_result'):
                        result = dialog.adjustment_result
                        quantity = result['quantity']
                        action_type = '入库' if quantity > 0 else '出库'
                        QMessageBox.information(
                            self,
                            '成功',
                            f'库存{action_type}成功!\n\n'
                            f'SKU: {variant_sku}\n'
                            f'变动: {quantity:+d}\n'
                            f'备注: {result["notes"]}'
                        )
                    
                    # 强制刷新
                    self.refresh_inventory()
                return  # 只处理第一个有效选择
        
        QMessageBox.information(
            self, '提示', '请选择子SKU项进行库存修改！'
        )

    def show_adjustment_dialog(self, item: QTreeWidgetItem, column: int):
        if not item.parent():  # 不处理父项点击
            return
            
        variant_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_stock = item.data(1, Qt.ItemDataRole.UserRole)
        variant_sku = item.data(2, Qt.ItemDataRole.UserRole)
        
        dialog = StockAdjustmentDialog(
            variant_id, variant_sku, current_stock, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 调整成功后清除缓存
            from utils.cache import data_cache
            data_cache.invalidate('inventory_data')
            print("🗑️ 库存调整成功，已清除缓存")
            self.load_inventory()
    
    def copy_selected_items(self):
        """复制选中的单元格内容"""
        selected_items = self.inventory_tree.selectedItems()
        if not selected_items:
            return
            
        texts = []
        for item in selected_items:
            row_texts = []
            for col in range(self.inventory_tree.columnCount()):
                row_texts.append(item.text(col))
            texts.append('\t'.join(row_texts))
            
        text = '\n'.join(texts)
        QApplication.clipboard().setText(text)
        
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        copy_action = menu.addAction("复制")
        copy_action.triggered.connect(self.copy_selected_items)
        menu.exec(self.inventory_tree.viewport().mapToGlobal(position))
        
    def filter_inventory(self):
        """已废弃：现在搜索通过后端API实现，按回车键触发搜索"""
        # 提示用户按回车搜索
        search_text = self.search_input.text().strip()
        if search_text and search_text != self.search_keyword:
            # 可以添加一个提示：按回车搜索
            pass
    


    def import_stock(self):
        """导入库存数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择库存数据文件',
            '',
            'Excel Files (*.xlsx *.xls);;CSV Files (*.csv)'
        )
        
        if not file_path:
            return
            
        try:
            # 读取Excel文件
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
            
            if df.empty:
                QMessageBox.critical(self, '导入错误', 'Excel文件为空或无法读取')
                return
            
            print(f"库存导入 - 原始列名: {list(df.columns)}")
            
            # 处理多行标题格式和标准化列名
            column_mapping = {}
            for col in df.columns:
                col_str = str(col).strip()
                
                # 处理多行标题（提取第一行作为主要标识）
                if '\n' in col_str:
                    main_part = col_str.split('\n')[0].strip()
                else:
                    main_part = col_str
                    
                # 标准化映射 - 识别SKU字段
                if main_part in ['sku', 'sku*', '子sku', '子商品编号', 'SKU']:
                    column_mapping[col] = 'sku'
                elif main_part in ['change_quantity', 'change_quantity*', 'quantity', 'quantity*', '变动数量', '数量', '库存数量', '入库数量']:
                    column_mapping[col] = 'change_quantity'
                elif main_part in ['notes', 'notes*', '备注', '备注说明']:
                    column_mapping[col] = 'notes'
                else:
                    # 保持原列名
                    column_mapping[col] = main_part
            
            # 应用列名映射
            df = df.rename(columns=column_mapping)
            print(f"库存导入 - 映射后列名: {list(df.columns)}")
            
            required_columns = ['sku', 'change_quantity']
            
            # 验证必需的列
            missing_columns = [
                col for col in required_columns
                if col not in df.columns
            ]
            if missing_columns:
                available_cols = list(df.columns)
                QMessageBox.critical(
                    self,
                    '导入错误',
                    f'Excel文件缺少必需字段: {", ".join(missing_columns)}\n\n'
                    f'可用字段: {", ".join(available_cols)}\n\n'
                    f'请确保Excel文件包含以下字段:\n'
                    f'- sku: 产品编号（或sku*）\n'
                    f'- change_quantity: 变动数量（或change_quantity*，正数=入库，负数=出库）\n\n'
                    f'可选字段:\n'
                    f'- notes: 备注说明（若不填写则自动生成）'
                )
                return
            
            # 过滤示例行（包含*的行）
            original_count = len(df)
            # 过滤sku中包含*的行
            mask = ~df['sku'].astype(str).str.contains(r'\*', na=False, regex=True)
            df = df[mask]
            
            if len(df) == 0:
                QMessageBox.warning(
                    self,
                    '导入警告',
                    '没有找到有效的库存数据，请确认Excel文件包含有效数据行'
                )
                return
                
            if len(df) < original_count:
                print(f"库存导入 - 已过滤 {original_count - len(df)} 行示例数据")
            
            # 验证必需的列（再次检查，确保过滤后仍有必需字段）
            missing_columns = [
                col for col in required_columns
                if col not in df.columns
            ]
            if missing_columns:
                QMessageBox.critical(
                    self,
                    '导入错误',
                    f'Excel文件缺少必需字段:\n\n'
                    f'缺少字段: {", ".join(missing_columns)}\n\n'
                    f'请确保Excel文件包含以下字段:\n'
                    f'- sku: 产品编号\n'
                    f'- change_quantity: 变动数量（正数=入库，负数=出库）\n\n'
                    f'可选字段:\n'
                    f'- notes: 备注说明（若不填写则自动生成）'
                )
                return
            
            # 开始导入
            from utils.data_access import dal
            from utils.operator import get_operator_info
            from gui.progress_dialog import ProgressDialog
            from PyQt6.QtWidgets import QApplication
            
            operator_info = get_operator_info()
            imported_count = 0
            errors = []
            
            # 显示进度对话框
            total_rows = len(df)
            progress = ProgressDialog(
                self,
                title="导入库存",
                message="正在导入库存调整记录,请稍候..."
            )
            progress.set_range(0, total_rows)
            progress.show()
            QApplication.processEvents()
            
            # ⚡ 性能优化：批量更新进度（每10行更新一次）
            update_interval = 10
            
            for idx, row in enumerate(df.iterrows(), 1):
                _, row = row  # 解包 (index, row)
                
                # 批量更新进度（每10行或最后一行更新）
                if idx % update_interval == 0 or idx == total_rows:
                    progress.update_progress(
                        idx, 
                        total_rows, 
                        f"处理中: {idx}/{total_rows}"
                    )
                    QApplication.processEvents()
                
                try:
                    # 获取SKU（处理字符串类型）
                    sku = str(row['sku']).strip()
                    if not sku or sku == 'nan':
                        continue
                    
                    # 获取数量（处理字符串转换，支持正负数）
                    quantity_str = str(row['change_quantity']).strip()
                    if not quantity_str or quantity_str == 'nan':
                        errors.append(f"SKU {sku} 变动数量为空")
                        continue
                        
                    try:
                        quantity = int(float(quantity_str))
                    except (ValueError, TypeError):
                        errors.append(f"SKU {sku} 变动数量无效: {quantity_str}")
                        continue
                    
                    # 允许数量为0(用于核对库存等场景)
                    # if quantity == 0:
                    #     errors.append(f"SKU {sku} 变动数量不能为0")
                    #     continue
                    
                    # 获取备注（可选）
                    notes = ""
                    if 'notes' in row and pd.notna(row['notes']):
                        notes = str(row['notes']).strip()
                    
                    if not notes:
                        notes = f'批量导入 ({operator_info.get("operator_name", "系统")})'
                    
                    # 使用DAL层调整库存
                    try:
                        dal.adjust_inventory(
                            sku=sku,
                            quantity=quantity,
                            notes=notes,
                            operator_info=operator_info
                        )
                        imported_count += 1
                    except Exception as e:
                        errors.append(f"SKU {sku}: {str(e)}")
                    
                except Exception as e:
                    sku = row.get('sku', '未知SKU')
                    errors.append(f"导入错误 - {sku}: {str(e)}")
            
            # 导入成功后清除缓存
            from utils.cache import data_cache
            data_cache.invalidate('inventory_data')
            print(f"🗑️ 导入库存成功（{imported_count}条），已清除缓存")
            
            # 完成进度对话框并自动关闭
            progress.complete(
                message=f"导入完成! 成功{imported_count}条,失败{len(errors)}条",
                auto_close_delay=1500
            )
            
            # 刷新显示
            self.load_inventory()
            
            # 显示详细结果
            message = f'成功导入 {imported_count} 条库存记录!\n'
            if errors:
                message += '\n失败记录:\n' + '\n'.join(errors[:10])  # 只显示前10条
                if len(errors) > 10:
                    message += f'\n... 还有 {len(errors)-10} 条错误'
            
            QMessageBox.information(self, '导入结果', message)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '导入错误',
                f'文件处理失败: {str(e)}'
            )

    def batch_edit_stock(self):
        """批量修改库存"""
        selected_items = self.inventory_tree.selectedItems()
        
        # 只选择子SKU项（带有variant_id的项）
        variant_items = []
        for item in selected_items:
            if item.data(0, Qt.ItemDataRole.UserRole):  # 子SKU项
                variant_items.append(item)
        
        if not variant_items:
            QMessageBox.information(
                self, 
                '提示', 
                '请选择要修改的子SKU项！\n（可按住Ctrl键多选）'
            )
            return
        
        # 获取选中的子SKU ID列表
        variant_ids = []
        for item in variant_items:
            variant_id = item.data(0, Qt.ItemDataRole.UserRole)
            if variant_id:
                variant_ids.append(variant_id)
        
        if not variant_ids:
            return
        
        # 显示批量修改对话框
        dialog = BatchStockEditDialog(variant_ids, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 批量修改成功后清除缓存
            from utils.cache import data_cache
            data_cache.invalidate('inventory_data')
            print("🗑️ 批量修改库存成功，已清除缓存")
            self.load_inventory()
    
    def export_inventory(self):
        """导出库存数据到Excel"""
        try:
            # 选择保存路径
            from datetime import datetime
            default_filename = f"库存数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出库存数据",
                default_filename,
                "Excel文件 (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # 收集所有显示的库存数据
            export_data = []
            root = self.inventory_tree.invisibleRootItem()
            
            for i in range(root.childCount()):
                product_item = root.child(i)
                parent_sku = product_item.text(0)
                
                for j in range(product_item.childCount()):
                    child_item = product_item.child(j)
                    
                    # 提取所有列数据
                    row_data = {
                        '父SKU': parent_sku,
                        '子SKU': child_item.text(0),
                        '库存': child_item.text(1),
                        '预警': child_item.text(2),
                        '在途库存': child_item.text(3),
                        '状态': child_item.text(4),
                        '今日销量': child_item.text(5),
                        '昨日销量': child_item.text(6),
                        '7天销量': child_item.text(7),
                        '30天销量': child_item.text(8),
                        '今年销量': child_item.text(9)
                    }
                    export_data.append(row_data)
            
            # 创建DataFrame并导出
            df = pd.DataFrame(export_data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            QMessageBox.information(
                self,
                '导出成功',
                f'成功导出 {len(export_data)} 条库存记录!\n\n文件位置: {file_path}'
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '导出错误',
                f'导出失败: {str(e)}'
            )


class BatchStockEditDialog(QDialog):
    """批量库存修改对话框 - 复用产品管理的批量修改样式"""
    
    def __init__(self, variant_ids, parent=None):
        super().__init__(parent)
        self.variant_ids = variant_ids
        self.individual_edit_data = []
        self.init_ui()
        self.load_variant_data()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f'批量修改库存 - 已选择 {len(self.variant_ids)} 个SKU')
        self.setMinimumSize(650, 500)
        self.resize(750, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题标签
        title_label = QLabel(f'选中了 {len(self.variant_ids)} 个SKU')
        title_label.setStyleSheet(
            'font-size: 14pt; font-weight: bold; color: #1890ff; '
            'padding: 10px; border-bottom: 2px solid #e6f7ff; '
            'background-color: #f0f9ff; margin-bottom: 10px;'
        )
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet('''
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                padding: 10px;
            }
            QTabBar::tab {
                background: #f8f9fa;
                padding: 8px 16px;
                margin: 1px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background: #007bff;
                color: white;
            }
            QTabBar::tab:hover {
                background: #e9ecef;
            }
        ''')
        
        # 批量操作标签
        batch_tab = self._create_batch_tab()
        self.tab_widget.addTab(batch_tab, '📋 批量操作')
        
        # 单独编辑标签
        individual_tab = self._create_individual_tab()
        self.tab_widget.addTab(individual_tab, '✏️ 单独编辑')
        
        layout.addWidget(self.tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton('取消')
        cancel_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 16px;
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        ''')
        cancel_btn.clicked.connect(self.reject)
        
        apply_btn = QPushButton('确认修改')
        apply_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 16px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        ''')
        apply_btn.clicked.connect(self.apply_changes)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(apply_btn)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _create_batch_tab(self):
        """创建批量操作标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 说明文本
        info_label = QLabel(
            f'对选中的 {len(self.variant_ids)} 个SKU进行批量库存调整。\n'
            '注意：批量操作将对所有选中的SKU应用相同的调整。'
        )
        info_label.setStyleSheet('''
            QLabel {
                background: #e3f2fd;
                padding: 10px;
                border-radius: 4px;
                border-left: 3px solid #2196f3;
                font-size: 10pt;
                color: #1565c0;
            }
        ''')
        layout.addWidget(info_label)
        
        # 库存调整配置
        config_frame = QFrame()
        config_frame.setStyleSheet('''
            QFrame {
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
            }
        ''')
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(10)
        
        # 调整类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel('调整类型:'))
        self.batch_type_combo = QComboBox()
        self.batch_type_combo.addItems(['入库', '出库', '设置为固定值'])
        self.batch_type_combo.setStyleSheet('''
            QComboBox {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                min-width: 120px;
            }
        ''')
        type_layout.addWidget(self.batch_type_combo)
        type_layout.addStretch()
        config_layout.addLayout(type_layout)
        
        # 数量输入
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel('数量/值:'))
        self.batch_quantity_edit = QLineEdit()
        self.batch_quantity_edit.setPlaceholderText('请输入数量或库存值')
        self.batch_quantity_edit.setStyleSheet('''
            QLineEdit {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                min-width: 150px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        ''')
        quantity_layout.addWidget(self.batch_quantity_edit)
        quantity_layout.addStretch()
        config_layout.addLayout(quantity_layout)
        
        # 备注输入
        notes_layout = QVBoxLayout()
        notes_layout.addWidget(QLabel('备注 (选填):'))
        self.batch_notes_edit = QLineEdit()
        self.batch_notes_edit.setPlaceholderText('请输入调整原因或备注')
        self.batch_notes_edit.setStyleSheet('''
            QLineEdit {
                padding: 6px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background: white;
                font-size: 12pt;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
        ''')
        notes_layout.addWidget(self.batch_notes_edit)
        config_layout.addLayout(notes_layout)
        
        layout.addWidget(config_frame)
        layout.addStretch()
        
        return widget

    def _create_individual_tab(self):
        """创建单独编辑标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明文本
        info_label = QLabel('在这里您可以单独编辑每个子SKU的内容：')
        info_label.setStyleSheet('''
            QLabel {
                background: #fff3cd;
                padding: 8px;
                border-radius: 4px;
                border-left: 3px solid #ffc107;
                font-size: 10pt;
                color: #856404;
            }
        ''')
        layout.addWidget(info_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet('''
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        ''')
        
        scroll_widget = QWidget()
        self.individual_layout = QVBoxLayout(scroll_widget)
        self.individual_layout.setSpacing(10)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        return widget

    def load_variant_data(self):
        """加载子SKU数据用于单独编辑"""
        # ✅ 使用统一的数据访问层
        from utils.data_access import dal
        
        self.individual_edit_data.clear()
        
        for variant_id in self.variant_ids:
            try:
                # 通过API获取变体信息
                variant = dal.get_variant_by_id(variant_id)
                if not variant:
                    continue
                
                # 兼容字典和ORM对象
                sku = safe_get_attr(variant, 'sku', '')
                current_stock = safe_get_attr(variant, 'current_stock', 0)
                
                # 创建编辑控件
                sku_frame = QFrame()
                sku_frame.setStyleSheet('''
                    QFrame {
                        background: #f8f9fa;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 8px;
                        margin: 2px;
                    }
                ''')
                
                sku_layout = QHBoxLayout(sku_frame)
                
                # SKU标题
                sku_title = QLabel(f'#{variant_id}: {sku}')
                sku_title.setStyleSheet('font-weight: bold; color: #007bff; min-width: 120px;')
                sku_layout.addWidget(sku_title)
                
                # 当前库存
                current_label = QLabel(f'当前: {current_stock}')
                current_label.setStyleSheet('color: #666; min-width: 60px;')
                sku_layout.addWidget(current_label)
                
                # 新库存值输入
                sku_layout.addWidget(QLabel('新值:'))
                stock_edit = QLineEdit(str(current_stock))
                stock_edit.setPlaceholderText('库存数量')
                stock_edit.setStyleSheet('''
                    QLineEdit {
                        padding: 4px;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        background: white;
                        max-width: 80px;
                    }
                    QLineEdit:focus {
                        border-color: #007bff;
                    }
                ''')
                sku_layout.addWidget(stock_edit)
                
                # 备注输入
                notes_layout = QHBoxLayout()
                notes_layout.addWidget(QLabel('备注:'))
                
                notes_edit = QLineEdit()
                notes_edit.setPlaceholderText('调整原因（选填）')
                notes_edit.setStyleSheet('''
                    QLineEdit {
                        padding: 8px;
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        background: white;
                        font-size: 11pt;
                    }
                    QLineEdit:focus {
                        border-color: #007bff;
                    }
                ''')
                notes_layout.addWidget(notes_edit)
                notes_layout.addStretch()
                sku_layout.addLayout(notes_layout)
                
                self.individual_layout.addWidget(sku_frame)
                
                # 保存控件引用
                self.individual_edit_data.append({
                    'variant_id': variant_id,
                    'variant_sku': sku,
                    'current_stock': current_stock,
                    'stock_edit': stock_edit,
                    'notes_edit': notes_edit
                })
            except Exception as e:
                print(f'加载SKU数据错误 (variant_id={variant_id}): {e}')
                continue

    def apply_changes(self):
        """应用修改"""
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index == 0:  # 批量操作
            self._apply_batch_changes()
        else:  # 单独编辑
            self._apply_individual_changes()

    def _apply_batch_changes(self):
        """应用批量修改"""
        try:
            # 获取输入值
            adjustment_type = self.batch_type_combo.currentText()
            quantity_text = self.batch_quantity_edit.text().strip()
            notes = self.batch_notes_edit.text().strip()
            
            if not quantity_text:
                QMessageBox.warning(self, '错误', '请输入数量或库存值！')
                return
            
            try:
                quantity_value = int(quantity_text)
            except ValueError:
                QMessageBox.warning(self, '错误', '请输入有效的数字！')
                return
            
            if quantity_value < 0:
                QMessageBox.warning(self, '错误', '数量不能为负数！')
                return
            
            # ✅ 使用统一的数据访问层（支持客户端/服务端模式）
            from utils.data_access import dal
            
            operator_info = get_operator_info()
            success_count = 0
            failed_count = 0
            failed_skus = []
            
            # 批量修改所有选中的SKU
            for variant_id in self.variant_ids:
                try:
                    # 1. 获取变体信息
                    variant = dal.get_variant_by_id(variant_id)
                    if not variant:
                        failed_count += 1
                        failed_skus.append(f'ID:{variant_id} (未找到)')
                        continue
                    
                    sku = safe_get_attr(variant, 'sku', '')
                    current_stock = safe_get_attr(variant, 'current_stock', 0)
                    
                    # 2. 计算变化量
                    if adjustment_type == '入库':
                        change_quantity = quantity_value
                        final_notes = notes or f'批量入库 {quantity_value} 件'
                    elif adjustment_type == '出库':
                        # 检查库存是否充足
                        if current_stock < quantity_value:
                            failed_count += 1
                            failed_skus.append(f'{sku} (当前: {current_stock}, 需要: {quantity_value})')
                            continue
                        change_quantity = -quantity_value
                        final_notes = notes or f'批量出库 {quantity_value} 件'
                    else:  # 设置为固定值
                        change_quantity = quantity_value - current_stock
                        
                        # 检查设置固定值时，如果需要减少库存，是否充足
                        if change_quantity < 0 and current_stock < abs(change_quantity):
                            failed_count += 1
                            failed_skus.append(f'{sku} (当前: {current_stock}, 需设置: {quantity_value})')
                            continue
                        
                        final_notes = notes or f'设置库存为 {quantity_value}'
                    
                    # 3. 通过API调整库存（自动处理客户端/本地模式）
                    dal.adjust_inventory(sku, change_quantity, final_notes, operator_info)
                    success_count += 1
                    
                except Exception as e:
                    print(f'批量修改库存错误 (variant_id={variant_id}): {e}')
                    failed_count += 1
                    # 尝试获取SKU显示
                    try:
                        variant = dal.get_variant_by_id(variant_id)
                        sku = safe_get_attr(variant, 'sku', '')
                        failed_skus.append(f'{sku} (错误: {str(e)})')
                    except:
                        failed_skus.append(f'ID:{variant_id} (错误: {str(e)})')
                    continue
            
            # 清除缓存
            if success_count > 0:
                from utils.cache import data_cache
                data_cache.invalidate('inventory_data')
                data_cache.invalidate('dashboard_stats')
            
            # 显示结果
            result_msg = f'成功修改了 {success_count} 个SKU的库存！'
            
            if failed_count > 0:
                result_msg += f'\n\n失败 {failed_count} 个SKU'
                if failed_skus and len(failed_skus) <= 10:
                    result_msg += ':\n' + '\n'.join(failed_skus)
                elif failed_skus:
                    result_msg += ':\n' + '\n'.join(failed_skus[:10])
                    result_msg += f'\n... 还有 {len(failed_skus) - 10} 个'
            
            if failed_count > 0:
                QMessageBox.warning(self, '部分修改完成', result_msg)
            else:
                QMessageBox.information(self, '修改完成', result_msg)
            
            self.accept()
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f'批量修改错误:\n{error_detail}')
            QMessageBox.critical(
                self,
                '修改失败',
                f'批量修改时发生错误:\n{str(e)}\n\n请查看日志获取详细信息'
            )

    def _apply_individual_changes(self):
        """应用单独修改"""
        try:
            # ✅ 使用统一的数据访问层
            from utils.data_access import dal
            
            operator_info = get_operator_info()
            success_count = 0
            
            for data in self.individual_edit_data:
                try:
                    variant_sku = data['variant_sku']
                    current_stock = data['current_stock']
                    new_stock_text = data['stock_edit'].text().strip()
                    notes = data['notes_edit'].text().strip()
                    
                    if not new_stock_text:
                        continue
                    
                    try:
                        new_stock = int(new_stock_text)
                    except ValueError:
                        continue
                    
                    if new_stock < 0:
                        continue
                    
                    # 计算变化量
                    change_quantity = new_stock - current_stock
                    
                    if change_quantity == 0:
                        continue  # 无变化，跳过
                    
                    # 通过API调整库存
                    final_notes = notes or f'单独调整库存: {variant_sku}'
                    dal.adjust_inventory(variant_sku, change_quantity, final_notes, operator_info)
                    success_count += 1
                    
                except Exception as e:
                    print(f'单独修改库存错误 ({variant_sku}): {e}')
                    continue
            
            QMessageBox.information(
                self,
                '修改完成',
                f'成功修改了 {success_count} 个SKU的库存！'
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '修改失败',
                f'单独修改时发生错误: {str(e)}'
            )