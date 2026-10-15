from datetime import datetime
from functools import partial
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QMessageBox, QComboBox,
    QLineEdit, QDateEdit, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
import pandas as pd

from database.inventory import ShipmentStatus
from utils.operator import get_operator_info
from config.column_width_manager import get_column_width_manager
from utils.cache import data_cache  # 全局缓存
from gui.widgets.pagination import PaginationWidget
from utils.type_safe import safe_get_attr as get_attr


def get_transport_icon(tracking_number: str) -> str:
    """
    根据物流单号判断运输方式并返回对应图标
    
    Args:
        tracking_number: 物流单号
        
    Returns:
        str: 运输方式图标
            - 🚢 海运 (YD/TA开头)
            - 🚚 陆运 (TB开头)
            - 🚚 默认陆运
    """
    if not tracking_number:
        return '🚚'
    
    tracking_upper = str(tracking_number).upper().strip()
    
    # 海运：YD或TA开头
    if tracking_upper.startswith(('YD', 'TA')):
        return '🚢'
    # 陆运：TB开头
    elif tracking_upper.startswith('TB'):
        return '🚚'
    else:
        # 默认陆运
        return '🚚'


def get_transport_method_text(tracking_number: str) -> str:
    """
    根据物流单号获取运输方式文本
    
    Args:
        tracking_number: 物流单号
        
    Returns:
        str: 运输方式文本 (海运/陆运)
    """
    if not tracking_number:
        return '陆运'
    
    tracking_upper = str(tracking_number).upper().strip()
    
    # 海运：YD或TA开头
    if tracking_upper.startswith(('YD', 'TA')):
        return '海运'
    # 陆运：TB开头
    elif tracking_upper.startswith('TB'):
        return '陆运'
    else:
        return '陆运'


