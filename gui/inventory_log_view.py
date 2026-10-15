from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel,
    QComboBox, QLineEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QColor, QFont

from client.api_client import api_client
from datetime import datetime, timedelta
from config.column_width_manager import get_column_width_manager
from gui.widgets.pagination import PaginationWidget


class OperationLogView(QWidget):
    def __init__(self):
        super().__init__()
        # 🆕 分页状态
        self.current_page = 1
        self.page_size = 50
        self.total_items = 0
        self.total_pages = 0
        
        # 🆕 添加分页防抖定时器 (避免快速点击导致批量查询)
        self.page_debounce_timer = QTimer()
        self.page_debounce_timer.setSingleShot(True)
        self.page_debounce_timer.timeout.connect(self._do_load_logs)
        self.pending_page = None  # 待加载的页码
        self.is_loading = False  # 是否正在加载
        
        # 🔥 轻量级询问机制：跟踪服务端数据变更时间戳
        self.last_server_timestamp = 0
        self.window_has_focus = True
        
        # 添加延时刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)  # 单次触发
        self.refresh_timer.timeout.connect(self.load_logs)
        
        # 自动刷新定时器（改为询问机制）
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.check_and_refresh)
        self.auto_refresh_timer.start(30000)  # 每30秒询问一次
        
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        """初始化UI布局"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 默认显示最近7天
        self.start_date = QDate.currentDate().addDays(-7)
        self.end_date = QDate.currentDate()
        
        # ==================== 顶部工具栏 ====================
        toolbar_container = QWidget()
        toolbar_container.setStyleSheet('''
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 12px;
            }
        ''')
        toolbar = QHBoxLayout(toolbar_container)
        toolbar.setSpacing(10)
        toolbar.setContentsMargins(12, 12, 12, 12)
        
        # 左侧：标题
        title_label = QLabel('📊 操作记录')
        title_label.setStyleSheet('''
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                background: transparent;
                padding: 0px;
            }
        ''')
        toolbar.addWidget(title_label)
        
        # 显示时间范围提示
        range_label = QLabel('(最近7天)')
        range_label.setStyleSheet('''
            QLabel {
                font-size: 12px;
                color: #6c757d;
                background: transparent;
                padding: 0px;
            }
        ''')
        toolbar.addWidget(range_label)
        
        # 🆕 显示总记录数
        self.total_label = QLabel('📋 总库存: 0 件')
        self.total_label.setStyleSheet('''
            QLabel {
                font-size: 13px;
                color: #495057;
                background: #e3f2fd;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
            }
        ''')
        toolbar.addWidget(self.total_label)
        
        toolbar.addStretch()
        
        # 右侧：清空按钮
        clear_7days_btn = QPushButton('🗑️ 清空7天前')
        clear_7days_btn.clicked.connect(lambda: self.clear_old_logs(7))
        clear_7days_btn.setFixedHeight(32)
        clear_7days_btn.setStyleSheet('''
            QPushButton {
                padding: 6px 16px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #bb2d3b;
            }
            QPushButton:pressed {
                background-color: #a02833;
            }
        ''')
        toolbar.addWidget(clear_7days_btn)
        
        clear_30days_btn = QPushButton('🗑️ 清空30天前')
        clear_30days_btn.clicked.connect(lambda: self.clear_old_logs(30))
        clear_30days_btn.setFixedHeight(32)
        clear_30days_btn.setStyleSheet('''
            QPushButton {
                padding: 6px 16px;
                background-color: #fd7e14;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e8590c;
            }
            QPushButton:pressed {
                background-color: #cc4e0a;
            }
        ''')
        toolbar.addWidget(clear_30days_btn)
        
        layout.addWidget(toolbar_container)
        
        # ==================== 筛选条件区域 ====================
        filter_container = QWidget()
        filter_container.setStyleSheet('''
            QWidget {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
            }
        ''')
        filter_main_layout = QVBoxLayout(filter_container)
        filter_main_layout.setSpacing(8)
        filter_main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 筛选标题
        filter_title = QLabel('🔍 筛选条件')
        filter_title.setStyleSheet('''
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #495057;
                background: transparent;
                padding: 0px;
            }
        ''')
        filter_main_layout.addWidget(filter_title)
        
        # 筛选输入行
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        # SKU搜索
        sku_container = QVBoxLayout()
        sku_container.setSpacing(4)
        sku_label = QLabel('SKU:')
        sku_label.setStyleSheet(
            'color: #6c757d; font-size: 12px; background: transparent;'
        )
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText('输入SKU筛选...')
        self.sku_input.textChanged.connect(self.apply_filters)
        self.sku_input.setFixedHeight(34)
        self.sku_input.setMinimumWidth(200)  # 最小宽度
        self.sku_input.setMaximumWidth(250)  # 最大宽度
        self.sku_input.setStyleSheet('''
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #80bdff;
                outline: none;
            }
        ''')
        sku_container.addWidget(sku_label)
        sku_container.addWidget(self.sku_input)
        filter_layout.addLayout(sku_container)
        
        # 操作类型筛选
        type_container = QVBoxLayout()
        type_container.setSpacing(4)
        type_label = QLabel('操作类型:')
        type_label.setStyleSheet(
            'color: #6c757d; font-size: 12px; background: transparent;'
        )
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            '全部', '入库', '出库', '产品修改', '创建产品',
            '删除操作', '数据导入', '销售操作', '发货操作', '其他操作'
        ])
        self.type_combo.currentTextChanged.connect(self.apply_filters)
        self.type_combo.setFixedHeight(34)
        self.type_combo.setMinimumWidth(160)  # 最小宽度
        self.type_combo.setMaximumWidth(200)  # 最大宽度
        self.type_combo.setStyleSheet('''
            QComboBox {
                padding: 6px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border: 1px solid #80bdff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 8px;
                height: 4px;
            }
        ''')
        type_container.addWidget(type_label)
        type_container.addWidget(self.type_combo)
        filter_layout.addLayout(type_container)
        
        # 操作人员筛选
        operator_container = QVBoxLayout()
        operator_container.setSpacing(4)
        operator_label = QLabel('操作人:')
        operator_label.setStyleSheet(
            'color: #6c757d; font-size: 12px; background: transparent;'
        )
        self.operator_combo = QComboBox()
        self.operator_combo.addItem('全部')
        
        # 连接信号 - 使用 activated 而不是 currentTextChanged
        # activated 只在用户主动选择时触发，不会在程序更新时触发
        self.operator_combo.activated.connect(self.apply_filters)
        self.operator_combo.setFixedHeight(34)
        self.operator_combo.setMaxVisibleItems(15)  # 最多显示15个项
        self.operator_combo.setMinimumWidth(160)  # 最小宽度
        self.operator_combo.setMaximumWidth(200)  # 最大宽度
        self.operator_combo.setStyleSheet('''
            QComboBox {
                padding: 6px 12px;
                padding-right: 30px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                font-size: 13px;
                background-color: #ffffff;
            }
            QComboBox:hover {
                border: 1px solid #80bdff;
                background-color: #f8f9fa;
            }
            QComboBox:focus {
                border: 1px solid #80bdff;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6c757d;
                width: 0;
                height: 0;
                margin-right: 5px;
            }
            QComboBox::down-arrow:hover {
                border-top-color: #0d6efd;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e7f1ff;
                selection-color: #0d6efd;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 12px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #f8f9fa;
            }
        ''')
        operator_container.addWidget(operator_label)
        operator_container.addWidget(self.operator_combo)
        filter_layout.addLayout(operator_container)
        
        # 添加弹性空间
        filter_layout.addStretch()
        
        # ==================== 操作按钮（垂直布局）====================
        action_buttons = QVBoxLayout()
        action_buttons.setSpacing(8)
        
        # 导出按钮
        export_btn = QPushButton('📤 导出数据')
        export_btn.clicked.connect(self.export_logs)
        export_btn.setFixedHeight(34)
        export_btn.setMinimumWidth(120)  # 最小宽度
        export_btn.setMaximumWidth(140)  # 最大宽度
        export_btn.setStyleSheet('''
            QPushButton {
                padding: 6px 12px;
                background-color: #198754;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #157347;
            }
            QPushButton:pressed {
                background-color: #146c43;
            }
        ''')
        action_buttons.addWidget(export_btn)
        
        # 刷新按钮
        refresh_btn = QPushButton('🔄 刷新')
        refresh_btn.clicked.connect(lambda: self.load_logs())
        refresh_btn.setFixedHeight(34)
        refresh_btn.setMinimumWidth(120)  # 最小宽度
        refresh_btn.setMaximumWidth(140)  # 最大宽度
        refresh_btn.setStyleSheet('''
            QPushButton {
                padding: 6px 12px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        ''')
        action_buttons.addWidget(refresh_btn)
        
        filter_layout.addLayout(action_buttons)
        
        filter_main_layout.addLayout(filter_layout)
        layout.addWidget(filter_container)
        
        # ==================== 数据表格 ====================
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(7)
        
        # 设置表头
        headers = ['时间', 'SKU', '操作类型', '数量变动',
                   '变动后库存', '操作人', '备注']
        self.log_table.setHorizontalHeaderLabels(headers)
        
        # 设置表头字体
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        
        # 设置表格样式
        self.log_table.setStyleSheet('''
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
                gridline-color: #e9ecef;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #f1f3f5;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #dee2e6;
                border-bottom: 2px solid #adb5bd;
                font-weight: 600;
                color: #495057;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #f1f3f5;
                color: #212529;
            }
            QTableWidget::item:selected {
                background-color: #e7f1ff;
                color: #0d6efd;
            }
            QTableWidget::item:hover {
                background-color: #f8f9fa;
            }
        ''')
        
        # 加载列宽配置（支持用户自定义调整）
        width_manager = get_column_width_manager()
        saved_widths = width_manager.get_column_widths('inventory_log_view')
        
        # 使用保存的列宽，如果没有则使用默认值
        if saved_widths and len(saved_widths) == 7:
            column_widths = saved_widths
        else:
            # 默认列宽: [时间, SKU, 操作类型, 数量变动, 变动后库存, 操作者, 备注]
            column_widths = [150, 139, 100, 100, 120, 120, 466]
        
        for i, width in enumerate(column_widths):
            self.log_table.setColumnWidth(i, width)
        
        # 连接列宽改变事件，自动保存配置
        self.log_table.horizontalHeader().sectionResized.connect(
            self._on_column_resized
        )
                
        # 设置表格行高
        self.log_table.verticalHeader().setDefaultSectionSize(45)
        self.log_table.verticalHeader().setVisible(False)
        
        # 设置表格属性
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setShowGrid(True)  # 显示网格线
        self.log_table.setGridStyle(Qt.PenStyle.SolidLine)  # 设置网格线样式
        
        layout.addWidget(self.log_table)
        
        # 🆕 分页控件
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)
    
    def _on_page_changed(self, page: int):
        """分页切换事件 - 使用防抖机制"""
        # 如果正在加载，记录待加载页码
        if self.is_loading:
            self.pending_page = page
            return
        
        # 停止之前的定时器
        self.page_debounce_timer.stop()
        
        # 更新目标页码
        self.pending_page = page
        
        # 启动防抖定时器 (150ms延迟)
        self.page_debounce_timer.start(150)
    
    def _on_column_resized(self, index: int, old_size: int, new_size: int):
        """列宽改变时自动保存配置"""
        try:
            # 获取当前所有列的宽度
            column_count = self.log_table.columnCount()
            widths = []
            for i in range(column_count):
                widths.append(self.log_table.columnWidth(i))
            
            # 保存到配置文件
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('inventory_log_view', widths)
        except Exception as e:
            print(f"保存列宽配置失败: {e}")
    
    def event(self, event):
        """窗口事件过滤器：检测窗口激活/失焦"""
        from PyQt6.QtCore import QEvent
        
        if event.type() == QEvent.Type.WindowActivate:
            if not self.window_has_focus:
                self.window_has_focus = True
                print("✅ 日志窗口激活：恢复自动刷新")
                self.check_and_refresh()
        elif event.type() == QEvent.Type.WindowDeactivate:
            if self.window_has_focus:
                self.window_has_focus = False
                print("😴 日志窗口失焦：暂停自动刷新")
        
        return super().event(event)
    
    def check_and_refresh(self):
        """轻量级询问机制：先问服务端数据是否变化"""
        if not self.window_has_focus:
            return
        
        try:
            status = api_client.get_server_status()
            server_timestamp = status.get('last_change', 0)
            
            if server_timestamp > self.last_server_timestamp:
                print("🔔 日志数据变化，开始刷新...")
                self.last_server_timestamp = server_timestamp
                self.load_logs()
            else:
                print("✅ 日志数据无变化，跳过刷新")
        except Exception as e:
            print(f"⚠️ 询问服务端状态失败: {e}")
        
    def load_logs(self):
        """加载操作记录 - 入口方法 (取消防抖直接加载)"""
        # 取消防抖定时器
        if hasattr(self, 'page_debounce_timer'):
            self.page_debounce_timer.stop()
        
        # 如果有待加载页码，使用待加载页码
        if hasattr(self, 'pending_page') and self.pending_page is not None:
            self.current_page = self.pending_page
            self.pending_page = None
        
        # 直接加载
        self._do_load_logs()
    
    def _do_load_logs(self):
        """实际加载操作记录 - 使用分页API"""
        # 防止重复加载
        if self.is_loading:
            return
        
        # 如果有待加载页码，使用待加载页码
        if self.pending_page is not None:
            self.current_page = self.pending_page
            self.pending_page = None
        
        self.is_loading = True
        self.log_table.setRowCount(0)
        
        try:
            # 默认加载最近7天的记录
            start = datetime.now() - timedelta(days=7)
            end = datetime.now()
            
            # 🆕 通过分页API获取操作记录
            response = api_client.get_operation_logs_paginated(
                page=self.current_page,
                page_size=self.page_size,
                start_date=start,
                end_date=end
            )
            
            # 获取分页数据
            logs = response.get('items', [])
            self.total_items = response.get('total', 0)
            self.total_pages = response.get('total_pages', 0)
            
            # 更新总记录数标签
            if hasattr(self, 'total_label'):
                self.total_label.setText(f'📋 总库存: {self.total_items} 件')
            
            # 更新分页控件
            if hasattr(self, 'pagination'):
                import math
                self.pagination.set_page_info(
                    current_page=self.current_page,
                    total_pages=self.total_pages,
                    total_items=self.total_items,
                    page_size=self.page_size
                )
            
            # 重置加载标志
            self.is_loading = False
            
            # ⚡ 性能优化：禁用UI更新
            self.log_table.setUpdatesEnabled(False)
            self.log_table.blockSignals(True)
            
            try:
                self.log_table.setRowCount(len(logs))
                for row, log in enumerate(logs):
                    # 时间 - 可能是字符串，需要解析
                    time_str = log.get('time', log.get('created_at', ''))
                    if isinstance(time_str, str):
                        try:
                            log_time = datetime.fromisoformat(
                                time_str.replace('Z', '+00:00')
                            )
                        except Exception:
                            log_time = datetime.now()
                    else:
                        log_time = time_str
                    
                    time_item = QTableWidgetItem()
                    time_item.setText(log_time.strftime('%Y-%m-%d %H:%M'))
                    time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # SKU
                    sku_item = QTableWidgetItem()
                    sku_text = str(log.get('sku', '') or '')
                    sku_item.setText(sku_text)
                    if sku_text:
                        sku_item.setFont(QFont('', -1, QFont.Weight.Bold))
                    
                    # 操作类型
                    type_item = QTableWidgetItem()
                    type_item.setText(log.get('operation_type', '未知操作'))
                    type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    # 数量变动
                    quantity_item = QTableWidgetItem()
                    quantity_change = log.get('quantity_change')
                    if quantity_change is not None:
                        quantity = quantity_change
                        quantity_text = (
                            f'+{quantity}' if quantity > 0
                            else str(quantity)
                        )
                        quantity_item.setText(quantity_text)
                        quantity_color = (
                            '#198754' if quantity > 0
                            else '#dc3545'
                        )
                        quantity_item.setForeground(QColor(quantity_color))
                        quantity_item.setFont(QFont('', -1, QFont.Weight.Bold))
                    else:
                        quantity_item.setText('')
                    quantity_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                    
                    # 变动后库存
                    stock_item = QTableWidgetItem()
                    after_stock = log.get('after_stock')
                    if after_stock is not None:
                        stock_item.setText(str(after_stock))
                    else:
                        stock_item.setText('')
                    stock_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                    
                    # 操作人
                    operator_item = QTableWidgetItem()
                    operator_item.setText(str(log.get('operator', '系统') or '系统'))
                    operator_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                    
                    # 备注
                    notes_item = QTableWidgetItem()
                    notes_item.setText(str(log.get('notes', '') or ''))
                    
                    # 设置行颜色
                    if row % 2 == 0:
                        for col in range(7):
                            item = [
                                time_item, sku_item, type_item,
                                quantity_item, stock_item,
                                operator_item, notes_item
                            ][col]
                            item.setBackground(QColor('#f8f9fa'))
                    
                    # 添加到表格
                    self.log_table.setItem(row, 0, time_item)
                    self.log_table.setItem(row, 1, sku_item)
                    self.log_table.setItem(row, 2, type_item)
                    self.log_table.setItem(row, 3, quantity_item)
                    self.log_table.setItem(row, 4, stock_item)
                    self.log_table.setItem(row, 5, operator_item)
                    self.log_table.setItem(row, 6, notes_item)
            finally:
                # ⚡ 恢复UI更新
                self.log_table.blockSignals(False)
                self.log_table.setUpdatesEnabled(True)
            
            # 重新应用筛选条件（如果有）
            self.update_operator_list()  # 更新操作人列表
            self.apply_filters()
                    
        except Exception as e:
            QMessageBox.critical(
                self, '错误',
                f'加载记录失败: {str(e)}\n\n请检查服务器连接是否正常'
            )
        finally:
            # 确保重置加载标志
            self.is_loading = False

    def update_operator_list(self):
        """从表格数据中提取操作人列表并更新下拉框"""
        operators = set()
        
        # 遍历表格提取所有操作人
        for row in range(self.log_table.rowCount()):
            operator_item = self.log_table.item(row, 5)
            if operator_item:
                operator = operator_item.text().strip()
                if operator:  # 不为空
                    operators.add(operator)
        
        # 保存当前选中的值
        current_text = self.operator_combo.currentText()
        
        # 清空并重新填充
        self.operator_combo.blockSignals(True)  # 阻止信号，避免触发筛选
        self.operator_combo.clear()
        self.operator_combo.addItem('全部')
        
        # 添加排序后的操作人列表
        for operator in sorted(operators):
            self.operator_combo.addItem(operator)
        
        # 恢复之前的选择（如果还存在）
        index = self.operator_combo.findText(current_text)
        if index >= 0:
            self.operator_combo.setCurrentIndex(index)
        else:
            self.operator_combo.setCurrentIndex(0)  # 默认选择"全部"
        
        self.operator_combo.blockSignals(False)  # 恢复信号

    def apply_filters(self):
        """应用筛选条件"""
        for row in range(self.log_table.rowCount()):
            show_row = True
            
            # SKU筛选
            if self.sku_input.text():
                sku = self.log_table.item(row, 1).text()
                if self.sku_input.text().lower() not in sku.lower():
                    show_row = False
            
            # 操作类型筛选
            if self.type_combo.currentText() != '全部':
                op_type = self.log_table.item(row, 2).text()
                if op_type != self.type_combo.currentText():
                    show_row = False
            
            # 操作人筛选
            operator_text = self.operator_combo.currentText()
            if operator_text and operator_text != '全部':
                operator = self.log_table.item(row, 5).text()
                if operator_text.lower() not in operator.lower():
                    show_row = False
            
            self.log_table.setRowHidden(row, not show_row)
    
    def export_logs(self):
        """导出日志数据"""
        # 获取可见行的数据
        visible_data = []
        headers = ['时间', 'SKU', '操作类型', '数量变动',
                   '变动后库存', '操作人', '备注']
        
        for row in range(self.log_table.rowCount()):
            if not self.log_table.isRowHidden(row):
                row_data = []
                for col in range(self.log_table.columnCount()):
                    item = self.log_table.item(row, col)
                    row_data.append(item.text() if item else '')
                visible_data.append(row_data)
        
        if not visible_data:
            QMessageBox.warning(self, '警告', '没有可导出的数据！')
            return
        
        # 获取保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '导出记录',
            f'操作记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'CSV Files (*.csv)'
        )
        
        if file_path:
            try:
                # 导出到CSV
                import csv
                with open(
                    file_path, 'w', newline='', encoding='utf-8'
                ) as csvfile:
                    writer = csv.writer(csvfile)
                    # 写入表头
                    writer.writerow(headers)
                    # 写入数据
                    writer.writerows(visible_data)
                
                QMessageBox.information(self, '成功', '记录导出成功！')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
    
    def clear_old_logs(self, days: int):
        """清空指定天数之前的操作审计日志（不影响库存数据）"""
        # 先获取将要删除的记录数量
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            # 调用API查询将要删除的数量
            count_result = api_client.get_operation_logs_count(cutoff_date)
            delete_count = count_result.get('count', 0)
        except Exception:
            delete_count = 0
        
        # 显示确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('确认清空操作审计日志')
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # 设置详细说明
        msg_box.setText(
            f'<h3>确定要清空 {days} 天前的操作审计日志吗？</h3>'
        )
        
        info_text = (
            f'<p><b>即将删除：</b>{delete_count} 条操作审计日志</p>'
            f'<p><b>截止日期：</b>'
            f'{cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}</p>'
            '<hr>'
            '<p style="color: #198754;"><b>✅ 不会影响：</b></p>'
            '<ul>'
            '<li>产品库存数据（完全保留）</li>'
            '<li>库存变动历史记录（永久保留）</li>'
            '<li>销售订单数据（完全保留）</li>'
            '</ul>'
            '<p style="color: #dc3545;"><b>⚠️ 将会删除：</b></p>'
            '<ul>'
            '<li>操作审计日志（谁在什么时候做了什么）</li>'
            '<li>仅用于审计跟踪，不影响业务数据</li>'
            '</ul>'
            '<p style="color: #6c757d; font-size: 11px;">'
            '<i>提示：此操作不可恢复，但不会影响任何业务数据</i>'
            '</p>'
        )
        
        msg_box.setInformativeText(info_text)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 调用API清空记录
                result = api_client.clear_old_logs(cutoff_date)
                
                if result.get('success'):
                    deleted_count = result.get('deleted_count', 0)
                    QMessageBox.information(
                        self,
                        '清空成功',
                        f'<h3>✅ 成功清空 {deleted_count} 条操作审计日志</h3>'
                        '<p>您的库存数据完全未受影响！</p>'
                    )
                    # 刷新列表
                    self.load_logs()
                else:
                    QMessageBox.warning(
                        self,
                        '清空失败',
                        result.get('message', '未知错误')
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    '错误',
                    f'清空操作记录失败: {str(e)}'
                )
