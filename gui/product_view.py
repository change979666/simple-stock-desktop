from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QDialog, QLabel,
    QLineEdit, QMessageBox, QFrame,
    QHeaderView, QFileDialog, QCheckBox, QComboBox, QTextEdit,
    QFormLayout, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
import csv
import re

from config.column_width_manager import get_column_width_manager
from config.product_options import (
    standardize_option_name,
    get_sort_key
)
from utils.async_loader import AsyncDataLoader
from gui.natural_sort_tree_item import HybridSortTreeWidgetItem
from utils.type_safe import safe_get_attr
from PyQt6.QtCore import QEvent


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


class ProductView(QWidget):
    def __init__(self):
        super().__init__()
        self.async_loader = AsyncDataLoader()  # 异步加载器
        self.last_server_timestamp = 0  # 服务端最后变更时间戳
        self.window_has_focus = True  # 窗口焦点状态
        self.init_ui()
        self.load_products()
        
        # 启动轻量级询问定时器(60秒)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_and_refresh)
        self.refresh_timer.start(60000)

    def init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = self._create_toolbar()
        layout.addLayout(toolbar)
        
        # 产品列表容器
        tree_container = self._create_tree_container()
        layout.addWidget(tree_container)
        
        # 设置现代化样式
        self.setStyleSheet(self._get_modern_style())
        
        # 设置布局间距和边距 - 减小空白
        layout.setSpacing(6)  # 进一步减小组件间距
        layout.setContentsMargins(8, 8, 8, 8)  # 减小外边距
        
        # 设置树形视图的属性
        self._setup_tree_properties()

    def _create_tree_container(self):
        """创建现代化的树形视图容器"""
        container = QFrame()
        container.setObjectName("treeContainer")
        container.setStyleSheet("""
            QFrame#treeContainer {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 0px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建产品树
        self.product_tree = self._create_product_tree()
        layout.addWidget(self.product_tree)
        
        return container

    def _setup_tree_properties(self):
        """设置树形视图属性"""
        header = self.product_tree.header()
        header.setStretchLastSection(False)
        
        # 设置各列宽度比例为可交互
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # 尝试加载保存的列宽
        width_manager = get_column_width_manager()
        saved_widths_list = width_manager.get_column_widths('product_view')
        
        # 设置初始列宽
        total_width = self.product_tree.width()
        default_widths_list = [
            int(total_width * 0.15),  # parent_sku
            int(total_width * 0.35),  # child_sku
            int(total_width * 0.35),  # spec
            int(total_width * 0.15)   # price
        ]
        
        # 使用保存的列宽或默认值
        if saved_widths_list and len(saved_widths_list) == 4:
            widths = saved_widths_list
        else:
            widths = default_widths_list
            
        # 设置列宽和对齐方式
        alignments = [
            Qt.AlignmentFlag.AlignLeft,
            Qt.AlignmentFlag.AlignCenter,
            Qt.AlignmentFlag.AlignCenter,
            Qt.AlignmentFlag.AlignCenter,
        ]
        
        for i, (width, align) in enumerate(zip(widths, alignments)):
            self.product_tree.setColumnWidth(i, width)
            self.product_tree.headerItem().setTextAlignment(i, align)
            
        # 连接列宽变更信号
        header.sectionResized.connect(self._on_column_resized)

    def _get_modern_style(self):
        """获取现代化样式"""
        return """
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* 按钮样式 */
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #d1d9e6;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 500;
                color: #495057;
                min-height: 16px;
            }
            
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #b8c5d6;
            }
            
            QPushButton:pressed {
                background-color: #e9ecef;
            }
            
            QPushButton[success="true"] {
                background-color: #28a745;
                border-color: #28a745;
                color: white;
            }
            
            QPushButton[success="true"]:hover {
                background-color: #218838;
                border-color: #1e7e34;
            }
            
            QPushButton[primary="true"] {
                background-color: #007bff;
                border-color: #007bff;
                color: white;
            }
            
            QPushButton[primary="true"]:hover {
                background-color: #0069d9;
                border-color: #0062cc;
            }
            
            QPushButton[danger="true"] {
                background-color: #dc3545;
                border-color: #dc3545;
                color: white;
            }
            
            QPushButton[danger="true"]:hover {
                background-color: #c82333;
                border-color: #bd2130;
            }
            
            /* 搜索框样式 */
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #d1d9e6;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #495057;
                selection-background-color: #007bff;
            }
            
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QLineEdit::placeholder {
                color: #6c757d;
                font-style: italic;
            }
            
            /* 标签样式 */
            QLabel {
                color: #495057;
                font-size: 13px;
            }
        """
        header = self.product_tree.header()
        header.setStretchLastSection(False)
        
        # 获取树形视图的总宽度
        total_width = self.product_tree.width()
        
        # 设置各列宽度比例为可交互
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # 尝试加载保存的列宽
        width_manager = get_column_width_manager()
        saved_widths_list = width_manager.get_column_widths('product_view')
        
        # 设置初始列宽
        default_widths_list = [
            int(total_width * 0.15),  # 父SKU列
            int(total_width * 0.35),  # 子SKU列
            int(total_width * 0.35),  # 规格列
            int(total_width * 0.15)   # 价格列
        ]
        
        # 使用保存的列宽或默认值
        if saved_widths_list and len(saved_widths_list) == 4:
            widths = saved_widths_list
        else:
            widths = default_widths_list
            
        # 设置列宽和对齐方式
        alignments = [
            Qt.AlignmentFlag.AlignLeft,  # 父SKU左对齐
            Qt.AlignmentFlag.AlignCenter,  # 子SKU居中
            Qt.AlignmentFlag.AlignCenter,  # 规格居中
            Qt.AlignmentFlag.AlignCenter,  # 价格居中
        ]
        
        for i, (width, align) in enumerate(zip(widths, alignments)):
            self.product_tree.setColumnWidth(i, width)
            self.product_tree.headerItem().setTextAlignment(i, align)
            
        # 连接列宽变更信号
        header.sectionResized.connect(self._on_column_resized)

    def _create_toolbar(self):
        """创建现代化工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("toolbarFrame")
        toolbar_frame.setStyleSheet("""
            QFrame#toolbarFrame {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 8px;
                margin: 2px 0;
            }
        """)
        
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setSpacing(6)  # 减小按钮间距
        toolbar.setContentsMargins(4, 2, 4, 2)

        # 左侧操作按钮组
        left_buttons = QHBoxLayout()
        left_buttons.setSpacing(4)  # 减小按钮间距

        # 刷新按钮
        self.refresh_btn = QPushButton('🔄 刷新')
        self.refresh_btn.clicked.connect(self.load_products)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #52c41a, stop:1 #389e0d);
                border: none;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #73d13d, stop:1 #52c41a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #389e0d, stop:1 #237804);
            }
        """)
        left_buttons.addWidget(self.refresh_btn)

        # 导入按钮
        self.import_btn = QPushButton('📁 导入')
        self.import_btn.clicked.connect(self.import_products)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1890ff, stop:1 #0050b3);
                border: none;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #40a9ff, stop:1 #1890ff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0050b3, stop:1 #003a8c);
            }
        """)
        left_buttons.addWidget(self.import_btn)
        
        # 修改按钮
        self.batch_edit_btn = QPushButton('✏️ 修改')
        self.batch_edit_btn.clicked.connect(self.batch_edit_variants)
        self.batch_edit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #722ed1, stop:1 #531dab);
                border: none;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9254de, stop:1 #722ed1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #531dab, stop:1 #391085);
            }
        """)
        left_buttons.addWidget(self.batch_edit_btn)

        # 删除按钮
        self.delete_btn = QPushButton('🗑️ 删除')
        self.delete_btn.clicked.connect(self.batch_delete_variants)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff4d4f, stop:1 #cf1322);
                border: none;
                color: white;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff7875, stop:1 #ff4d4f);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #cf1322, stop:1 #a8071a);
            }
            QPushButton:disabled {
                background: #d9d9d9;
                color: #8c8c8c;
            }
        """)
        left_buttons.addWidget(self.delete_btn)

        toolbar.addLayout(left_buttons)
        
        # 中间统计信息
        # 产品数量标签
        self.product_count_label = QLabel('📦 产品: 0 个')
        self.product_count_label.setStyleSheet("""
            QLabel {
                color: #1890ff;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 12px;
                background-color: #e6f7ff;
                border-radius: 6px;
                border: 1px solid #91d5ff;
            }
        """)
        toolbar.addWidget(self.product_count_label)
        
        # 子SKU数量标签
        self.sku_count_label = QLabel('🏷️ 子SKU: 0 个')
        self.sku_count_label.setStyleSheet("""
            QLabel {
                color: #52c41a;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 12px;
                background-color: #f6ffed;
                border-radius: 6px;
                border: 1px solid #b7eb8f;
            }
        """)
        toolbar.addWidget(self.sku_count_label)
        
        toolbar.addStretch()

        # 右侧搜索区域 - 现代化设计
        search_container = QFrame()
        search_container.setObjectName("searchContainer")
        search_container.setStyleSheet("""
            QFrame#searchContainer {
                background-color: #ffffff;
                border: 2px solid #e1e5e9;
                border-radius: 20px;
                padding: 2px 12px;
            }
            QFrame#searchContainer:focus-within {
                border: 2px solid #1890ff;
                background-color: #f6f8fa;
            }
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(6)
        
        # 搜索图标
        search_icon = QLabel('🔍')
        search_icon.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 14px;
            }
        """)
        search_layout.addWidget(search_icon)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索产品SKU或规格...')
        self.search_input.textChanged.connect(self.filter_products)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                padding: 6px 4px;
                font-size: 13px;
                color: #333333;
                min-width: 200px;
            }
            QLineEdit::placeholder {
                color: #999999;
                font-style: italic;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        toolbar.addWidget(search_container)
        
        # 返回整个工具栏容器而不是布局
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(toolbar_frame)
        
        return container_layout

    def batch_delete_variants(self):
        """批量删除选中的子SKU和父产品 - 使用DAL层"""
        selected_items = self.product_tree.selectedItems()
        variant_ids = []
        product_ids = []
        
        for item in selected_items:
            if not item.parent():  # 父项
                product_id = item.data(0, Qt.ItemDataRole.UserRole)
                if product_id:
                    product_ids.append(product_id)
            elif item.text(1):  # 子SKU项
                variant_id = item.data(0, Qt.ItemDataRole.UserRole)
                if variant_id:
                    variant_ids.append(variant_id)
        
        if not variant_ids and not product_ids:
            QMessageBox.information(self, '提示', '请先选择要删除的产品或子SKU！')
            return
            
        msg = []
        if product_ids:
            msg.append(f'{len(product_ids)} 个产品')
        if variant_ids:
            msg.append(f'{len(variant_ids)} 个子SKU')
        
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除选中的{" 和 ".join(msg)}吗？此操作不可恢复！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            from utils.data_access import dal
            from utils.operator import get_operator_info
            
            operator_info = get_operator_info()
            deleted_products = 0
            deleted_variants = 0
            
            try:
                # 删除父产品
                for product_id in product_ids:
                    try:
                        dal.delete_product(product_id, operator_info)
                        deleted_products += 1
                    except Exception as e:
                        print(f'删除产品失败: {e}')
                
                # 删除子SKU
                for variant_id in variant_ids:
                    try:
                        dal.delete_variant(variant_id, operator_info)
                        deleted_variants += 1
                    except Exception as e:
                        print(f'删除变体失败: {e}')
                
                # 清除产品缓存
                from utils.cache import data_cache
                data_cache.invalidate('products_list_full')
                
                self.load_products()
                
                # 记录操作日志
                if deleted_products > 0 or deleted_variants > 0:
                    log_details = []
                    if deleted_products:
                        log_details.append(f'删除产品 {deleted_products} 个')
                    if deleted_variants:
                        log_details.append(f'删除子SKU {deleted_variants} 个')
                    
                    dal.create_action_log(
                        action='delete_product',
                        details=', '.join(log_details),
                        operator_info=operator_info
                    )
                
                # 显示删除结果
                result_msg = []
                if deleted_products:
                    result_msg.append(f'{deleted_products} 个产品')
                if deleted_variants:
                    result_msg.append(f'{deleted_variants} 个子SKU')
                
                QMessageBox.information(
                    self,
                    '删除成功',
                    f'已删除 {" 和 ".join(result_msg)}'
                )
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除操作失败: {str(e)}')

    def _clear_variant_stock(self, db, variant_id):
        """清空指定子SKU的所有库存记录"""
        try:
            from database.models import StockLog
            # 删除该子SKU的所有库存记录
            db.query(StockLog).filter(
                StockLog.variant_id == variant_id
            ).delete()
        except Exception as e:
            print(f"清空库存记录时出错: {str(e)}")

    def _create_product_tree(self):
        """创建现代化产品树形视图"""
        tree = QTreeWidget()
        tree.setHeaderLabels(['父SKU', '子SKU', '规格选项', '成本价'])
        
        # 支持多选
        tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # 现代化样式
        tree.setStyleSheet('''
            QTreeWidget {
                border: none;
                background-color: transparent;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
                outline: none;
                show-decoration-selected: 1;
            }
            
            QTreeWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f1f3f4;
                background-color: #ffffff;
                margin: 1px 0;
                border-radius: 6px;
            }
            
            QTreeWidget::item:hover {
                background-color: #f8f9ff;
                border: 1px solid #e6f7ff;
            }
            
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e6f7ff, stop:1 #bae7ff);
                border: 1px solid #91d5ff;
                color: #003a8c;
                font-weight: 500;
            }
            
            QTreeWidget::item:selected:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #bae7ff, stop:1 #91d5ff);
            }
            
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fafbfc, stop:1 #f1f3f4);
                border: none;
                border-right: 1px solid #e8eaed;
                border-bottom: 2px solid #e8eaed;
                padding: 12px 8px;
                font-weight: 600;
                font-size: 13px;
                color: #5f6368;
                text-align: center;
            }
            
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
            }
            
            QTreeWidget::branch {
                background: transparent;
            }
            
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
                image: none;
                background: transparent;
            }
            
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
                image: none;
                background: transparent;
            }
            
            QTreeWidget::branch:has-children:!has-siblings:closed:hover,
            QTreeWidget::branch:closed:has-children:has-siblings:hover {
                background: #f5f5f5;
            }
            
            /* 滚动条样式 */
            QScrollBar:vertical {
                background: #f5f5f5;
                width: 12px;
                border-radius: 6px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #a8a8a8;
            }
            
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        ''')
        
        tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # 设置行高
        tree.setIndentation(20)
        tree.setRootIsDecorated(True)
        tree.setAlternatingRowColors(False)
        
        return tree



    def _on_column_resized(self, column: int, _: int, width: int):
        """列宽改变时保存新的宽度配置"""
        try:
            # 获取所有列的宽度
            widths = []
            for i in range(self.product_tree.columnCount()):
                widths.append(self.product_tree.columnWidth(i))
            
            # 使用统一的列宽管理器保存
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('product_view', widths)
        except Exception as e:
            print(f"保存列宽配置失败: {e}")

    def event(self, event):
        """捕获窗口焦点事件"""
        if event.type() == QEvent.Type.WindowActivate:
            self.window_has_focus = True
            print("✅ 产品视图窗口激活：恢复自动刷新")
        elif event.type() == QEvent.Type.WindowDeactivate:
            self.window_has_focus = False
            print("😴 产品视图窗口失焦：暂停自动刷新")
        return super().event(event)

    def check_and_refresh(self):
        """轻量级询问机制：先问服务器数据是否变化"""
        if not self.window_has_focus:
            print("⏸️ 产品视图窗口未激活，跳过刷新")
            return
        
        try:
            from client.api_client import api_client
            status = api_client.get_server_status()
            
            if status and 'last_change' in status:
                server_timestamp = status['last_change']
                
                if server_timestamp > self.last_server_timestamp:
                    print(f"🔄 检测到数据变化，刷新产品列表 (服务端: {server_timestamp})")
                    self.last_server_timestamp = server_timestamp
                    self.load_products()
                else:
                    print("✅ 产品数据无变化，跳过刷新")
            else:
                print("⚠️ 无法获取服务器状态，跳过刷新")
                
        except Exception as e:
            print(f"❌ 检查服务器状态失败: {e}")

    def load_products(self):
        """加载所有产品到树形视图（异步加载优化）"""
        # 显示加载状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText('⏳ 加载中...')
        
        # 清空产品树
        self.product_tree.clear()
        
        # 使用异步加载
        from utils.cache import data_cache
        from utils.data_access import dal
        
        def load_data():
            """后台加载产品数据（获取全部产品）"""
            # 尝试从缓存获取
            cached_products = data_cache.get('products_list_full')
            if cached_products:
                print("✅ 使用缓存的完整产品数据")
                return cached_products
            else:
                # 缓存未命中，从服务端获取全部产品
                # 使用 DAL 的 get_all_products 方法（已优化为循环分页）
                products = dal.get_all_products()
                # 保存到缓存(10分钟TTL)
                data_cache.set('products_list_full', products, ttl=600)
                print(f"📥 从服务端加载了 {len(products)} 个产品并缓存")
                return products
        
        # 启动异步加载
        self.async_loader.load_data(
            load_func=load_data,
            on_success=self._on_products_loaded,
            on_error=self._on_load_error
        )
    
    def _on_products_loaded(self, products):
        """产品数据加载成功回调"""
        try:
            # 帮助函数:支持字典和对象两种数据格式
            def get_attr(obj, attr, default=""):
                if isinstance(obj, dict):
                    return obj.get(attr, default)
                return getattr(obj, attr, default)
            
            # 设置列对齐方式
            header_alignments = [
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter,
                Qt.AlignmentFlag.AlignCenter
            ]
            
            for i, align in enumerate(header_alignments):
                self.product_tree.headerItem().setTextAlignment(i, align)
            
            # 排序产品（使用自然排序）
            products = sorted(
                products,
                key=lambda x: natural_sort_key(get_attr(x, 'parent_sku', ''))
            )

            for product in products:
                # 创建父产品项 - 去掉图标
                parent_text = get_attr(product, 'parent_sku')
                
                product_item = QTreeWidgetItem([
                    parent_text, '', '', ''
                ])
                
                # 设置父项数据和样式
                product_item.setData(0, Qt.ItemDataRole.UserRole, get_attr(product, 'id'))
                
                # 父项使用渐变背景和加粗字体
                parent_font = QFont()
                parent_font.setWeight(QFont.Weight.Bold)
                parent_font.setPointSize(13)
                
                for col in range(4):
                    product_item.setFont(col, parent_font)
                    product_item.setBackground(col, QColor('#f8f9ff'))
                    product_item.setForeground(col, QColor('#1a73e8'))

                # 子SKU按规格选项排序
                variants = sorted(
                    get_attr(product, 'variants', []),
                    key=lambda x: get_sort_key(get_attr(x, 'option_name', ''))
                )
                
                for i, variant in enumerate(variants):
                    # 去掉图标，使用简洁显示
                    cost_price = get_attr(variant, 'cost_price', 0)
                    # 确保cost_price不是None
                    if cost_price is None:
                        cost_price = 0
                    price_text = f"¥{cost_price:.2f}"
                    
                    # 使用智能排序树形项
                    variant_item = HybridSortTreeWidgetItem([
                        '',
                        get_attr(variant, 'sku', ''),
                        get_attr(variant, 'option_name', ''),
                        price_text
                    ])
                    
                    # 设置列类型：SKU使用自然排序，价格使用数值排序
                    variant_item.set_column_type(1, 'natural')  # SKU列
                    variant_item.set_numeric_value(3, cost_price)  # 价格列
                    
                    variant_item.setData(
                        0, Qt.ItemDataRole.UserRole, get_attr(variant, 'id')
                    )
                    
                    # 设置子项样式
                    variant_font = QFont()
                    variant_font.setPointSize(12)
                    
                    # 设置列对齐方式和颜色
                    alignments = [
                        Qt.AlignmentFlag.AlignLeft,
                        Qt.AlignmentFlag.AlignCenter,
                        Qt.AlignmentFlag.AlignCenter,
                        Qt.AlignmentFlag.AlignCenter,
                    ]
                    
                    colors = [
                        QColor('#333333'),  # 空列
                        QColor('#1890ff'),  # SKU蓝色
                        QColor('#52c41a'),  # 规格绿色
                        QColor('#fa541c'),  # 价格橙色
                    ]
                    
                    for col, (align, color) in enumerate(
                        zip(alignments, colors)
                    ):
                        variant_item.setTextAlignment(col, align)
                        variant_item.setForeground(col, color)
                        variant_item.setFont(col, variant_font)
                        variant_item.setBackground(col, QColor('#ffffff'))
                    
                    # 添加轻微的行间距效果
                    if i % 2 == 1:
                        for col in range(4):
                            variant_item.setBackground(col, QColor('#fafafa'))
                    
                    # 添加变体到父产品
                    product_item.addChild(variant_item)
                
                # 添加父产品到树形视图(在循环外面)
                self.product_tree.addTopLevelItem(product_item)
                product_item.setExpanded(True)
                    
            # 设置树形视图的美化属性
            self.product_tree.setAlternatingRowColors(False)
            self.product_tree.setIndentation(24)
            self.product_tree.setAnimated(True)
            self.product_tree.setSortingEnabled(False)
            
            # 设置默认列宽
            self.product_tree.setColumnWidth(0, 200)
            self.product_tree.setColumnWidth(1, 180)
            self.product_tree.setColumnWidth(2, 160)
            self.product_tree.setColumnWidth(3, 120)
            
            # 展开所有项目
            self.product_tree.expandAll()
            
            # 重新应用搜索过滤（如果有搜索文本）
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self.filter_products()
            
            # 在状态栏居中显示刷新成功消息
            if hasattr(self, 'refresh_btn') and self.sender() == self.refresh_btn:
                main_window = self.window()
                if hasattr(main_window, 'center_message_label'):
                    main_window.center_message_label.setText(
                        f'✅ 产品列表刷新成功，已加载 {len(products)} 个产品'
                    )
                    # 3秒后清除消息
                    QTimer.singleShot(3000, lambda: main_window.center_message_label.setText(''))
            
            # 重新应用搜索过滤（如果有搜索文本）
            if hasattr(self, 'search_input') and self.search_input.text().strip():
                self.filter_products()
            
            # 更新统计信息
            self._update_statistics(products)
                
        finally:
            # 恢复刷新按钮状态
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText('🔄 刷新')
    
    def _update_statistics(self, products):
        """更新统计信息"""
        product_count = len(products)
        sku_count = 0
        
        # 计算所有子SKU数量
        for product in products:
            if isinstance(product, dict):
                variants = product.get('variants', [])
            else:
                variants = product.variants
            sku_count += len(variants)
        
        # 更新标签
        if hasattr(self, 'product_count_label'):
            self.product_count_label.setText(f'📦 产品: {product_count} 个')
        
        if hasattr(self, 'sku_count_label'):
            self.sku_count_label.setText(f'🏷️ 子SKU: {sku_count} 个')
    
    def _on_load_error(self, error_msg):
        """产品数据加载失败回调"""
        QMessageBox.critical(
            self,
            '加载失败',
            f'无法加载产品列表:\n\n{error_msg}\n\n'
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

    def _update_stats_widget(self):
        """更新统计信息显示"""
        try:
            # 这里可以添加动态更新统计信息的逻辑
            # 暂时保持静态显示，避免频繁数据库查询
            pass
        except Exception as e:
            print(f"更新统计信息失败: {e}")

    def filter_products(self):
        """根据搜索框内容过滤产品列表"""
        search_text = self.search_input.text().lower()
        
        def filter_item(item: QTreeWidgetItem):
            if not item.parent():  # 父项（产品）
                # 检查产品名称和父SKU
                parent_text = item.text(0).lower()
                if search_text in parent_text:
                    item.setHidden(False)
                    for i in range(item.childCount()):
                        item.child(i).setHidden(False)
                    return
                
                # 检查子项
                show_parent = False
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_text = child.text(1).lower()  # 检查子SKU
                    option_text = child.text(2).lower()  # 检查规格选项
                    if search_text in child_text or search_text in option_text:
                        child.setHidden(False)
                        show_parent = True
                    else:
                        child.setHidden(True)
                item.setHidden(not show_parent)
        
        for i in range(self.product_tree.topLevelItemCount()):
            filter_item(self.product_tree.topLevelItem(i))

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """处理项目双击事件：仅支持子SKU编辑"""
        if item.parent():
            # 只有子SKU支持双击修改
            self.edit_variant_dialog(item)

    def edit_variant_dialog(self, item: QTreeWidgetItem):
        """弹出编辑子SKU对话框 - 使用DAL层"""
        from utils.data_access import dal
        from utils.operator import get_operator_info
        from config.product_options import standardize_option_name
        
        # 使用DAL层获取变体 - 添加异常保护
        try:
            variant = dal.get_variant_by_sku(item.text(1))
            if not variant:
                QMessageBox.warning(self, '错误', '未找到该SKU')
                return
        except Exception as e:
            QMessageBox.critical(
                self,
                '加载失败',
                f'无法获取SKU数据:\n\n{str(e)}\n\n'
                '可能原因:\n'
                '• 网络连接中断\n'
                '• 服务器未响应\n'
                '• 数据已被删除\n\n'
                '请检查网络连接后重试'
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('编辑子SKU')
        dialog.setMinimumWidth(480)
        dialog.setMinimumHeight(320)
        
        # 主布局
        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # 获取变体数据（兼容字典和对象）
        current_sku = safe_get_attr(variant, 'sku', '')
        # 优先使用 option_name，兼容旧的 option1_value
        current_option = safe_get_attr(variant, 'option_name', '')
        if not current_option:
            current_option = safe_get_attr(variant, 'option1_value', '')
        current_cost = safe_get_attr(variant, 'cost_price', 0)
        variant_id = safe_get_attr(variant, 'id')

        # 表单区域
        form_widget = QWidget()
        form_widget.setStyleSheet('''
            QWidget {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        ''')
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(18)
        
        # 子SKU输入
        sku_label = QLabel('子SKU')
        sku_label.setStyleSheet('''
            QLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #495057;
                margin-bottom: 4px;
                border: none;
                background: none;
            }
        ''')
        form_layout.addWidget(sku_label)
        
        sku_edit = QLineEdit(current_sku)
        sku_edit.setStyleSheet('''
            QLineEdit {
                padding: 12px 15px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12pt;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                outline: none;
            }
        ''')
        form_layout.addWidget(sku_edit)
        
        # 规格选项
        option_label = QLabel('规格选项')
        option_label.setStyleSheet('''
            QLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #495057;
                margin-bottom: 4px;
                border: none;
                background: none;
            }
        ''')
        form_layout.addWidget(option_label)
        
        option_edit = QLineEdit(current_option)
        option_edit.setStyleSheet('''
            QLineEdit {
                padding: 12px 15px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12pt;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                outline: none;
            }
        ''')
        form_layout.addWidget(option_edit)
        
        # 成本价
        price_label = QLabel('成本价')
        price_label.setStyleSheet('''
            QLabel {
                font-size: 11pt;
                font-weight: bold;
                color: #495057;
                margin-bottom: 4px;
                border: none;
                background: none;
            }
        ''')
        form_layout.addWidget(price_label)
        
        price_edit = QLineEdit()
        price_edit.setText(f'{current_cost:.2f}')
        price_edit.setPlaceholderText('输入成本价，如: 15.50')
        price_edit.setStyleSheet('''
            QLineEdit {
                padding: 12px 15px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background: white;
                font-size: 12pt;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                outline: none;
            }
        ''')
        form_layout.addWidget(price_edit)
        
        main_layout.addWidget(form_widget)

        # 按钮区域
        btn_box = QHBoxLayout()
        btn_box.setSpacing(15)
        btn_box.setContentsMargins(0, 10, 0, 0)
        
        save_btn = QPushButton('保存')
        save_btn.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-size: 11pt;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        ''')
        
        cancel_btn = QPushButton('取消')
        cancel_btn.setStyleSheet('''
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                font-size: 11pt;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c41f13;
            }
        ''')
        
        btn_box.addStretch()
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        main_layout.addLayout(btn_box)

        def save():
            new_sku = sku_edit.text().strip()
            new_option = option_edit.text().strip()
            price_text = price_edit.text().strip()
            
            if not new_sku or not new_option:
                QMessageBox.warning(dialog, '错误', 'SKU和规格不能为空')
                return
            
            # 验证成本价输入
            try:
                new_price = float(price_text)
                if new_price <= 0:
                    QMessageBox.warning(dialog, '错误', '成本价必须大于0')
                    return
            except ValueError:
                QMessageBox.warning(dialog, '错误', '请输入有效的成本价')
                return
            
            try:
                # 使用DAL层更新变体
                std_option = standardize_option_name(new_option)
                
                variant_data = {
                    'sku': new_sku,
                    'option_name': std_option,  # 使用 option_name 而不是 option1_value
                    'cost_price': new_price
                }
                
                operator_info = get_operator_info()
                dal.update_variant(variant_id, variant_data, operator_info)
                
                # 记录操作日志
                dal.create_action_log(
                    action='update_product',
                    details=f'修改产品SKU: {new_sku}, 规格: {std_option}, '
                            f'成本价: {new_price}',
                    operator_info=operator_info
                )
                
                # 清除产品缓存和库存缓存
                from utils.cache import data_cache
                data_cache.invalidate('products_list_full')
                data_cache.invalidate('inventory_data')  # 新产品会影响库存显示
                print("🗑️ 添加产品成功，已清除缓存")
                
                self.load_products()
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, '错误', f'保存失败: {str(e)}')

        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec()

    def batch_edit_variants(self):
        """修改选中的子SKU"""
        selected_items = self.product_tree.selectedItems()
        variant_ids = []

        # 只收集子SKU的ID
        for item in selected_items:
            if item.parent() and item.text(1):  # 确保是子SKU项
                variant_id = item.data(0, Qt.ItemDataRole.UserRole)
                if variant_id:
                    variant_ids.append(variant_id)

        if not variant_ids:
            QMessageBox.information(self, '提示', '请先选择要修改的子SKU！')
            return
        # 如果只选中了一个子SKU，直接打开编辑对话框
        if len(variant_ids) == 1:
            for item in selected_items:
                item_id = item.data(0, Qt.ItemDataRole.UserRole)
                if item.parent() and item_id == variant_ids[0]:
                    self.edit_variant_dialog(item)
                    return
        
        # 多个子SKU时，提供批量或单独编辑选择
        self.show_batch_edit_dialog(variant_ids)

    def show_batch_edit_dialog(self, variant_ids):
        """显示批量编辑对话框，支持单独编辑每个子SKU"""
        dialog = QDialog(self)
        dialog.setWindowTitle('批量修改子SKU')
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)
        
        # 标题
        title_label = QLabel(f'选中了 {len(variant_ids)} 个子SKU')
        title_label.setStyleSheet(
            'font-size: 14pt; font-weight: bold; color: #1890ff; '
            'padding: 10px; border-bottom: 2px solid #e6f7ff; '
            'background-color: #f0f9ff; margin-bottom: 10px;'
        )
        layout.addWidget(title_label)
        
        # 选项标签页
        from PyQt6.QtWidgets import QTabWidget
        tab_widget = QTabWidget()
        
        # 第一个标签页：批量修改（原有功能）
        batch_tab = QWidget()
        self.create_batch_edit_tab(batch_tab, variant_ids)
        tab_widget.addTab(batch_tab, '📝 批量修改')
        
        # 第二个标签页：单独编辑
        individual_tab = QWidget()
        self.create_individual_edit_tab(individual_tab, variant_ids)
        tab_widget.addTab(individual_tab, '✏️ 单独编辑')
        
        layout.addWidget(tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)
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
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()

    def create_batch_edit_tab(self, parent, variant_ids):
        """创建批量编辑标签页（原有的批量修改功能）"""
        layout = QVBoxLayout(parent)
        
        # 子SKU前缀修改
        sku_frame = QFrame()
        sku_frame.setStyleSheet('QFrame { border: 1px solid #ddd; '
                               'border-radius: 5px; padding: 10px; '
                               'margin: 5px 0; }')
        sku_layout = QVBoxLayout(sku_frame)
        
        modify_skus_cb = QCheckBox('修改子SKU')
        modify_skus_cb.setStyleSheet('font-weight: bold;')
        sku_layout.addWidget(modify_skus_cb)
        
        sku_input_layout = QHBoxLayout()
        sku_prefix_edit = QLineEdit()
        sku_prefix_edit.setPlaceholderText('输入SKU前缀，如: NEW-')
        sku_prefix_edit.setEnabled(False)
        sku_suffix_edit = QLineEdit()
        sku_suffix_edit.setPlaceholderText('输入SKU后缀，如: -V2')
        sku_suffix_edit.setEnabled(False)
        
        sku_input_layout.addWidget(QLabel('前缀:'))
        sku_input_layout.addWidget(sku_prefix_edit)
        sku_input_layout.addWidget(QLabel('后缀:'))
        sku_input_layout.addWidget(sku_suffix_edit)
        sku_layout.addLayout(sku_input_layout)
        
        layout.addWidget(sku_frame)
        
        # 规格选项修改
        option_frame = QFrame()
        option_frame.setStyleSheet('QFrame { border: 1px solid #ddd; '
                                  'border-radius: 5px; padding: 10px; '
                                  'margin: 5px 0; }')
        option_layout = QVBoxLayout(option_frame)
        
        modify_option_names_cb = QCheckBox('修改规格选项')
        modify_option_names_cb.setStyleSheet('font-weight: bold;')
        option_layout.addWidget(modify_option_names_cb)
        
        option_input_layout = QHBoxLayout()
        option_name_edit = QLineEdit()
        option_name_edit.setPlaceholderText('替换选项名称，如: 蓝色')
        option_name_edit.setEnabled(False)
        option_suffix_combo = QComboBox()
        option_suffix_combo.addItems(['添加后缀', '替换全部'])
        option_suffix_combo.setEnabled(False)
        
        option_input_layout.addWidget(option_name_edit)
        option_input_layout.addWidget(option_suffix_combo)
        option_layout.addLayout(option_input_layout)
        
        layout.addWidget(option_frame)
        
        # 成本价修改
        cost_frame = QFrame()
        cost_frame.setStyleSheet('QFrame { border: 1px solid #ddd; '
                                'border-radius: 5px; padding: 10px; '
                                'margin: 5px 0; }')
        cost_layout = QVBoxLayout(cost_frame)
        
        modify_cost_prices_cb = QCheckBox('修改成本价')
        modify_cost_prices_cb.setStyleSheet('font-weight: bold;')
        cost_layout.addWidget(modify_cost_prices_cb)
        
        cost_input_layout = QHBoxLayout()
        cost_mode_combo = QComboBox()
        cost_mode_combo.addItems(['设置为固定值', '增加金额', '减少金额', 
                                 '增加百分比', '减少百分比'])
        cost_mode_combo.setEnabled(False)
        cost_amount_edit = QLineEdit()
        cost_amount_edit.setPlaceholderText('输入数值，如: 15.50')
        cost_amount_edit.setEnabled(False)
        
        cost_input_layout.addWidget(cost_mode_combo)
        cost_input_layout.addWidget(cost_amount_edit)
        cost_layout.addLayout(cost_input_layout)
        
        layout.addWidget(cost_frame)
        
        # 预览区域
        preview_frame = QFrame()
        preview_frame.setStyleSheet('QFrame { border: 1px solid #1890ff; '
                                   'border-radius: 5px; background-color: '
                                   '#f0f9ff; padding: 10px; margin: 5px 0; }')
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_label = QLabel('预览效果 (前3个):')
        preview_label.setStyleSheet('font-weight: bold; color: #1890ff;')
        preview_layout.addWidget(preview_label)
        
        preview_text = QTextEdit()
        preview_text.setMaximumHeight(120)
        preview_text.setReadOnly(True)
        preview_text.setStyleSheet('background-color: white; border: none;')
        preview_layout.addWidget(preview_text)
        
        layout.addWidget(preview_frame)
        
        # 应用按钮
        apply_btn = QPushButton('应用批量修改')
        apply_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 20px;
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #449d44;
            }
        ''')
        
        def apply_batch_changes():
            self._apply_batch_changes(variant_ids, {
                'modify_skus': modify_skus_cb.isChecked(),
                'sku_prefix': sku_prefix_edit.text().strip(),
                'sku_suffix': sku_suffix_edit.text().strip(),
                'modify_options': modify_option_names_cb.isChecked(),
                'option_name': option_name_edit.text().strip(),
                'option_mode': option_suffix_combo.currentText(),
                'modify_costs': modify_cost_prices_cb.isChecked(),
                'cost_mode': cost_mode_combo.currentText(),
                'cost_value': cost_amount_edit.text().strip()
            })
            parent.parent().accept()  # 关闭对话框
            
        apply_btn.clicked.connect(apply_batch_changes)
        layout.addWidget(apply_btn)
        
        # 更新预览功能
        def update_preview():
            if not any([modify_skus_cb.isChecked(), 
                       modify_option_names_cb.isChecked(),
                       modify_cost_prices_cb.isChecked()]):
                preview_text.setText('请选择要修改的内容')
                return
                
            preview_items = []
            # 使用 DAL 层获取变体数据
            from utils.data_access import dal
            for i, variant_id in enumerate(variant_ids[:3]):
                variant = dal.get_variant_by_id(variant_id)
                if variant:
                    # 兼容字典和对象格式
                    current_sku = safe_get_attr(variant, 'sku', '')
                    current_option = safe_get_attr(variant, 'option_name', '')
                    current_cost = safe_get_attr(variant, 'cost_price', 0)
                    
                    # 模拟修改后的效果
                    new_sku = current_sku
                    new_option = current_option or ''
                    new_cost = current_cost
                    
                    if modify_skus_cb.isChecked():
                        prefix = sku_prefix_edit.text().strip()
                        suffix = sku_suffix_edit.text().strip()
                        if prefix:
                            new_sku = prefix + new_sku
                        if suffix:
                            new_sku = new_sku + suffix
                            
                    if modify_option_names_cb.isChecked():
                        option_text = option_name_edit.text().strip()
                        if option_text:
                            if option_suffix_combo.currentText() == '添加后缀':
                                new_option = new_option + option_text
                            else:
                                new_option = option_text
                                
                    if modify_cost_prices_cb.isChecked():
                        try:
                            value = float(cost_amount_edit.text().strip() or 0)
                            mode = cost_mode_combo.currentText()
                            if mode == '设置为固定值':
                                new_cost = value
                            elif mode == '增加金额':
                                new_cost = current_cost + value
                            elif mode == '减少金额':
                                new_cost = current_cost - value
                            elif mode == '增加百分比':
                                new_cost = current_cost * (1 + value / 100)
                            elif mode == '减少百分比':
                                new_cost = current_cost * (1 - value / 100)
                        except ValueError:
                            pass
                            
                    preview_items.append(
                        f'{i+1}. SKU: {current_sku} → {new_sku}\n'
                        f'   选项: {current_option or ""} → {new_option}\n'
                        f'   成本: ¥{current_cost:.2f} → ¥{new_cost:.2f}\n'
                    )
            
            preview_text.setText('\n'.join(preview_items))
        
        # 连接信号
        modify_skus_cb.stateChanged.connect(lambda state: (
            sku_prefix_edit.setEnabled(state), 
            sku_suffix_edit.setEnabled(state), 
            update_preview()))
            
        modify_option_names_cb.stateChanged.connect(lambda state: (
            option_name_edit.setEnabled(state), 
            option_suffix_combo.setEnabled(state), 
            update_preview()))
        
        modify_cost_prices_cb.stateChanged.connect(lambda state: (
            cost_mode_combo.setEnabled(state), 
            cost_amount_edit.setEnabled(state), 
            update_preview()))
        
        # 文本改变时更新预览
        for widget in [sku_prefix_edit, sku_suffix_edit, option_name_edit, 
                      cost_amount_edit]:
            widget.textChanged.connect(update_preview)
        cost_mode_combo.currentTextChanged.connect(update_preview)
        option_suffix_combo.currentTextChanged.connect(update_preview)
        
        # 初始预览
        update_preview()

    def create_individual_edit_tab(self, parent, variant_ids):
        """创建单独编辑标签页"""
        layout = QVBoxLayout(parent)
        
        # 说明文字
        info_label = QLabel(
            '在这里您可以单独编辑每个子SKU的内容：'
        )
        info_label.setStyleSheet(
            'color: #666; margin-bottom: 10px; font-size: 13px;'
        )
        layout.addWidget(info_label)
        
        # 创建滚动区域
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 存储所有输入控件
        self.individual_edit_data = []
        
        # 使用 DAL 层获取变体数据 - 添加异常保护
        from utils.data_access import dal
        import logging
        
        failed_count = 0
        for i, variant_id in enumerate(variant_ids):
            try:
                variant = dal.get_variant_by_id(variant_id)
                if not variant:
                    logging.warning(f'变体ID {variant_id} 不存在，跳过')
                    failed_count += 1
                    continue
            except Exception as e:
                logging.error(f'获取变体ID {variant_id} 失败: {e}')
                failed_count += 1
                continue
            
            # 兼容字典和对象格式
            variant_sku = safe_get_attr(variant, 'sku', '')
            variant_option = safe_get_attr(variant, 'option_name', '')
            variant_cost = safe_get_attr(variant, 'cost_price', 0)
                
            # 为每个子SKU创建编辑框
            sku_frame = QFrame()
            sku_frame.setStyleSheet('''
                QFrame {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 5px 0;
                    background-color: #fafafa;
                }
            ''')
            sku_layout = QVBoxLayout(sku_frame)
            
            # 标题
            title = QLabel(f'#{i+1}: {variant_sku}')
            title.setStyleSheet('font-weight: bold; font-size: 14px; '
                               'color: #333; margin-bottom: 8px;')
            sku_layout.addWidget(title)
            
            # 输入字段
            form_layout = QFormLayout()
            form_layout.setSpacing(8)
            
            sku_edit = QLineEdit(variant_sku)
            sku_edit.setPlaceholderText('子SKU编号')
            form_layout.addRow('SKU:', sku_edit)
            
            option_edit = QLineEdit(variant_option or '')
            option_edit.setPlaceholderText('规格选项，如: 红色-L')
            form_layout.addRow('选项:', option_edit)
            
            cost_edit = QLineEdit(f'{variant_cost:.2f}')
            cost_edit.setPlaceholderText('成本价格')
            form_layout.addRow('成本价:', cost_edit)
            
            sku_layout.addLayout(form_layout)
            
            # 保存控件引用
            self.individual_edit_data.append({
                'variant_id': variant_id,
                'sku_edit': sku_edit,
                'option_edit': option_edit,
                'cost_edit': cost_edit
            })
            
            scroll_layout.addWidget(sku_frame)
        
        # 如果有失败的项，显示警告
        if failed_count > 0:
            warning_label = QLabel(
                f'⚠️ 警告: {failed_count} 个SKU加载失败，已跳过'
            )
            warning_label.setStyleSheet(
                'color: #ff4d4f; font-weight: bold; '
                'padding: 10px; background: #fff2e8; '
                'border-radius: 4px; margin: 10px 0;'
            )
            scroll_layout.addWidget(warning_label)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 应用按钮
        apply_individual_btn = QPushButton('应用单独修改')
        apply_individual_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 20px;
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
        ''')
        
        def apply_individual_changes():
            self._apply_individual_changes()
            parent.parent().accept()  # 关闭对话框
            
        apply_individual_btn.clicked.connect(apply_individual_changes)
        layout.addWidget(apply_individual_btn)

    def _apply_individual_changes(self):
        """应用个人编辑的更改 - 使用DAL层"""
        from utils.data_access import dal
        from utils.operator import get_operator_info
        
        success_count = 0
        error_count = 0
        
        for edit_data in self.individual_edit_data:
            try:
                variant_id = edit_data['variant_id']
                new_sku = edit_data['sku_edit'].text().strip()
                new_option = edit_data['option_edit'].text().strip()
                new_cost_str = edit_data['cost_edit'].text().strip()
                
                if not new_sku or not new_option:
                    continue
                
                # 验证成本价
                try:
                    cost_price = float(new_cost_str)
                except ValueError:
                    error_count += 1
                    continue
                
                # 构建更新数据
                variant_data = {
                    'sku': new_sku,
                    'option1_value': new_option,  # 使用标准化的选项名
                    'cost_price': cost_price
                }
                
                # 使用 DAL 层更新变体
                operator_info = get_operator_info()
                dal.update_variant(variant_id, variant_data, operator_info)
                success_count += 1
                
            except Exception as e:
                print(f'批量编辑错误: {e}')
                import traceback
                traceback.print_exc()
                error_count += 1
        
        # 显示结果
        if success_count > 0:
            msg = f'成功更新 {success_count} 个变体'
            if error_count > 0:
                msg += f'，失败 {error_count} 个'
            QMessageBox.information(self, '成功', msg)
            
            # 清除产品缓存和库存缓存
            from utils.cache import data_cache
            data_cache.invalidate('products_list_full')
            data_cache.invalidate('inventory_data')  # 批量修改可能影响库存显示
            print("🗑️ 批量修改产品成功，已清除缓存")
        elif error_count > 0:
            QMessageBox.warning(self, '警告', f'更新失败 {error_count} 个变体')
        
        self.load_products()

    def export_products(self):
        """导出产品信息"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出产品', '', 'CSV Files (*.csv)'
        )
        if file_path:
            try:
                # 使用DAL层获取产品数据
                from utils.data_access import dal
                products = dal.get_all_products()
                
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(['产品名称', 'SKU', '规格', '成本价', '预警值'])
                    
                    for product in products:
                        # 处理不同数据格式（ORM对象或字典）
                        product_name = safe_get_attr(product, 'name', '')
                        warning_threshold = safe_get_attr(product, 'stock_warning_level', 10)
                        if warning_threshold is None:
                            warning_threshold = safe_get_attr(product, 'warning_threshold', 10)
                        variants = safe_get_attr(product, 'variants', [])
                        
                        for variant in variants:
                            sku = safe_get_attr(variant, 'sku', '')
                            option = safe_get_attr(variant, 'option_name', '')
                            cost_price = safe_get_attr(variant, 'cost_price', 0)
                            
                            writer.writerow([
                                product_name,
                                sku,
                                option,
                                cost_price,
                                warning_threshold
                            ])
                
                QMessageBox.information(self, '成功', '产品导出完成！')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')

    def import_products(self):
        """导入产品信息 - 使用DAL层"""
        file_path, file_type = QFileDialog.getOpenFileName(
            self,
            '导入产品',
            '',
            'All Files (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx)'
        )
        if not file_path:
            return
        
        try:
            from utils.data_access import dal
            from utils.operator import get_operator_info
            import pandas as pd
            
            # 读取数据
            data = []
            if file_path.lower().endswith('.csv'):
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    data = list(csv.DictReader(f))
            else:
                df = pd.read_excel(file_path)
                data = df.to_dict('records')
            
            if not data:
                QMessageBox.warning(self, '警告', '文件为空')
                return
            
            # 标准化列名映射 - 严格按照模板字段
            column_map = {
                # parent_sku 字段
                '父SKU': 'parent_sku', '父SKU编号': 'parent_sku', 'parent_sku': 'parent_sku',
                # sku 字段
                'SKU': 'sku', 'SKU编号': 'sku', '子SKU编号': 'sku', 'sku': 'sku',
                # option_name 字段
                '规格': 'option_name', '规格名称': 'option_name', 
                'option_name': 'option_name', 'option': 'option_name',
                # cost_price 字段
                '成本价': 'cost_price', '成本价格': 'cost_price', 'cost_price': 'cost_price'
            }
            
            # 转换数据格式
            products_to_import = []
            for row in data:
                converted_row = {}
                for orig_col in row.keys():
                    col_str = str(orig_col).strip()
                    if col_str in column_map:
                        converted_row[column_map[col_str]] = row[orig_col]
                
                # 验证必需字段
                if 'sku' in converted_row and 'parent_sku' in converted_row:
                    try:
                        product_item = {
                            'parent_sku': str(converted_row.get('parent_sku', '')).strip(),
                            'sku': str(converted_row.get('sku', '')).strip(),
                            'option_name': str(converted_row.get('option_name', '')).strip(),
                            'cost_price': float(converted_row.get('cost_price', 0))
                        }
                        products_to_import.append(product_item)
                    except Exception as e:
                        print(f'数据转换错误: {e}')
            
            if not products_to_import:
                QMessageBox.warning(self, '警告', '没有找到有效的产品数据')
                return
            
            # 显示进度对话框
            from gui.progress_dialog import ProgressDialog
            progress = ProgressDialog(
                self,
                title="导入产品",
                message="正在导入产品,请稍候..."
            )
            progress.set_range(0, len(products_to_import))
            progress.show()
            QApplication.processEvents()  # 刷新界面
            
            # 使用DAL层导入
            operator_info = get_operator_info()
            
            # 更新进度(开始处理)
            progress.set_detail(f"准备导入 {len(products_to_import)} 个产品...")
            QApplication.processEvents()
            
            result = dal.import_products(products_to_import, operator_info)
            
            # 更新进度(处理完成)
            progress.set_value(len(products_to_import))
            QApplication.processEvents()
            
            # 清除产品缓存和库存缓存（因为新产品会影响库存显示）
            from utils.cache import data_cache
            data_cache.invalidate('products_list_full')
            data_cache.invalidate('inventory_data')  # 同时清除库存缓存
            print("🗑️ 导入产品成功，已清除产品和库存缓存")
            
            self.load_products()
            
            success = result.get('success', 0)
            failed = result.get('failed', 0)
            
            # 完成进度对话框并自动关闭
            progress.complete(
                message=f"导入完成! 成功{success}个,失败{failed}个",
                auto_close_delay=1500
            )
            
            # 记录操作日志
            if success > 0:
                dal.create_action_log(
                    action='import_products',
                    details=f'导入产品 {success} 个 (失败 {failed} 个)',
                    operator_info=operator_info
                )
            
            QMessageBox.information(
                self,
                '导入完成',
                f'成功导入 {success} 个产品\n失败 {failed} 个'
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')