class ShipmentView(QWidget):
    def __init__(self):
        super().__init__()
        self.search_timer = None  # 搜索防抖定时器
        self.all_shipments = []  # 缓存所有发货记录，用于内存过滤
        
        # 分页状态
        self.current_page = 1
        self.page_size = 50
        self.total_shipments = 0
        
        # 搜索状态
        self.search_keyword = ''
        
        self.init_ui()
        self.load_shipments()
        
    def init_ui(self):
        """初始化现代化UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 创建现代化工具栏
        toolbar_frame = self._create_modern_toolbar()
        layout.addWidget(toolbar_frame)
        
        # 创建表格容器
        table_container = self._create_table_container()
        layout.addWidget(table_container, 1)
        
    def _create_modern_toolbar(self):
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
        toolbar.setSpacing(8)
        toolbar.setContentsMargins(8, 6, 8, 6)
        
        # 主要操作按钮组
        self.import_btn = self._create_action_button(
            '📥 批量导入', '#52c41a', '#389e0d'
        )
        self.import_btn.clicked.connect(self.import_shipments)
        toolbar.addWidget(self.import_btn)
        
        self.export_template_btn = self._create_action_button(
            '📄 下载模板', '#722ed1', '#531dab'
        )
        self.export_template_btn.clicked.connect(self.export_template)
        toolbar.addWidget(self.export_template_btn)
        
        self.refresh_btn = self._create_action_button(
            '🔄 刷新', '#13c2c2', '#08979c'
        )
        self.refresh_btn.clicked.connect(self.load_shipments)
        toolbar.addWidget(self.refresh_btn)
        
        toolbar.addStretch()
        
        # 状态筛选区域
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setSpacing(8)
        filter_layout.setContentsMargins(8, 4, 8, 4)
        
        status_label = QLabel('📊 状态筛选:')
        status_label.setStyleSheet('font-weight: bold; color: #495057;')
        filter_layout.addWidget(status_label)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems([
            '🔍 全部状态',
            '⏳ 待发货',
            '🚚 运输中',
            '✅ 已上架',
            '❌ 已取消'
        ])
        self.status_filter.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                min-width: 140px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #1890ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.status_filter.currentTextChanged.connect(self.filter_shipments)
        filter_layout.addWidget(self.status_filter)
        
        toolbar.addWidget(filter_frame)
        
        # SKU搜索区域
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(8)
        search_layout.setContentsMargins(8, 4, 8, 4)
        
        search_label = QLabel('🔎 搜索SKU:')
        search_label.setStyleSheet('font-weight: bold; color: #495057;')
        search_layout.addWidget(search_label)
        
        self.sku_search_input = QLineEdit()
        self.sku_search_input.setPlaceholderText('输入SKU名称搜索（按回车）...')
        self.sku_search_input.returnPressed.connect(self.on_search)
        self.sku_search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                min-width: 200px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1890ff;
            }
        """)
        search_layout.addWidget(self.sku_search_input)
        
        # 清空搜索按钮
        clear_search_btn = QPushButton('✖')
        clear_search_btn.setFixedSize(28, 28)
        clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_search_btn)
        
        toolbar.addWidget(search_frame)
        
        return toolbar_frame
    
    def _create_action_button(self, text, normal_color, hover_color):
        """创建统一样式的操作按钮"""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {normal_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                padding: 9px 15px 7px 17px;
            }}
        """)
        return btn
    
    def _create_table_container(self):
        """创建表格容器"""
        container = QFrame()
        container.setObjectName("tableContainer")
        container.setStyleSheet("""
            QFrame#tableContainer {
                background-color: white;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 发货记录树形表格
        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels([
            '批次/SKU', '数量', '物流单号', '状态',
            '发货时间', '操作'
        ])
        self.tree.setAlternatingRowColors(True)
        
        # 设置现代化字体
        font = QFont()
        font.setFamily('Microsoft YaHei UI')
        font.setPointSize(10)
        self.tree.setFont(font)
        
        # 设置表头样式
        header = self.tree.header()
        header.setFont(font)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef
                );
                color: #495057;
                padding: 10px 8px;
                border: none;
                border-right: 1px solid #dee2e6;
                border-bottom: 2px solid #1890ff;
                font-weight: bold;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e9ecef, stop:1 #dee2e6
                );
            }
        """)
        
        # 设置树形视图现代化样式
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: white;
                outline: none;
            }
            QTreeWidget::item {
                padding: 10px 6px;
                min-height: 36px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:hover {
                background-color: #f5f8ff;
            }
            QTreeWidget::item:selected {
                background-color: #e6f4ff;
                color: #1890ff;
                border-left: 3px solid #1890ff;
            }
            QTreeWidget::branch:has-children:closed {
                image: url(none);
            }
            QTreeWidget::branch:has-children:open {
                image: url(none);
            }
        """)
        
        # 加载列宽配置（支持用户自定义调整）
        width_manager = get_column_width_manager()
        saved_widths = width_manager.get_column_widths('shipment_view')
        
        # 使用保存的列宽，如果没有则使用默认值
        if saved_widths and len(saved_widths) == 6:
            column_widths = saved_widths
        else:
            # 默认列宽: [批次/SKU, 数量, 物流单号, 状态, 发货时间, 操作]
            column_widths = [232, 100, 150, 127, 108, 426]
        
        for i, width in enumerate(column_widths):
            self.tree.setColumnWidth(i, width)
        
        # 监听列宽变化
        header.sectionResized.connect(self.on_column_resized)
        
        container_layout.addWidget(self.tree)
        
        # 添加分页控件
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        container_layout.addWidget(self.pagination)
        
        return container
    
    def _on_page_changed(self, page: int):
        """页码变更回调"""
        self.current_page = page
        self.load_shipments()
        
    def on_column_resized(self, column, old_width, new_width):
        """保存列宽到配置文件"""
        try:
            # 获取所有列的宽度
            column_count = self.tree.columnCount()
            widths = []
            for i in range(column_count):
                widths.append(self.tree.columnWidth(i))
            
            # 保存到配置文件
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('shipment_view', widths)
        except Exception as e:
            print(f"保存列宽配置失败: {e}")
        
    def load_shipments(self):
        """从服务端加载发货记录（分页加载）"""
        try:
            # 获取当前过滤条件
            status_filter = None
            if hasattr(self, 'status_filter'):
                filter_text = self.status_filter.currentText()
                if filter_text != '🔍 全部状态':
                    filter_map = {
                        '⏳ 待发货': 'pending',
                        '🚚 运输中': 'in_transit',
                        '✅ 已上架': 'shelved',
                        '❌ 已取消': 'cancelled'
                    }
                    status_filter = filter_map.get(filter_text)
            
            sku_search = ''
            if hasattr(self, 'sku_search_input'):
                sku_search = self.search_keyword
            
            # 从服务端获取分页数据
            from utils.data_access import dal
            from client.api_client import APIClient
            
            client = APIClient()
            result = client.get_shipments_paginated(
                page=self.current_page,
                page_size=self.page_size,
                status=status_filter,
                sku=sku_search if sku_search else None
            )
            
            shipments = result.get('items', [])
            total = result.get('total', 0)
            self.total_shipments = total
            
            print(f"📝 加载第{self.current_page}页发货记录, 共{total}条")
            
            # 更新分页控件
            if hasattr(self, 'pagination'):
                import math
                total_pages = math.ceil(total / self.page_size) if self.page_size > 0 else 1
                self.pagination.set_page_info(
                    current_page=self.current_page,
                    total_pages=total_pages,
                    total_items=total,
                    page_size=self.page_size
                )
            
            # 显示数据
            self.display_shipments_from_result(shipments)
            
        except Exception as e:
            error_msg = f'加载发货记录失败: {str(e)}'
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, '错误', error_msg)
        finally:
            # 恢复按钮状态
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText('🔄 刷新')
    
    def display_shipments_from_result(self, shipments):
        """显示发货记录（从分页结果）"""
        self.tree.clear()
        
        # 状态映射(带表情图标)
        status_map = {
            'pending': "⏳ 待发货",
            'in_transit': "🚚 运输中",
            'arrived': "📦 已到达",
            'shelved': "✅ 已上架",
            'cancelled': "❌ 已取消"
        }
        
        # 状态背景色
        status_color_map = {
            'pending': '#FFF9E6',
            'in_transit': '#E6F7FF',
            'arrived': '#F0FAF0',
            'shelved': '#FAFAFA',
            'cancelled': '#FFF1F0'
        }
        
        # 状态文字颜色
        status_text_color_map = {
            'pending': '#FA8C16',
            'in_transit': '#1890FF',
            'arrived': '#52C41A',
            'shelved': '#8C8C8C',
            'cancelled': '#F5222D'
        }
        
        for shipment in shipments:
            # 创建发货批次父节点
            batch_item = QTreeWidgetItem(self.tree)
            shipment_id = get_attr(shipment, 'id')
            batch_item.setData(0, Qt.ItemDataRole.UserRole, shipment_id)
            
            batch_number = get_attr(shipment, 'batch_number', '')
            batch_item.setText(0, f"📦 {batch_number}")
            
            # 计算批次总数量
            shipment_items = get_attr(shipment, 'shipment_items', [])
            total_quantity = sum(
                get_attr(item, 'quantity', 0) for item in shipment_items
            )
            batch_item.setText(1, str(total_quantity))
            
            # 获取第一个物流单号（批次行显示）
            first_tracking = None
            if shipment_items:
                first_tracking = get_attr(shipment_items[0], 'tracking_number')
            batch_item.setText(2, first_tracking or '-')  # 批次行显示物流单号
            
            # 获取状态
            shipment_status = get_attr(shipment, 'status', 'pending')
            if isinstance(shipment_status, str):
                status_str = shipment_status.lower()
            else:
                status_str = str(shipment_status).lower()
            
            # 根据运输方式确定状态文本（运输中状态显示运输图标）
            if status_str == 'in_transit':
                transport_icon = get_transport_icon(first_tracking)
                transport_text = get_transport_method_text(first_tracking)
                status_text = f"{transport_icon} 运输中({transport_text})"
            else:
                status_map = {
                    'pending': "⏳ 待发货",
                    'arrived': "📦 已到达",
                    'shelved': "✅ 已上架",
                    'cancelled': "❌ 已取消"
                }
                status_text = status_map.get(status_str, status_str)
            
            bg_color = status_color_map.get(status_str, '#FFFFFF')
            text_color = status_text_color_map.get(status_str, '#000000')
            
            # 设置批次行样式
            batch_item.setBackground(0, QColor(bg_color))
            batch_item.setText(3, status_text)
            batch_item.setForeground(3, QColor(text_color))
            
            # 批次行使用粗体
            font_bold = QFont()
            font_bold.setBold(True)
            batch_item.setFont(0, font_bold)
            batch_item.setFont(1, font_bold)  # 数量列也加粗
            
            # 设置发货时间
            created_at = get_attr(shipment, 'created_at')
            if created_at:
                if hasattr(created_at, 'strftime'):
                    time_text = created_at.strftime('%Y-%m-%d')
                else:
                    time_text = str(created_at)[:10]
            else:
                time_text = '-'
            batch_item.setText(4, time_text)
            
            # 添加SKU子项
            for item in shipment_items:
                variant = get_attr(item, 'variant')
                if not variant:
                    continue
                
                sku_item = QTreeWidgetItem()
                sku = get_attr(variant, 'sku', '')
                quantity = get_attr(item, 'quantity', 0)
                tracking = get_attr(item, 'tracking_number', '') or '-'
                
                sku_item.setText(0, f"  └─ {sku}")
                sku_item.setText(1, str(quantity))
                sku_item.setText(2, tracking)  # 物流单号
                sku_item.setText(3, status_text)
                sku_item.setText(4, time_text)
                
                # 子项使用浅色背景
                lighter_bg = QColor(bg_color)
                lighter_bg.setAlpha(128)
                for i in range(sku_item.columnCount()):
                    sku_item.setBackground(i, lighter_bg)
                    if i == 3:
                        sku_item.setForeground(i, QColor(text_color))
                
                batch_item.addChild(sku_item)
            
            # 为批次节点创建操作按钮
            self._create_batch_action_buttons(
                batch_item, shipment, shipment_id
            )
            
            # 默认折叠批次节点（性能优化）
            batch_item.setExpanded(False)
    
    def display_shipments(self):
        """显示发货记录（支持过滤）【已弃用，使用分页加载】"""
        # 显示加载状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText('⏳ 加载中...')
        
        try:
            self.tree.clear()
            status_filter = self.status_filter.currentText()
            sku_search = ''
            if hasattr(self, 'sku_search_input'):
                sku_search = self.sku_search_input.text().strip().upper()
            
            # 使用内存中的数据
            shipments = self.all_shipments
            
            # 状态映射(带表情图标)
            status_map = {
                ShipmentStatus.PENDING: "⏳ 待发货",
                ShipmentStatus.IN_TRANSIT: "🚚 运输中",
                ShipmentStatus.ARRIVED: "📦 已到达",
                ShipmentStatus.SHELVED: "✅ 已上架",
                ShipmentStatus.CANCELLED: "❌ 已取消"
            }
            
            # 状态背景色
            status_color_map = {
                ShipmentStatus.PENDING: '#FFF9E6',
                ShipmentStatus.IN_TRANSIT: '#E6F7FF',
                ShipmentStatus.ARRIVED: '#F0FAF0',
                ShipmentStatus.SHELVED: '#FAFAFA',
                ShipmentStatus.CANCELLED: '#FFF1F0'
            }
            
            # 状态文字颜色
            status_text_color_map = {
                ShipmentStatus.PENDING: '#FA8C16',
                ShipmentStatus.IN_TRANSIT: '#1890FF',
                ShipmentStatus.ARRIVED: '#52C41A',
                ShipmentStatus.SHELVED: '#8C8C8C',
                ShipmentStatus.CANCELLED: '#F5222D'
            }
            
            for shipment in shipments:
                # 状态筛选
                shipment_status_str = get_attr(shipment, 'status')
                
                # 将字符串状态转换为枚举
                if isinstance(shipment_status_str, str):
                    # 转换为小写以兼容大小写
                    status_lower = shipment_status_str.lower()
                    status_str_to_enum = {
                        'pending': ShipmentStatus.PENDING,
                        'in_transit': ShipmentStatus.IN_TRANSIT,
                        'arrived': ShipmentStatus.ARRIVED,
                        'shelved': ShipmentStatus.SHELVED,
                        'cancelled': ShipmentStatus.CANCELLED
                    }
                    shipment_status = status_str_to_enum.get(
                        status_lower, shipment_status_str
                    )
                else:
                    shipment_status = shipment_status_str
                
                # SKU搜索过滤
                if sku_search:
                    shipment_items = get_attr(shipment, 'shipment_items', [])
                    # 检查发货单中是否包含搜索的SKU
                    has_matching_sku = False
                    for item in shipment_items:
                        variant = get_attr(item, 'variant')
                        if variant:
                            item_sku = get_attr(variant, 'sku', '').upper()
                            if sku_search in item_sku:
                                has_matching_sku = True
                                break
                    
                    if not has_matching_sku:
                        continue
                
                # 状态筛选
                if status_filter == '🔍 全部状态':
                    # 如果有SKU搜索,显示所有状态;否则只显示待处理的
                    if not sku_search:
                        # 隐藏已完成(已上架)和已取消的记录
                        if shipment_status in [
                            ShipmentStatus.SHELVED,
                            ShipmentStatus.CANCELLED
                        ]:
                            continue
                elif status_filter != '🔍 全部状态':
                    filter_map = {
                        '⏳ 待发货': ShipmentStatus.PENDING,
                        '🚚 运输中': ShipmentStatus.IN_TRANSIT,
                        '✅ 已上架': ShipmentStatus.SHELVED,
                        '❌ 已取消': ShipmentStatus.CANCELLED
                    }
                    if shipment_status != filter_map.get(status_filter):
                        continue
                
                # 创建发货批次父节点
                batch_item = QTreeWidgetItem(self.tree)
                shipment_id = get_attr(shipment, 'id')
                batch_item.setData(
                    0, Qt.ItemDataRole.UserRole, shipment_id
                )
                
                # 设置批次号粗体
                font_bold = QFont()
                font_bold.setFamily('Microsoft YaHei UI')
                font_bold.setPointSize(10)
                font_bold.setBold(True)
                batch_item.setFont(0, font_bold)
                
                # 计算总数量
                shipment_items = get_attr(shipment, 'shipment_items', [])
                total_qty = sum(
                    get_attr(i, 'quantity', 0) for i in shipment_items
                )
                
                # 获取第一个物流单号
                first_tracking = None
                if shipment_items:
                    first_tracking = get_attr(
                        shipment_items[0], 'tracking_number'
                    )
                
                # 设置批次信息
                batch_number = get_attr(shipment, 'batch_number', '')
                batch_item.setText(
                    0, f"📦 批次: {batch_number}"
                )
                batch_item.setText(1, f"{total_qty} 件")
                batch_item.setText(2, first_tracking or "-")  # 批次行显示物流单号
                
                # 设置状态（根据运输方式显示不同图标）
                if shipment_status == ShipmentStatus.IN_TRANSIT:
                    transport_icon = get_transport_icon(first_tracking)
                    transport_text = get_transport_method_text(first_tracking)
                    status_text = f"{transport_icon} 运输中({transport_text})"
                else:
                    status_text = status_map.get(
                        shipment_status, str(shipment_status)
                    )
                
                batch_item.setText(3, status_text)
                
                # 设置颜色
                bg_color = status_color_map.get(
                    shipment_status, '#FFFFFF'
                )
                text_color = status_text_color_map.get(
                    shipment_status, '#000000'
                )
                for i in range(batch_item.columnCount()):
                    batch_item.setBackground(i, QColor(bg_color))
                    if i == 3:  # 状态列特殊颜色
                        batch_item.setForeground(i, QColor(text_color))
                
                # 设置发货时间(创建时间)
                created_at = get_attr(shipment, 'created_at')
                if created_at:
                    if hasattr(created_at, 'strftime'):
                        time_text = created_at.strftime('%Y-%m-%d')
                    else:
                        time_text = str(created_at)[:10]
                else:
                    time_text = '-'
                batch_item.setText(4, time_text)
                
                # 创建每个SKU的子节点
                # 如果有搜索关键词，只显示匹配的SKU；否则显示所有SKU
                for item in shipment_items:
                    variant = get_attr(item, 'variant', {})
                    sku = get_attr(variant, 'sku', '')
                    
                    # 如果有搜索，只显示匹配的SKU
                    if sku_search:
                        if sku_search not in sku.upper():
                            continue
                    
                    sku_item = QTreeWidgetItem(batch_item)
                    
                    # SKU信息(带缩进符号)
                    quantity = get_attr(item, 'quantity', 0)
                    tracking = get_attr(item, 'tracking_number', '') or '-'
                    
                    sku_item.setText(0, f"  └─ {sku}")
                    sku_item.setText(1, f"{quantity} 件")
                    sku_item.setText(
                        2, tracking
                    )
                    sku_item.setText(3, status_text)
                    sku_item.setText(4, time_text)
                    
                    # 子项使用浅色背景
                    lighter_bg = QColor(bg_color)
                    lighter_bg.setAlpha(128)
                    for i in range(sku_item.columnCount()):
                        sku_item.setBackground(i, lighter_bg)
                        if i == 3:
                            sku_item.setForeground(i, QColor(text_color))
                
                # 为批次节点创建操作按钮
                self._create_batch_action_buttons(
                    batch_item, shipment, shipment_id
                )
                
                # 默认折叠批次节点（性能优化）
                batch_item.setExpanded(False)
            
            # 显示搜索/筛选结果统计
            displayed_count = self.tree.topLevelItemCount()
            
            # 统计显示的SKU数量（用于搜索结果）
            if sku_search:
                sku_count = 0
                for i in range(self.tree.topLevelItemCount()):
                    batch_item = self.tree.topLevelItem(i)
                    sku_count += batch_item.childCount()
            
            # 在状态栏居中显示刷新成功消息
            if hasattr(self, 'refresh_btn'):
                main_window = self.window()
                if hasattr(main_window, 'center_message_label'):
                    if sku_search:
                        main_window.center_message_label.setText(
                            f'🔍 搜索 "{sku_search}" 找到 {sku_count} 个SKU '
                            f'({displayed_count} 笔发货)'
                        )
                    elif status_filter != '🔍 全部状态':
                        main_window.center_message_label.setText(
                            f'✅ 已加载 {displayed_count} 笔 {status_filter} 记录'
                        )
                    else:
                        main_window.center_message_label.setText(
                            f'✅ 发货记录刷新成功，已加载 {displayed_count} 笔记录'
                        )
                    # 3秒后清除消息
                    QTimer.singleShot(3000, lambda: main_window.center_message_label.setText(''))
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载发货记录失败: {str(e)}')
        finally:
            # 恢复刷新按钮状态
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText('🔄 刷新')
    
    def _create_batch_action_buttons(self, batch_item, shipment, shipment_id):
        """为批次创建现代化操作按钮"""
        # 使用传入的shipment_id,而不是重新获取
        shipment_status_str = get_attr(shipment, 'status')
        
        # 调试输出
        print(f"[DEBUG] 创建按钮 - ID={shipment_id}, type={type(shipment_id)}")
        
        # 确保ID有效
        if not shipment_id or shipment_id is False or shipment_id is None:
            print(f"⚠️ 警告: 发货记录ID无效: {shipment_id}")
            return
        
        # 将字符串状态转换为枚举(如果是字符串)
        if isinstance(shipment_status_str, str):
            # 转换为小写以兼容大小写
            status_lower = shipment_status_str.lower()
            status_map = {
                'pending': ShipmentStatus.PENDING,
                'in_transit': ShipmentStatus.IN_TRANSIT,
                'arrived': ShipmentStatus.ARRIVED,
                'shelved': ShipmentStatus.SHELVED,
                'cancelled': ShipmentStatus.CANCELLED
            }
            shipment_status = status_map.get(
                status_lower, ShipmentStatus.PENDING
            )
        else:
            # 已经是枚举对象
            shipment_status = shipment_status_str
        
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(6, 4, 6, 4)
        action_layout.setSpacing(8)
        
        def create_modern_button(text, icon, color, hover_color):
            """创建现代化按钮"""
            btn = QPushButton(f"{icon} {text}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 6px 14px;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 11px;
                    min-width: 90px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
                QPushButton:pressed {{
                    background-color: {hover_color};
                    padding: 7px 13px 5px 15px;
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            return btn
        
        # 根据状态显示不同按钮
        if shipment_status == ShipmentStatus.PENDING:
            ship_btn = create_modern_button(
                '开始发货', '🚀', '#1890FF', '#096DD9'
            )
            # 将ID存储在按钮属性中
            ship_btn.setProperty('shipment_id', shipment_id)
            ship_btn.clicked.connect(
                lambda checked, btn=ship_btn: self.mark_as_intransit(
                    btn.property('shipment_id')
                )
            )
            action_layout.addWidget(ship_btn)
            
        elif shipment_status == ShipmentStatus.IN_TRANSIT:
            # 运输中直接显示"上架入库"按钮
            shelve_btn = create_modern_button(
                '上架入库', '✅', '#52C41A', '#389E0D'
            )
            # 将ID存储在按钮属性中
            shelve_btn.setProperty('shipment_id', shipment_id)
            shelve_btn.clicked.connect(
                lambda checked, btn=shelve_btn: self.mark_as_shelved(
                    btn.property('shipment_id')
                )
            )
            action_layout.addWidget(shelve_btn)
        
        # 取消按钮(非终态才显示)
        if shipment_status not in [
            ShipmentStatus.SHELVED, ShipmentStatus.CANCELLED
        ]:
            cancel_btn = create_modern_button(
                '取消', '❌', '#FF4D4F', '#CF1322'
            )
            # 将ID存储在按钮属性中
            cancel_btn.setProperty('shipment_id', shipment_id)
            cancel_btn.clicked.connect(
                lambda checked, btn=cancel_btn: self.mark_as_cancelled(
                    btn.property('shipment_id')
                )
            )
            action_layout.addWidget(cancel_btn)
        
        # 删除按钮(所有状态都可以删除)
        delete_btn = create_modern_button(
            '删除', '🗑️', '#8C8C8C', '#595959'
        )
        # 将ID存储在按钮属性中
        delete_btn.setProperty('shipment_id', shipment_id)
        delete_btn.clicked.connect(
            lambda checked, btn=delete_btn: self.delete_shipment(
                btn.property('shipment_id')
            )
        )
        action_layout.addWidget(delete_btn)
        
        action_layout.addStretch()
        
        # 确保widget有内容时才显示
        if action_layout.count() > 1:  # 有按钮+stretch
            action_widget.setVisible(True)
            self.tree.setItemWidget(batch_item, 5, action_widget)
                
    def mark_as_arrived(self, shipment_id: int):
        try:
            from utils.data_access import dal
            
            # 使用数据访问层更新状态(使用小写值)
            dal.update_shipment(shipment_id, {
                'status': 'arrived',
                'arrival_date': datetime.now().isoformat()
            })
            
            # 更新后清除缓存
            data_cache.invalidate('shipments_list')
            
            self.load_shipments()
            QMessageBox.information(self, '成功', '已标记为到货')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'操作失败: {str(e)}')
            
    def mark_as_shelved(self, shipment_id: int):
        try:
            from utils.data_access import dal
            
            # 使用数据访问层更新状态(使用小写值)
            dal.update_shipment(shipment_id, {'status': 'shelved'})
            
            # 更新后清除缓存（包括库存数据缓存，以更新在途库存显示）
            data_cache.invalidate('shipments_list')
            data_cache.invalidate('inventory_data')  # 清除库存缓存
            
            self.load_shipments()
            QMessageBox.information(
                self, 
                '成功', 
                '已完成入库\n\n相关SKU的在途库存将自动更新为0'
            )
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'操作失败: {str(e)}')
            
    def mark_as_intransit(self, shipment_id: int):
        """标记为运输中"""
        try:
            from utils.data_access import dal
            
            # 使用数据访问层更新状态(使用小写值)
            dal.update_shipment(shipment_id, {'status': 'in_transit'})
            
            # 更新后清除缓存
            data_cache.invalidate('shipments_list')
            
            self.load_shipments()
            QMessageBox.information(self, '成功', '已标记为运输中')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'操作失败: {str(e)}')
            
    def mark_as_cancelled(self, shipment_id: int):
        """标记为已取消"""
        reply = QMessageBox.question(
            self,
            '确认取消',
            f'确定要取消此发货记录吗?\n'
            f'发货记录ID: {shipment_id}\n'
            f'此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from utils.data_access import dal
                
                # 使用数据访问层更新状态(使用小写值)
                result = dal.update_shipment(
                    shipment_id, {'status': 'cancelled'}
                )
                
                # 更新后清除缓存
                data_cache.invalidate('shipments_list')
                
                self.load_shipments()
                
                # 显示详细的成功消息
                QMessageBox.information(
                    self,
                    '成功',
                    f'发货记录 {shipment_id} 已取消\n\n'
                    f'提示: 已取消的记录已被隐藏\n'
                    f'如需查看,请选择"❌ 已取消"筛选'
                )
                
            except Exception as e:
                error_msg = f'操作失败: {str(e)}'
                print(f"❌ 取消发货失败: {error_msg}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, '错误', error_msg)
    
    def delete_shipment(self, shipment_id: int):
        """删除发货记录"""
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除此发货批次吗?\n'
            f'批次ID: {shipment_id}\n\n'
            f'⚠️ 警告: 此操作将永久删除该批次及其所有明细记录!\n'
            f'此操作不可撤销,请谨慎操作。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from utils.data_access import dal
                
                # 调用数据访问层删除发货记录
                result = dal.delete_shipment(shipment_id)
                
                # 删除后清除缓存
                data_cache.invalidate('shipments_list')
                
                # 刷新列表
                self.load_shipments()
                
                QMessageBox.information(
                    self,
                    '成功',
                    f'发货批次 {shipment_id} 已成功删除'
                )
                
            except Exception as e:
                error_msg = f'删除失败: {str(e)}'
                print(f"❌ 删除发货记录失败: {error_msg}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, '错误', error_msg)
    
    def filter_shipments(self):
        """已废弃：现在搜索通过后端API实现，按回车键触发搜索"""
        pass
    
    def on_search(self):
        """搜索SKU回调：重新从后端查询匹配的数据"""
        new_keyword = self.sku_search_input.text().strip()
        
        # 如果搜索关键词改变，重置到第一页
        if new_keyword != self.search_keyword:
            self.search_keyword = new_keyword
            self.current_page = 1
            
            # 搜索模式提示
            if self.search_keyword:
                print(f"🔍 搜索SKU: '{self.search_keyword}'")
            else:
                print("🔄 清空搜索，恢复全部数据")
            
            self.load_shipments()
    
    def clear_search(self):
        """清空搜索框并恢复全部数据"""
        self.sku_search_input.clear()
        self.search_keyword = ''
        self.current_page = 1
        print("🔄 清空搜索，恢复全部数据")
        self.load_shipments()
        
    def import_shipments(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择发货记录文件',
            '',
            'Excel Files (*.xlsx *.xls);;CSV Files (*.csv)'
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, dtype=str)
            else:
                df = pd.read_excel(file_path, dtype=str)
            
            print(f"发货导入 - 原始列名: {list(df.columns)}")
            
            # 标准化列名映射（支持带星号的列名）
            column_mapping = {}
            for col in df.columns:
                col_str = str(col).strip()
                
                # 移除星号后进行映射
                main_part = col_str.rstrip('*')
                
                if main_part in ['sku', 'SKU', '产品SKU', '产品编号']:
                    column_mapping[col] = 'sku'
                elif main_part in ['quantity', '数量', '发货数量']:
                    column_mapping[col] = 'quantity'
                elif main_part in ['tracking_number', '追踪号', '物流追踪号', '快递单号']:
                    column_mapping[col] = 'tracking_number'
                elif main_part in ['estimated_arrival', '预计到货日期', '预计到货']:
                    column_mapping[col] = 'estimated_arrival'
                elif main_part in ['notes', '备注', '备注说明']:
                    column_mapping[col] = 'notes'
                elif main_part in ['batch_number', '批次号']:
                    column_mapping[col] = 'batch_number'
                else:
                    column_mapping[col] = main_part
            
            # 应用列名映射
            df = df.rename(columns=column_mapping)
            print(f"发货导入 - 映射后列名: {list(df.columns)}")
            
            # 过滤示例行（包含*的行）
            original_count = len(df)
            mask = ~df['sku'].astype(str).str.contains(r'\*', na=False, regex=True)
            df = df[mask]
            
            if len(df) == 0:
                QMessageBox.warning(
                    self,
                    '导入警告',
                    '没有找到有效的发货数据，请确认Excel文件包含有效数据行'
                )
                return
                
            if len(df) < original_count:
                print(f"发货导入 - 已过滤 {original_count - len(df)} 行示例数据")
                
            required_columns = ['sku', 'quantity', 'tracking_number', 'estimated_arrival']
            
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
                    f'文件缺少必需字段: {", ".join(missing_columns)}\n\n'
                    f'可用字段: {", ".join(available_cols)}\n\n'
                    f'请确保文件包含以下字段:\n'
                    f'- sku 或 sku*: 产品SKU\n'
                    f'- quantity 或 quantity*: 数量\n'
                    f'- tracking_number 或 tracking_number*: 追踪号\n'
                    f'- estimated_arrival 或 estimated_arrival*: 预计到货日期 (YYYY-MM-DD)\n'
                    f'可选字段:\n'
                    f'- notes: 备注\n'
                    f'- batch_number: 批次号'
                )
                return
            
            # 使用DAL层统一接口
            from utils.data_access import dal
            from gui.progress_dialog import ProgressDialog
            from PyQt6.QtWidgets import QApplication
            
            operator_info = get_operator_info()
            errors = []
            
            # 显示进度对话框
            progress = ProgressDialog(
                self,
                title="导入发货记录",
                message="正在导入发货记录,请稍候..."
            )
            progress.set_indeterminate()
            progress.show()
            QApplication.processEvents()
            
            # 获取所有产品用于SKU验证
            try:
                all_products = dal.get_all_products()
                sku_lowercase_map = {}
                
                # 辅助函数: 兼容字典和对象
                def get_attr(obj, attr, default=None):
                    if isinstance(obj, dict):
                        return obj.get(attr, default)
                    return getattr(obj, attr, default)
                
                for product in all_products:
                    variants = get_attr(product, 'variants', [])
                    for variant in variants:
                        sku = get_attr(variant, 'sku')
                        if sku:
                            sku_lowercase_map[sku.lower()] = sku
            except Exception as e:
                QMessageBox.critical(
                    self,
                    '错误',
                    f'获取产品信息失败: {str(e)}'
                )
                return
            
            # 按批次号分组
            if 'batch_number' in df.columns:
                groups = df.groupby('batch_number')
            else:
                df['_auto_batch'] = [
                    f'BATCH_{i+1}' for i in range(len(df))
                ]
                groups = df.groupby('_auto_batch')
            
            # 构建发货数据列表
            shipments_to_import = []
            
            for batch_number, batch_df in groups:
                try:
                    # 获取批次的第一条记录的预计到货日期和备注
                    first_row = batch_df.iloc[0]
                    estimated_arrival = pd.to_datetime(
                        first_row['estimated_arrival']
                    ).date()
                    notes = str(first_row.get('notes', '')).strip() if \
                        'notes' in first_row else ''
                    
                    # 构建发货项列表
                    shipment_items = []
                    
                    for _, row in batch_df.iterrows():
                        try:
                            # 检查SKU
                            sku = str(row['sku']).strip()
                            actual_sku = sku_lowercase_map.get(sku.lower())
                            if not actual_sku:
                                errors.append(f"SKU不存在: {sku}")
                                continue
                            
                            # 获取数量
                            quantity_str = str(row['quantity']).strip()
                            if not quantity_str or quantity_str == 'nan':
                                errors.append(f"SKU {sku} 数量为空")
                                continue
                            
                            try:
                                quantity = int(float(quantity_str))
                                if quantity <= 0:
                                    errors.append(f"SKU {sku} 数量必须大于0")
                                    continue
                            except (ValueError, TypeError):
                                errors.append(
                                    f"SKU {sku} 数量无效: {quantity_str}"
                                )
                                continue
                            
                            # 构建发货项数据
                            shipment_item = {
                                'variant_sku': actual_sku,
                                'quantity': quantity,
                                'tracking_number': str(
                                    row['tracking_number']
                                ).strip()
                            }
                            shipment_items.append(shipment_item)
                            
                        except Exception as e:
                            errors.append(f"处理SKU {row['sku']} 时出错: {str(e)}")
                    
                    if not shipment_items:
                        errors.append(f"批次 {batch_number} 没有有效的发货项")
                        continue
                    
                    # 构建发货数据
                    shipment_data = {
                        'batch_number': str(batch_number),
                        'estimated_arrival': estimated_arrival.isoformat(),
                        'notes': notes,
                        'items': shipment_items
                    }
                    shipments_to_import.append(shipment_data)
                    
                except Exception as e:
                    errors.append(f"批次 {batch_number} 处理失败: {str(e)}")
            
            # 调用DAL层导入
            imported_count = 0
            if shipments_to_import:
                # 更新进度提示
                progress.set_message(
                    f"正在导入 {len(shipments_to_import)} 批次发货记录..."
                )
                QApplication.processEvents()
                
                try:
                    result = dal.import_shipments(
                        shipments_to_import,
                        operator_info
                    )
                    imported_count = result.get('success', 0)
                    import_errors = result.get('errors', [])
                    
                    # 合并错误信息
                    for err in import_errors:
                        if isinstance(err, dict):
                            errors.append(
                                f"发货导入失败: {err.get('error', str(err))}"
                            )
                        else:
                            errors.append(f"导入错误: {str(err)}")
                    
                    # 完成进度对话框并自动关闭
                    progress.complete(
                        message=f"导入完成! 成功{imported_count}批次",
                        auto_close_delay=1500
                    )
                    
                except Exception as e:
                    progress.error(
                        message="导入失败!",
                        detail=str(e)[:50],
                        auto_close_delay=2000
                    )
                    QMessageBox.critical(
                        self,
                        '导入失败',
                        f'导入过程中发生错误: {str(e)}'
                    )
                    return
            else:
                progress.error(
                    message="没有可导入的发货记录",
                    auto_close_delay=1500
                )
            
            # 刷新显示
            data_cache.invalidate('shipments_list')  # 清除缓存
            self.load_shipments()
            
            # 显示导入结果
            if imported_count > 0:
                # 导入成功后清除缓存
                data_cache.invalidate('shipments_list')
                
                message = f'成功导入 {imported_count} 条发货记录!\n'
                if errors:
                    message += '\n失败记录:\n' + '\n'.join(
                        f'- {err}' for err in errors[:10]
                    )
                    if len(errors) > 10:
                        message += f'\n... 还有 {len(errors) - 10} 条错误'
                
                QMessageBox.information(self, '导入完成', message)
            else:
                error_message = '导入失败:\n\n'
                if errors:
                    error_message += '\n'.join(
                        f'- {err}' for err in errors[:10]
                    )
                    if len(errors) > 10:
                        error_message += f'\n... 还有 {len(errors) - 10} 条错误'
                
                QMessageBox.critical(self, '导入失败', error_message)
            
        except Exception as e:
            QMessageBox.critical(self, '导入错误', f'文件处理失败: {str(e)}')
            
    def export_template(self):
        try:
            # 创建示例数据
            data = {
                'sku': ['示例SKU-001', 'SKU-002'],
                'quantity': [100, 200],
                'tracking_number': ['SF1234567890', 'YT0987654321'],
                'estimated_arrival': ['2025-10-01', '2025-10-15'],
                'notes': ['示例备注1', '示例备注2']
            }
            df = pd.DataFrame(data)
            
            # 保存文件
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '保存导入模板',
                '发货记录导入模板.xlsx',
                'Excel Files (*.xlsx)'
            )
            
            if file_path:
                df.to_excel(file_path, index=False)
                QMessageBox.information(
                    self,
                    '成功',
                    f'模板已保存到: {file_path}'
                )
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出模板失败: {str(e)}')