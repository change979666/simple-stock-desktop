from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFileDialog,
    QLabel, QMessageBox, QComboBox, QFrame,
    QLineEdit, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
import pandas as pd
from datetime import datetime, timedelta

from utils.operator import get_operator_info
from utils.sku_processor import process_wholesale_sku
from config.column_width_manager import get_column_width_manager
from utils.cache import data_cache  # 全局缓存
from utils.async_loader import AsyncDataLoader
from gui.widgets.pagination import PaginationWidget
from utils.type_safe import safe_get_attr


def natural_sort_key(text: str) -> list:
    """自然排序键（处理带数字的字符串）"""
    import re
    return [
        int(t) if t.isdigit() else t.lower()
        for t in re.split(r'(\d+)', str(text))
    ]


class SalesView(QWidget):
    # 定义信号：订单导入成功时触发
    orders_imported = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.async_loader = AsyncDataLoader()  # 异步加载器
        # 初始化日期范围为最近30天(而不是今天)
        from datetime import timedelta
        today = datetime.now().date()
        self.current_start_date = today - timedelta(days=29)
        self.current_end_date = today
        
        # 分页状态
        self.current_page = 1
        self.page_size = 50
        self.total_orders = 0
        
        # 搜索状态
        self.search_keyword = ''
        
        self.init_ui()

    def init_ui(self):
        """初始化现代化UI布局 - 紧凑简洁的设计"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 创建现代化工具栏
        toolbar_frame = self._create_modern_toolbar()
        layout.addWidget(toolbar_frame)
        
        # 创建表格容器
        table_container = self._create_table_container()
        layout.addWidget(table_container, 1)  # 表格占据剩余空间
        
        # 加载数据
        self.load_sales()

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
        toolbar.setSpacing(10)
        toolbar.setContentsMargins(10, 8, 10, 8)

        # 时间范围显示标签
        self.date_range_label = QLabel('📅 最近30天')
        self.date_range_label.setStyleSheet("""
            QLabel {
                color: #1890ff;
                font-weight: bold;
                padding: 8px 16px;
                border: 2px solid #91d5ff;
                border-radius: 6px;
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f9ff, stop:1 #e6f7ff
                );
                font-size: 13px;
            }
        """)
        toolbar.addWidget(self.date_range_label)

        # 快捷时间选择区域
        period_frame = QFrame()
        period_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fafafa, stop:1 #f0f0f0
                );
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        period_layout = QHBoxLayout(period_frame)
        period_layout.setSpacing(10)
        period_layout.setContentsMargins(10, 6, 10, 6)
        
        # 时间标签样式
        label_style = """
            QLabel {
                color: #595959;
                font-weight: bold;
                font-size: 12px;
            }
        """
        
        # 快捷时间选择
        period_label = QLabel('⚡ 快捷:')
        period_label.setStyleSheet(label_style)
        period_layout.addWidget(period_label)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            '今天', '昨天', '最近7天', '最近30天',
            '本月', '上月', '今年'
        ])
        # 默认选中"最近30天"
        self.period_combo.setCurrentText('最近30天')
        self.period_combo.currentTextChanged.connect(
            self.on_period_changed
        )
        self.period_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #40a9ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        period_layout.addWidget(self.period_combo)
        
        toolbar.addWidget(period_frame)
        
        # 搜索框
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(8)
        search_layout.setContentsMargins(10, 6, 10, 6)
        
        search_label = QLabel('🔍 搜索:')
        search_label.setStyleSheet(label_style)
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入客户名或订单号（按回车搜索）...')
        self.search_input.returnPressed.connect(self.on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
                min-width: 200px;
            }
            QLineEdit:hover {
                border-color: #40a9ff;
            }
            QLineEdit:focus {
                border-color: #1890ff;
                outline: none;
            }
        """)
        search_layout.addWidget(self.search_input)
        
        # 清空搜索按钮
        clear_search_btn = QPushButton('✕')
        clear_search_btn.setToolTip('清空搜索')
        clear_search_btn.clicked.connect(self.clear_search)
        clear_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #ff4d4f;
                color: white;
                border-color: #ff4d4f;
            }
        """)
        search_layout.addWidget(clear_search_btn)
        
        toolbar.addWidget(search_frame)
        toolbar.addStretch()
        
        # 操作按钮组
        self.refresh_btn = self._create_action_button(
            '🔄 刷新', '#1890ff', '#096dd9'
        )
        self.refresh_btn.clicked.connect(self.load_sales)
        toolbar.addWidget(self.refresh_btn)
        
        self.import_btn = self._create_action_button(
            '📥 导入', '#52c41a', '#389e0d'
        )
        self.import_btn.clicked.connect(self.import_orders)
        toolbar.addWidget(self.import_btn)
        
        self.delete_btn = self._create_action_button(
            '🗑️ 删除', '#ff4d4f', '#cf1322'
        )
        self.delete_btn.clicked.connect(self.delete_selected_order)
        self.delete_btn.setEnabled(False)
        toolbar.addWidget(self.delete_btn)
        
        return toolbar_frame
    
    def _create_action_button(self, text, normal_color, hover_color):
        """创建统一样式的操作按钮"""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {normal_color},
                    stop:1 {hover_color}
                );
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: {normal_color};
            }}
            QPushButton:pressed {{
                background: {hover_color};
                padding: 9px 17px 7px 19px;
            }}
            QPushButton:disabled {{
                background: #d9d9d9;
                color: #8c8c8c;
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn
    
    def _create_table_container(self):
        """创建现代化表格容器"""
        container = QFrame()
        container.setObjectName("tableContainer")
        container.setStyleSheet("""
            QFrame#tableContainer {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 销售记录树形表格
        self.sales_table = QTreeWidget()
        self.sales_table.setColumnCount(7)
        
        # 设置选择模式
        self.sales_table.setSelectionMode(
            QTreeWidget.SelectionMode.SingleSelection
        )
        self.sales_table.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows
        )
        
        # 设置表头
        headers = [
            '📋 订单号', '👤 客户', '📦 SKU', '🔢 数量',
            '💰 单价', '💵 总额', '📅 时间'
        ]
        self.sales_table.setHeaderLabels(headers)
        
        # 设置现代化字体
        font = QFont()
        font.setFamily('Microsoft YaHei UI')
        font.setPointSize(10)
        self.sales_table.setFont(font)
        
        # 设置表头样式
        header = self.sales_table.header()
        header.setFont(font)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QHeaderView::section {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fafafa, stop:1 #f0f0f0
                );
                color: #262626;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #e8e8e8;
                border-bottom: 2px solid #1890ff;
                font-weight: bold;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:1 #e6e6e6
                );
            }
        """)
        
        # 设置表格现代化样式
        # 注意: 使用 rgba 半透明叠加，保留代码设置的背景色
        self.sales_table.setStyleSheet("""
            QTreeWidget {
                border: none;
                background-color: white;
                alternate-background-color: #fafafa;
                outline: none;
            }
            QTreeWidget::item {
                padding: 10px 6px;
                min-height: 36px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:hover {
                /* 半透明蓝色叠加在原背景上 */
                background-color: rgba(33, 150, 243, 0.08);
            }
            QTreeWidget::item:selected {
                /* 半透明蓝色叠加在原背景上 */
                background-color: rgba(33, 150, 243, 0.15);
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
        saved_widths = width_manager.get_column_widths('sales_view')
        
        # 使用保存的列宽，如果没有则使用默认值
        if saved_widths and len(saved_widths) == 7:
            column_widths = saved_widths
        else:
            # 默认列宽: [订单号, 客户, SKU, 数量, 单价, 总额, 时间]
            column_widths = [235, 218, 170, 80, 80, 100, 260]
        
        for i, width in enumerate(column_widths):
            self.sales_table.setColumnWidth(i, width)
        
        # 连接列宽改变事件，自动保存配置
        header = self.sales_table.header()
        header.sectionResized.connect(self._on_column_resized)
            
        # 选择改变事件
        self.sales_table.itemSelectionChanged.connect(
            self.on_selection_changed
        )
        
        # 调试：确认信号已连接
        print("[DEBUG] 销售管理页面已初始化，信号已连接")
        print(f"[DEBUG] 删除按钮初始状态: {self.delete_btn.isEnabled()}")
        
        layout.addWidget(self.sales_table)
        
        # 添加分页控件
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)
        
        return container
    
    def _on_page_changed(self, page: int):
        """页码变更回调"""
        self.current_page = page
        self.load_sales()
    
    def set_date_range(self, start_date, end_date):
        """设置日期范围（供其他视图调用）"""
        try:
            # **先阻止信号**，避免任何可能的递归调用
            self.period_combo.blockSignals(True)
            
            # 直接保存日期范围
            self.current_start_date = start_date
            self.current_end_date = end_date
            
            # 检查是否匹配预设时间段
            days_diff = (end_date - start_date).days
            today = datetime.now().date()
            
            if start_date == end_date:
                if start_date == today:
                    self.period_combo.setCurrentText('今天')
                    self.date_range_label.setText('📅 今天')
                elif start_date == (today - timedelta(days=1)):
                    self.period_combo.setCurrentText('昨天')
                    self.date_range_label.setText('📅 昨天')
                else:
                    # 其他单日
                    self.period_combo.setCurrentText('自定义')
                    self.date_range_label.setText(
                        f'📅 {start_date.strftime("%Y-%m-%d")}'
                    )
            elif end_date == today:
                if days_diff == 6:
                    self.period_combo.setCurrentText('最近7天')
                    self.date_range_label.setText('📅 最近7天')
                elif days_diff == 29:
                    self.period_combo.setCurrentText('最近30天')
                    self.date_range_label.setText('📅 最近30天')
                else:
                    # 自定义日期范围
                    self.period_combo.setCurrentText('自定义')
                    self.date_range_label.setText(
                        f'📅 {start_date.strftime("%m-%d")} ~ {end_date.strftime("%m-%d")}'
                    )
            else:
                # 自定义日期范围
                self.period_combo.setCurrentText('自定义')
                self.date_range_label.setText(
                    f'📅 {start_date.strftime("%m-%d")} ~ {end_date.strftime("%m-%d")}'
                )
            
            # **恢复信号**
            self.period_combo.blockSignals(False)
            
            # **最后更新数据显示**
            self.load_sales()
            
        except Exception as e:
            print(f"设置日期范围时出错: {e}")
            import traceback
            traceback.print_exc()
            # 确保恢复信号
            try:
                self.period_combo.blockSignals(False)
            except Exception:
                pass

    def on_period_changed(self, period: str):
        """处理快捷时间段选择"""
        from datetime import timedelta
        
        today = datetime.now().date()
        
        if period == '今天':
            start_date = end_date = today
        elif period == '昨天':
            yesterday = today - timedelta(days=1)
            start_date = end_date = yesterday
        elif period == '最近7天':
            start_date = today - timedelta(days=6)
            end_date = today
        elif period == '最近30天':
            start_date = today - timedelta(days=29)
            end_date = today
        elif period == '本月':
            # 本月第一天到今天
            start_date = today.replace(day=1)
            end_date = today
        elif period == '上月':
            # 上月第一天到最后一天
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            start_date = last_day_last_month.replace(day=1)
            end_date = last_day_last_month
        elif period == '今年':
            # 今年第一天到今天
            start_date = today.replace(month=1, day=1)
            end_date = today
        else:
            start_date = end_date = today
        
        # 保存当前选择的日期范围
        self.current_start_date = start_date
        self.current_end_date = end_date
        
        # 更新时间范围标签
        self.date_range_label.setText(f'📅 {period}')
        
        # 重新加载数据
        self.load_sales()
    
    def on_search_changed(self):
        """搜索回调：重新从后端查询匹配的数据"""
        new_keyword = self.search_input.text().strip()
        
        # 如果搜索关键词改变，重置到第一页
        if new_keyword != self.search_keyword:
            self.search_keyword = new_keyword
            self.current_page = 1
            
            # 搜索模式提示
            if self.search_keyword:
                print(f"🔍 搜索订单: '{self.search_keyword}'")
            else:
                print("🔄 清空搜索，恢复时间范围数据")
            
            self.load_sales()
    
    def clear_search(self):
        """清空搜索"""
        self.search_input.clear()
        self.search_keyword = ''
        self.current_page = 1
        # 清空搜索后重新加载时间范围内的数据
        self.load_sales()
    
    def load_sales_by_search(self, search_text: str):
        """根据搜索文本从数据库加载订单（不限时间范围）"""
        try:
            if not hasattr(self, 'sales_table') or not self.sales_table:
                return
                
            try:
                # 阻止信号
                self.sales_table.blockSignals(True)
                self.sales_table.clear()
            except (RuntimeError, AttributeError):
                return
            
            from utils.data_access import dal
            
            # 从数据库搜索订单（不限时间范围）
            orders = dal.search_sales_orders(search_text)
            
            # 帮助函数:支持字典和对象两种数据格式
            def get_attr(obj, attr, default=None):
                if isinstance(obj, dict):
                    return obj.get(attr, default)
                return getattr(obj, attr, default)
            
            # 显示搜索结果（复用 load_sales 的显示逻辑）
            for order in orders:
                # 创建订单父节点
                order_item = QTreeWidgetItem()
                
                # 计算订单总件数
                order_items = get_attr(order, 'items', [])
                # 处理items可能是方法的情况
                if callable(order_items):
                    order_items = []
                total_items = sum(
                    get_attr(item, 'quantity', 0) for item in order_items
                )
                
                # 判断是否为批发订单（检查订单项中是否包含×5标记）
                is_wholesale = False
                for item in order_items:
                    parent_sku = str(get_attr(item, 'parent_sku', ''))
                    if '×5' in parent_sku:
                        is_wholesale = True
                        break
                
                # 设置订单信息(带图标和格式化)
                order_num = get_attr(order, 'order_number', '')
                customer = get_attr(order, 'customer_name', '')
                order_item.setText(0, f"📋 {order_num}")
                order_item.setText(1, f"👤 {customer}")
                order_item.setText(2, f"{len(order_items)}个SKU")
                order_item.setText(3, f"📦 {total_items}件")
                order_item.setText(4, "-")
                total_amt = get_attr(order, 'total_amount', 0)
                order_item.setText(5, f"💰 ¥{total_amt:.2f}")
                
                order_date = get_attr(order, 'order_date')
                # 处理日期: 可能是datetime对象或ISO字符串
                if order_date:
                    if isinstance(order_date, str):
                        try:
                            # ISO字符串转datetime
                            from datetime import datetime as dt
                            date_obj = dt.fromisoformat(order_date)
                            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                            order_item.setText(6, date_str)
                        except Exception:
                            # 如果转换失败,直接显示原始字符串的简化版
                            short_date = order_date[:16]
                            if len(order_date) >= 16:
                                order_item.setText(6, short_date)
                            else:
                                order_item.setText(6, order_date)
                    elif hasattr(order_date, 'strftime'):
                        # datetime对象
                        date_str = order_date.strftime('%Y-%m-%d %H:%M')
                        order_item.setText(6, date_str)
                    else:
                        order_item.setText(6, str(order_date))
                else:
                    order_item.setText(6, '')
                
                # 设置订单行字体(粗体)
                font_bold = QFont()
                font_bold.setFamily('Microsoft YaHei UI')
                font_bold.setPointSize(11)
                font_bold.setBold(True)
                
                for col in range(7):
                    order_item.setFont(col, font_bold)
                    # 根据订单类型设置不同背景色
                    if is_wholesale:
                        # 批发订单使用浅橙色背景
                        order_item.setBackground(col, QColor('#fff7e6'))
                    else:
                        # 普通订单使用浅蓝色背景
                        order_item.setBackground(col, QColor('#f0f9ff'))
                
                # 设置不同列的颜色强调
                order_item.setForeground(0, QColor('#1890ff'))  # 订单号
                order_item.setForeground(1, QColor('#52c41a'))  # 客户
                order_item.setForeground(3, QColor('#722ed1'))  # 数量
                order_item.setForeground(5, QColor('#fa8c16'))  # 金额
                order_item.setForeground(6, QColor('#8c8c8c'))  # 时间
                
                # 添加订单项子节点
                for idx, item in enumerate(order_items, 1):
                    order_detail = QTreeWidgetItem()
                    
                    # 设置子项信息(带缩进符号)
                    order_detail.setText(0, f"  └─ #{idx}")
                    order_detail.setText(1, "-")
                    variant_sku = get_attr(item, 'variant_sku', '')
                    order_detail.setText(2, variant_sku)
                    qty = get_attr(item, 'quantity', 0)
                    order_detail.setText(3, f"{qty} 件")
                    
                    item_price = get_attr(item, 'item_price')
                    if item_price is not None:
                        order_detail.setText(4, f"¥{item_price:.2f}")
                        # 计算小计
                        subtotal = item_price * qty
                        order_detail.setText(5, f"¥{subtotal:.2f}")
                    else:
                        order_detail.setText(4, '-')
                        order_detail.setText(5, '-')
                    
                    order_detail.setText(6, "-")
                    
                    # 子项字体和样式
                    detail_font = QFont()
                    detail_font.setFamily('Microsoft YaHei UI')
                    detail_font.setPointSize(10)
                    
                    # SKU使用粗体
                    sku_font = QFont(detail_font)
                    sku_font.setBold(True)
                    order_detail.setFont(2, sku_font)
                    
                    # 设置子项颜色
                    order_detail.setForeground(2, QColor('#1890ff'))
                    if item_price is not None:
                        order_detail.setForeground(4, QColor('#52c41a'))
                        order_detail.setForeground(5, QColor('#fa8c16'))
                    
                    # 子项浅色背景
                    lighter_bg = QColor('#fafafa')
                    for col in range(7):
                        order_detail.setBackground(col, lighter_bg)
                    
                    # 将子项添加到订单项
                    order_item.addChild(order_detail)
                
                # 将订单项添加到树形表格
                self.sales_table.addTopLevelItem(order_item)
                
                # 默认折叠订单（性能优化）
                order_item.setExpanded(False)
            
            self.sales_table.resizeColumnToContents(0)  # 订单号列
            
            # 更新标题提示
            count = len(orders)
            self.date_range_label.setText(f'🔍 搜索结果: {count} 笔订单')
            
        except Exception as e:
            print(f"搜索订单时出错: {e}")
            QMessageBox.critical(self, '错误', f'搜索订单失败: {str(e)}')
        finally:
            try:
                self.sales_table.blockSignals(False)
            except Exception:
                pass

    def load_sales(self):
        """加载销售记录（分页+异步加载优化）"""
        # 显示加载状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText('⏳ 加载中...')
        
        # 清空表格
        if hasattr(self, 'sales_table') and self.sales_table:
            try:
                self.sales_table.blockSignals(True)
                self.sales_table.clear()
                self.sales_table.blockSignals(False)
            except (RuntimeError, AttributeError):
                pass
        
        def load_data():
            """后台加载销售数据（分页）"""
            # 使用内部保存的日期范围
            if not hasattr(self, 'current_start_date'):
                today = datetime.now().date()
                self.current_start_date = today
                self.current_end_date = today
            
            start = datetime.combine(self.current_start_date, datetime.min.time())
            end = datetime.combine(self.current_end_date, datetime.max.time())
            
            # 从服务端获取分页数据
            from utils.data_access import dal
            result = dal.get_sales_orders_paginated(
                page=self.current_page,
                page_size=self.page_size,
                start_date=start,
                end_date=end,
                search=self.search_keyword if self.search_keyword else None
            )
            print(f"📝 加载第{self.current_page}页订单, 共{result.get('total', 0)}条")
            return result
        
        # 启动异步加载
        self.async_loader.load_data(
            load_func=load_data,
            on_success=self._on_sales_loaded,
            on_error=self._on_load_error
        )
    
    def _on_sales_loaded(self, result):
        """销售数据加载成功回调（分页结果）"""
        try:
            if not hasattr(self, 'sales_table') or not self.sales_table:
                return
            
            # 提取分页数据
            orders = result.get('items', [])
            total = result.get('total', 0)
            self.total_orders = total
            
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
                
            try:
                # 阻止信号,避免触发不必要的事件
                self.sales_table.blockSignals(True)
                self.sales_table.clear()
            except (RuntimeError, AttributeError):
                return
            
            # 帮助函数:支持字典和对象两种数据格式
            def get_attr(obj, attr, default=None):
                if isinstance(obj, dict):
                    return obj.get(attr, default)
                return getattr(obj, attr, default)
            
            for order in orders:
                # 创建订单父节点
                order_item = QTreeWidgetItem()
                
                # 计算订单总件数
                order_items = get_attr(order, 'items', [])
                # 处理items可能是方法的情况
                if callable(order_items):
                    order_items = []
                total_items = sum(get_attr(item, 'quantity', 0) for item in order_items)
                
                # 判断是否为批发订单（检查订单项中是否包含×5标记）
                is_wholesale = False
                for item in order_items:
                    parent_sku = str(get_attr(item, 'parent_sku', ''))
                    if '×5' in parent_sku:
                        is_wholesale = True
                        break
                
                # 设置订单信息(带图标和格式化)
                order_item.setText(0, f"📋 {get_attr(order, 'order_number', '')}")
                order_item.setText(1, f"👤 {get_attr(order, 'customer_name', '')}")
                order_item.setText(2, f"{len(order_items)}个SKU")
                order_item.setText(3, f"📦 {total_items}件")
                order_item.setText(4, "-")
                order_item.setText(
                    5, f"💰 ¥{get_attr(order, 'total_amount', 0):.2f}"
                )
                order_date = get_attr(order, 'order_date')
                # 处理日期: 可能是datetime对象或ISO字符串
                if order_date:
                    if isinstance(order_date, str):
                        try:
                            # ISO字符串转datetime
                            from datetime import datetime as dt
                            date_obj = dt.fromisoformat(order_date)
                            date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                            order_item.setText(6, date_str)
                        except Exception:
                            # 如果转换失败,直接显示原始字符串的简化版
                            short_date = order_date[:16]
                            if len(order_date) >= 16:
                                order_item.setText(6, short_date)
                            else:
                                order_item.setText(6, order_date)
                    elif hasattr(order_date, 'strftime'):
                        # datetime对象
                        date_str = order_date.strftime('%Y-%m-%d %H:%M')
                        order_item.setText(6, date_str)
                    else:
                        order_item.setText(6, str(order_date))
                else:
                    order_item.setText(6, '')
                
                # 设置订单行字体(粗体)
                font_bold = QFont()
                font_bold.setFamily('Microsoft YaHei UI')
                font_bold.setPointSize(11)
                font_bold.setBold(True)
                
                for col in range(7):
                    order_item.setFont(col, font_bold)
                    # 根据订单类型设置不同背景色
                    if is_wholesale:
                        # 批发订单使用浅橙色背景
                        order_item.setBackground(col, QColor('#fff7e6'))
                    else:
                        # 普通订单使用浅蓝色背景
                        order_item.setBackground(col, QColor('#f0f9ff'))
                
                # 设置不同列的颜色强调
                order_item.setForeground(0, QColor('#1890ff'))  # 订单号
                order_item.setForeground(1, QColor('#52c41a'))  # 客户
                order_item.setForeground(3, QColor('#722ed1'))  # 数量
                order_item.setForeground(5, QColor('#fa8c16'))  # 金额
                order_item.setForeground(6, QColor('#8c8c8c'))  # 时间
                
                # 添加订单项子节点
                for idx, item in enumerate(order_items, 1):
                    order_detail = QTreeWidgetItem()
                    
                    # 设置子项信息(带缩进符号)
                    order_detail.setText(0, f"  └─ #{idx}")
                    order_detail.setText(1, "-")
                    order_detail.setText(2, get_attr(item, 'variant_sku', ''))
                    order_detail.setText(3, f"{get_attr(item, 'quantity', 0)} 件")
                    
                    item_price = get_attr(item, 'item_price')
                    if item_price is not None:
                        order_detail.setText(
                            4, f"¥{item_price:.2f}"
                        )
                        # 计算小计
                        subtotal = item_price * get_attr(item, 'quantity', 0)
                        order_detail.setText(
                            5, f"¥{subtotal:.2f}"
                        )
                    else:
                        order_detail.setText(4, '-')
                        order_detail.setText(5, '-')
                    
                    order_detail.setText(6, "-")
                    
                    # 子项字体和样式
                    detail_font = QFont()
                    detail_font.setFamily('Microsoft YaHei UI')
                    detail_font.setPointSize(10)
                    
                    # SKU使用粗体
                    sku_font = QFont(detail_font)
                    sku_font.setBold(True)
                    order_detail.setFont(2, sku_font)
                    
                    # 设置子项颜色
                    order_detail.setForeground(2, QColor('#1890ff'))
                    if item_price is not None:
                        order_detail.setForeground(4, QColor('#52c41a'))
                        order_detail.setForeground(5, QColor('#fa8c16'))
                    
                    # 子项浅色背景
                    lighter_bg = QColor('#fafafa')
                    for col in range(7):
                        order_detail.setBackground(col, lighter_bg)
                    
                    # 将子项添加到订单项
                    order_item.addChild(order_detail)
                
                # 将订单项添加到树形表格
                self.sales_table.addTopLevelItem(order_item)
                
                # 默认折叠订单（性能优化）
                order_item.setExpanded(False)
            
            self.sales_table.resizeColumnToContents(0)  # 订单号列
            
            # 在状态栏居中显示刷新成功消息
            main_window = self.window()
            if hasattr(main_window, 'center_message_label'):
                main_window.center_message_label.setText(
                    f'✅ 销售订单刷新成功，已加载 {len(orders)} 笔订单'
                )
                # 3秒后清除消息
                QTimer.singleShot(
                    3000,
                    lambda: main_window.center_message_label.setText('')
                )
            
        except Exception as e:
            print(f"渲染销售记录时出错: {e}")
            QMessageBox.critical(
                self,
                '渲染失败',
                f'无法渲染销售订单:\n\n{str(e)}\n\n'
                '数据已加载但渲染时出现错误'
            )
        finally:
            # 恢复信号
            if hasattr(self, 'sales_table') and self.sales_table:
                try:
                    self.sales_table.blockSignals(False)
                except (RuntimeError, AttributeError):
                    pass
            
            # 恢复按钮状态
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(True)
                self.refresh_btn.setText('刷新')
    
    def _on_load_error(self, error_msg):
        """销售数据加载失败回调"""
        print(f"加载销售记录时出错: {error_msg}")
        QMessageBox.critical(
            self,
            '加载失败',
            f'无法加载销售订单:\n\n{error_msg}\n\n'
            '可能原因:\n'
            '• 网络连接中断\n'
            '• 服务器未响应\n'
            '• 数据格式错误\n\n'
            '请检查网络连接和服务器状态后重试'
        )
        
        # 恢复按钮状态
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText('刷新')
    
    def import_orders(self):
        """导入订单Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择订单文件',
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
            
            print(f"销售导入 - 原始列名: {list(df.columns)}")
            
            # 处理多行标题格式和标准化列名
            column_mapping = {}
            for col in df.columns:
                col_str = str(col).strip()
                
                # 处理多行标题（提取第一行作为主要标识）
                if '\n' in col_str:
                    main_part = col_str.split('\n')[0].strip()
                else:
                    main_part = col_str
                    
                # 标准化映射 - 识别订单字段
                if main_part in ['sku', 'sku*', '产品编号', 'SKU']:
                    column_mapping[col] = 'sku'
                elif main_part in ['order_number', 'order_id', 'order_id*', '订单号', '订单编号']:
                    column_mapping[col] = 'order_number'
                elif main_part in ['customer_name', 'customer_name*', '客户名称', '客户姓名']:
                    column_mapping[col] = 'customer_name'
                elif main_part in ['order_date', 'order_date*', '订单日期', '日期']:
                    column_mapping[col] = 'order_date'
                elif main_part in ['quantity', 'quantity*', '数量']:
                    column_mapping[col] = 'quantity'
                elif main_part in ['price', 'price*', 'selling_price', 'selling_price*', '单价', '价格', '销售单价']:
                    column_mapping[col] = 'selling_price'
                elif main_part in ['total_amount', 'total_price', 'order_total', '订单总价', '总价', '订单金额']:
                    column_mapping[col] = 'total_amount'
                else:
                    # 保持原列名
                    column_mapping[col] = main_part
            
            # 应用列名映射
            df = df.rename(columns=column_mapping)
            print(f"销售导入 - 映射后列名: {list(df.columns)}")
            
            # 过滤示例行（包含*的行）
            original_count = len(df)
            # 过滤各个关键字段中包含*的行
            mask1 = ~df['sku'].astype(str).str.contains(r'\*', na=False, regex=True)
            mask2 = ~df['order_number'].astype(str).str.contains(r'\*', na=False, regex=True)
            df = df[mask1 & mask2]
            
            if len(df) == 0:
                QMessageBox.warning(
                    self,
                    '导入警告',
                    '没有找到有效的订单数据，请确认Excel文件包含有效数据行'
                )
                return
                
            if len(df) < original_count:
                print(f"销售导入 - 已过滤 {original_count - len(df)} 行示例数据")
            
            # 验证必需的列（基础字段）
            required_columns = [
                'sku', 'order_number', 'customer_name',
                'order_date', 'quantity'
            ]
            
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
                    f'请确保Excel文件包含以下必需字段:\n'
                    f'- sku: 产品编号（或sku*）\n'
                    f'- order_number: 订单号（或order_number*）\n'
                    f'- customer_name: 客户名称（或customer_name*）\n'
                    f'- order_date: 订单日期（或order_date*）\n'
                    f'- quantity: 数量（或quantity*）\n\n'
                    f'💡 价格字段（至少需要以下之一）:\n'
                    f'- selling_price: 销售单价\n'
                    f'- net_selling_price: 净销售价格\n'
                    f'- total_amount: 订单总价\n\n'
                    f'📝 价格优先级:\n'
                    f'1. 有单价 > 0 → 使用单价自动计算\n'
                    f'2. 有订单总价 → 使用订单总价\n'
                    f'3. 两者都有 → 使用订单总价（支持优惠）'
                )
                return
            
            # 验证价格字段（必须包含 selling_price 和 total_amount）
            required_price_fields = ['selling_price', 'total_amount']
            missing_fields = [
                f for f in required_price_fields if f not in df.columns
            ]
            
            if missing_fields:
                QMessageBox.critical(
                    self,
                    '导入错误',
                    f'Excel文件缺少必需的价格字段:\n\n'
                    f'缺失字段: {", ".join(missing_fields)}\n\n'
                    f'必需字段:\n'
                    f'- selling_price（销售单价）\n'
                    f'- total_amount（订单总价）'
                )
                return
            
            # 开始导入 - 使用DAL层统一接口
            from utils.data_access import dal
            from gui.progress_dialog import ProgressDialog
            from PyQt6.QtWidgets import QApplication
            
            operator_info = get_operator_info()
            errors = []
            warnings = []  # 库存不足警告（不阻止导入）
            skipped_count = 0
            
            # 创建进度对话框
            progress = ProgressDialog(
                self,
                title="导入销售订单",
                message="正在初始化..."
            )
            progress.show()
            QApplication.processEvents()
            
            # 按订单号分组
            orders_df = df.groupby(['order_number', 'customer_name', 'order_date'])
            total_orders = len(orders_df)
            
            # 预验证所有SKU - 通过DAL获取所有产品
            all_skus = set(df['sku'].dropna().unique())
            
            # 获取所有产品用于SKU映射（使用缓存优化）
            try:
                # 更新进度提示
                progress.set_message(f"正在加载产品信息...\n共 {total_orders} 笔订单待导入")
                progress.set_indeterminate()
                QApplication.processEvents()
                
                # 优先从缓存获取，避免重复加载
                from utils.cache import data_cache
                cache_key = 'sales_import_sku_map'
                cached_data = data_cache.get(cache_key)
                
                if cached_data:
                    sku_lowercase_map = cached_data['sku_map']
                    variant_stock_map = cached_data['stock_map']
                    print("✅ 使用缓存的SKU映射数据")
                else:
                    all_products = dal.get_all_products()
                    sku_lowercase_map = {}
                    variant_stock_map = {}
                    
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
                                # 使用小写作为key进行映射
                                sku_lower = sku.lower()
                                sku_lowercase_map[sku_lower] = sku
                                # 获取库存 - 使用原始SKU和小写SKU都存一份
                                stock = get_attr(variant, 'current_stock', 0)
                                variant_stock_map[sku] = stock
                                variant_stock_map[sku_lower] = stock  # 同时用小写key存储
                    
                    # 缓存SKU映射数据（5分钟有效期）
                    data_cache.set(cache_key, {
                        'sku_map': sku_lowercase_map,
                        'stock_map': variant_stock_map
                    }, ttl=300)
                    print(f"✅ 已缓存 {len(sku_lowercase_map)} 个SKU映射")
                
                # 更新进度提示
                progress.set_message(
                    f"正在验证 {len(all_skus)} 个SKU...\n"
                    f"共 {total_orders} 笔订单待导入"
                )
                QApplication.processEvents()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    '错误',
                    f'获取产品信息失败: {str(e)}'
                )
                return
            
            # 验证SKU（不区分大小写）
            invalid_skus = []
            for sku in all_skus:
                processed_sku, _ = process_wholesale_sku(sku)
                if processed_sku.lower() not in sku_lowercase_map:
                    invalid_skus.append(sku)
            
            if invalid_skus:
                errors.append(
                    f'以下SKU不存在，将被跳过:\n'
                    f'{", ".join(sorted(invalid_skus))}'
                )
            
            # 构建订单数据列表
            orders_to_import = []
            
            # 设置进度条范围
            progress.set_range(0, total_orders)
            progress.set_message(f"正在处理订单数据...\n共 {total_orders} 笔订单")
            QApplication.processEvents()
            
            processed_count = 0
            for (order_number, customer_name, order_date), items in orders_df:
                try:
                    # 更新进度
                    processed_count += 1
                    progress.update_progress(
                        processed_count,
                        total_orders,
                        f"正在处理订单: {order_number}"
                    )
                    QApplication.processEvents()
                    
                    if not customer_name or pd.isna(customer_name):
                        errors.append(f'订单 {order_number}: 客户名称不能为空')
                        continue
                    
                    try:
                        order_date_obj = pd.to_datetime(order_date)
                    except Exception:
                        errors.append(f'订单 {order_number}: 订单日期格式无效')
                        continue
                    
                    # 处理订单项
                    order_items_list = []
                    
                    for _, item in items.iterrows():
                        # 获取和处理SKU
                        raw_sku = str(item['sku']).strip()
                        if not raw_sku or raw_sku == 'nan':
                            continue
                        
                        # 处理批发SKU
                        processed_sku, base_qty = process_wholesale_sku(raw_sku)
                        
                        # 不区分大小写查找SKU
                        actual_sku = sku_lowercase_map.get(
                            processed_sku.lower()
                        )
                        if not actual_sku:
                            errors.append(
                                f'订单 {order_number}: '
                                f'SKU {processed_sku} 不存在'
                            )
                            continue
                        
                        # 获取和处理数量
                        quantity_str = str(item['quantity']).strip()
                        if not quantity_str or quantity_str == 'nan':
                            errors.append(
                                f'订单 {order_number}: '
                                f'SKU {raw_sku} 数量为空'
                            )
                            continue
                        
                        try:
                            order_qty = int(float(quantity_str))
                            if order_qty <= 0:
                                errors.append(
                                    f'订单 {order_number}: '
                                    f'SKU {raw_sku} 数量必须大于0'
                                )
                                continue
                            # 计算实际数量
                            actual_qty = order_qty * base_qty
                        except (ValueError, TypeError):
                            errors.append(
                                f'订单 {order_number}: '
                                f'SKU {raw_sku} 数量无效: {quantity_str}'
                            )
                            continue
                        
                        # 检查库存（仅警告，不阻止导入）
                        # 优先使用actual_sku查询，如果没有则用小写key
                        current_stock = variant_stock_map.get(
                            actual_sku, 
                            variant_stock_map.get(processed_sku.lower(), 0)
                        )
                        if current_stock < actual_qty:
                            warnings.append(
                                f'⚠️ 订单 {order_number}: '
                                f'SKU {raw_sku} 库存不足 '
                                f'(需要: {actual_qty}, '
                                f'当前: {current_stock}, '
                                f'超卖: {actual_qty - current_stock})'
                            )
                        
                        # 获取销售价格
                        selling_price = None
                        if 'selling_price' in item and pd.notna(
                            item['selling_price']
                        ):
                            price_str = str(item['selling_price']).strip()
                            if price_str and price_str != 'nan':
                                try:
                                    temp_price = float(price_str)
                                    if temp_price < 0:
                                        errors.append(
                                            f'订单 {order_number}: '
                                            f'SKU {raw_sku} 销售单价不能为负'
                                        )
                                        continue
                                    selling_price = temp_price
                                except (ValueError, TypeError):
                                    errors.append(
                                        f'订单 {order_number}: '
                                        f'SKU {raw_sku} '
                                        f'销售单价格式无效: {price_str}'
                                    )
                                    continue
                        
                        # 构建订单项数据
                        order_item_data = {
                            'parent_sku': raw_sku,
                            'variant_sku': actual_sku,
                            'quantity': actual_qty,
                            'item_price': selling_price  # 保持None，不转成0
                        }
                        order_items_list.append(order_item_data)
                    
                    if not order_items_list:
                        errors.append(
                            f'订单 {order_number}: 没有有效的订单项'
                        )
                        continue
                    
                    # 获取订单总价（如果Excel中有total_amount列）
                    order_total_amount = None
                    if 'total_amount' in items.columns:
                        # 取第一行的total_amount（订单级别数据）
                        total_value = items.iloc[0]['total_amount']
                        if pd.notna(total_value):
                            try:
                                order_total_amount = float(total_value)
                                if order_total_amount < 0:
                                    errors.append(
                                        f'订单 {order_number}: 订单总价不能为负'
                                    )
                                    continue
                            except (ValueError, TypeError):
                                errors.append(
                                    f'订单 {order_number}: 订单总价格式无效'
                                )
                                continue
                    
                    # 构建订单数据
                    order_data = {
                        'order_number': str(order_number).strip(),
                        'customer_name': str(customer_name).strip(),
                        'order_date': order_date_obj.isoformat(),
                        'items': order_items_list
                    }
                    
                    # 如果有订单总价，添加到订单数据中
                    if order_total_amount is not None:
                        order_data['total_amount'] = order_total_amount
                    
                    orders_to_import.append(order_data)
                    
                except Exception as e:
                    errors.append(
                        f'处理订单 {order_number} 时出错: {str(e)}'
                    )
                    continue
            
            # 调用DAL层导入
            if orders_to_import:
                # 更新进度提示：显示订单数量
                progress.set_message(
                    f"正在提交 {len(orders_to_import)} 笔订单到服务器..."
                )
                progress.set_detail("请稍候,正在处理中...")
                progress.set_indeterminate()
                QApplication.processEvents()
                
                try:
                    result = dal.import_sales_orders(
                        orders_to_import,
                        operator_info
                    )
                    imported_count = result.get('success', 0)
                    failed_count = result.get('failed', 0)
                    skipped_count = result.get('skipped', 0)
                    import_errors = result.get('errors', [])
                    
                    # 检查是否有重复订单冲突
                    conflict_orders = []
                    other_errors = []
                    
                    for err in import_errors:
                        if isinstance(err, dict):
                            if err.get('error') == 'DUPLICATE_CONFLICT':
                                conflict_orders.append(err)
                            else:
                                other_errors.append(
                                    f"订单导入失败: {err.get('error', str(err))}"
                                )
                        else:
                            other_errors.append(f"导入错误: {str(err)}")
                    
                    errors.extend(other_errors)
                    
                    # 如果有冲突订单，询问用户处理方式
                    if conflict_orders:
                        progress.close()
                        
                        # 构建冲突信息
                        conflict_msg = f"检测到 {len(conflict_orders)} 笔订单与现有订单冲突:\n\n"
                        for i, conflict in enumerate(conflict_orders[:5], 1):  # 只显示前5笔
                            order_num = conflict.get('order_number', 'N/A')
                            conflict_msg += f"{i}. 订单号: {order_num}\n"
                            
                            existing_items = conflict.get('existing_items', {})
                            new_items = conflict.get('new_items', {})
                            
                            conflict_msg += "   现有数据:\n"
                            for sku, qty in list(existing_items.items())[:3]:
                                conflict_msg += f"     - {sku}: {qty}件\n"
                            if len(existing_items) > 3:
                                conflict_msg += f"     ... 共{len(existing_items)}个SKU\n"
                            
                            conflict_msg += "   新导入数据:\n"
                            for sku, qty in list(new_items.items())[:3]:
                                conflict_msg += f"     - {sku}: {qty}件\n"
                            if len(new_items) > 3:
                                conflict_msg += f"     ... 共{len(new_items)}个SKU\n"
                            
                            conflict_msg += "\n"
                        
                        if len(conflict_orders) > 5:
                            conflict_msg += f"... 还有 {len(conflict_orders)-5} 笔冲突订单\n\n"
                        
                        conflict_msg += "请选择处理方式:\n"
                        conflict_msg += "- 跳过: 保留现有订单，跳过新数据\n"
                        conflict_msg += "- 覆盖: 删除现有订单并导入新数据\n"
                        conflict_msg += "- 取消: 终止导入操作"
                        
                        # 创建自定义对话框
                        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
                        
                        dialog = QDialog(self)
                        dialog.setWindowTitle("订单冲突")
                        dialog.setMinimumWidth(600)
                        
                        layout = QVBoxLayout(dialog)
                        
                        label = QLabel(conflict_msg)
                        label.setWordWrap(True)
                        layout.addWidget(label)
                        
                        # 添加按钮
                        button_box = QDialogButtonBox()
                        skip_btn = button_box.addButton("跳过", QDialogButtonBox.ButtonRole.AcceptRole)
                        overwrite_btn = button_box.addButton("覆盖", QDialogButtonBox.ButtonRole.ActionRole)
                        cancel_btn = button_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
                        
                        layout.addWidget(button_box)
                        
                        user_choice = None
                        
                        def on_skip():
                            nonlocal user_choice
                            user_choice = 'skip'
                            dialog.accept()
                        
                        def on_overwrite():
                            nonlocal user_choice
                            user_choice = 'overwrite'
                            dialog.accept()
                        
                        def on_cancel():
                            nonlocal user_choice
                            user_choice = 'cancel'
                            dialog.reject()
                        
                        skip_btn.clicked.connect(on_skip)
                        overwrite_btn.clicked.connect(on_overwrite)
                        cancel_btn.clicked.connect(on_cancel)
                        
                        dialog.exec()
                        
                        # 根据用户选择处理
                        if user_choice == 'cancel':
                            QMessageBox.information(self, '已取消', '导入操作已取消')
                            return
                        elif user_choice == 'overwrite':
                            # 重新导入，标记为强制覆盖
                            progress = ProgressDialog(
                                self,
                                title="覆盖导入订单",
                                message="正在覆盖现有订单..."
                            )
                            progress.set_detail(
                                f"正在处理 {len(conflict_orders)} 笔冲突订单..."
                            )
                            progress.set_indeterminate()
                            progress.show()
                            QApplication.processEvents()
                            
                            # 将冲突订单添加force_overwrite标记
                            conflict_order_numbers = {c.get('order_number') for c in conflict_orders}
                            for order in orders_to_import:
                                if order['order_number'] in conflict_order_numbers:
                                    order['force_overwrite'] = True
                            
                            # 重新导入
                            result = dal.import_sales_orders(
                                orders_to_import,
                                operator_info
                            )
                            imported_count = result.get('success', 0)
                            failed_count = result.get('failed', 0)
                            skipped_count = result.get('skipped', 0)
                        # 如果选择skip，不做处理，冲突订单会被计入skipped_count
                    
                    # 完成进度对话框并自动关闭
                    success_msg = (
                        f"导入完成!\n"
                        f"成功: {imported_count}笔\n"
                        f"跳过: {skipped_count}笔\n"
                        f"失败: {failed_count}笔"
                    )
                    progress.complete(
                        message=success_msg,
                        auto_close_delay=2000
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
                imported_count = 0
                progress.error(
                    message="没有可导入的订单",
                    auto_close_delay=1500
                )
            
            # 刷新显示
            self.load_sales()
            
            # 发出信号通知其他页面刷新
            if imported_count > 0:
                self.orders_imported.emit()
            
            # 显示导入结果
            if imported_count > 0 or skipped_count > 0:
                message = '📊 导入结果统计：\n\n'
                if imported_count > 0:
                    message += f'✅ 成功导入: {imported_count} 笔订单\n'
                if skipped_count > 0:
                    message += f'⏭️  跳过重复: {skipped_count} 笔订单\n'
                if failed_count > 0:
                    message += f'❌ 导入失败: {failed_count} 笔订单\n'
                
                # 显示库存不足警告
                if warnings:
                    message += f'\n⚠️  库存不足: {len(warnings)} 个SKU\n'
                    message += '\n库存警告详情：\n'
                    message += '\n'.join(f'  • {wrn}' for wrn in warnings[:10])
                    if len(warnings) > 10:
                        message += f'\n  ... 还有 {len(warnings) - 10} 条警告'
                    message += '\n\n💡 提示：订单已导入，请及时补充库存'
                
                if errors:
                    message += '\n⚠️ 失败详情：\n'
                    message += '\n'.join(f'  • {err}' for err in errors[:10])
                    if len(errors) > 10:
                        message += f'\n  ... 还有 {len(errors) - 10} 条错误'
                
                # 导入成功后强制刷新所有相关缓存（销售数据已变化）
                # 1. 清除销售订单缓存
                data_cache.invalidate_pattern('sales_orders_*')
                
                # 2. 清除导入用的SKU映射缓存（库存已变化）
                data_cache.invalidate('sales_import_sku_map')
                print("✅ 已清除SKU映射缓存")
                
                # 3. 强制刷新仪表盘统计（立即生效）
                from utils.data_access import dal
                try:
                    dashboard_data = dal.get_batch_dashboard_data(threshold=1.0)
                    data_cache.set('dashboard_stats', dashboard_data, ttl=300)
                    print("✅ 订单导入后刷新仪表盘缓存")
                except:
                    data_cache.invalidate('dashboard_stats')
                
                # 4. 强制刷新库存数据（销量变化影响库存状态）
                try:
                    # 注意：这里只是清除缓存，让下次访问时重新加载
                    data_cache.invalidate('inventory_data')
                    print("✅ 订单导入后已清除库存缓存")
                except Exception as e:
                    print(f"⚠️ 清除库存缓存失败: {e}")
                
                QMessageBox.information(
                    self,
                    '导入完成',
                    message
                )
            else:
                error_message = '导入失败：\n\n'
                if errors:
                    error_message += '数据验证错误：\n'
                    error_message += '\n'.join(f'- {err}' for err in errors[:10])
                    if len(errors) > 10:
                        error_message += f'\n... 还有 {len(errors) - 10} 条错误'
                
                QMessageBox.critical(
                    self,
                    '导入失败',
                    error_message
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                '导入错误',
                f'文件处理失败: {str(e)}'
            )

    def _on_column_resized(self, index: int, old_size: int, new_size: int):
        """列宽改变时自动保存配置"""
        try:
            # 获取当前所有列的宽度
            column_count = self.sales_table.columnCount()
            widths = []
            for i in range(column_count):
                widths.append(self.sales_table.columnWidth(i))
            
            # 保存到配置文件
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('sales_view', widths)
        except Exception as e:
            print(f"保存列宽配置失败: {e}")

    def on_selection_changed(self):
        """处理选择改变事件"""
        # 获取当前选中的项（行）
        current_item = self.sales_table.currentItem()
        
        # 调试信息
        print(f"[DEBUG] on_selection_changed 被调用")
        print(f"[DEBUG] current_item: {current_item}")
        
        if current_item:
            parent = current_item.parent()
            print(f"[DEBUG] parent: {parent}")
            print(f"[DEBUG] 第0列文本: {current_item.text(0)}")
            
            # 只有选中了顶级订单项时才启用删除按钮
            # 顶级项没有父项，即 item.parent() 为 None
            is_top_level = parent is None
            print(f"[DEBUG] is_top_level: {is_top_level}")
            
            self.delete_btn.setEnabled(is_top_level)
            print(f"[DEBUG] 删除按钮状态: {'启用' if is_top_level else '禁用'}")
        else:
            print(f"[DEBUG] 没有选中项，禁用删除按钮")
            self.delete_btn.setEnabled(False)

    def delete_selected_order(self):
        """删除选中的订单"""
        selected_items = self.sales_table.selectedItems()
        if not selected_items:
            return
            
        # 获取选中的顶级项（订单）
        orders_to_delete = []
        for item in selected_items:
            if item.parent() is None:  # 顶级项是订单
                # 获取订单号，去掉emoji前缀 "📋 "
                order_text = item.text(0)
                order_number = order_text.replace('📋 ', '').strip()
                if order_number:
                    orders_to_delete.append(order_number)
        
        if not orders_to_delete:
            QMessageBox.warning(
                self, '提示', '请选择要删除的订单（不是订单明细）'
            )
            return
            
        # 确认删除
        order_list = '\n'.join(f'- {order}' for order in orders_to_delete)
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除以下订单吗？\n\n{order_list}\n\n'
            '删除后无法恢复！',
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_orders(orders_to_delete)

    def _delete_orders(self, order_numbers):
        """执行删除订单操作"""
        try:
            from utils.data_access import dal
            from utils.operator import get_operator_info
            
            # 创建进度对话框
            progress = QProgressDialog(
                "正在删除订单...",
                "取消",
                0,
                len(order_numbers),
                self
            )
            progress.setWindowTitle("删除订单")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)  # 立即显示
            progress.setValue(0)
            
            deleted_count = 0
            operator_info = get_operator_info()
            
            # 直接通过订单号搜索每个订单,获取其ID
            for index, order_number in enumerate(order_numbers):
                # 检查用户是否取消
                if progress.wasCanceled():
                    break
                
                # 更新进度对话框
                label_text = (
                    f"正在删除订单 {index + 1}/{len(order_numbers)}\n"
                    f"订单号: {order_number}"
                )
                progress.setLabelText(label_text)
                progress.setValue(index)
                
                # 搜索订单
                search_results = dal.search_sales_orders(order_number)
                
                # 在搜索结果中找到匹配的订单
                order_found = False
                for order in search_results:
                    order_num = safe_get_attr(order, 'order_number')
                    if order_num == order_number:
                        order_id = safe_get_attr(order, 'id')
                        if order_id:
                            # 删除订单
                            dal.delete_sale_order(order_id, operator_info)
                            deleted_count += 1
                            order_found = True
                            break
                
                if not order_found:
                    print(f"警告: 未找到订单 {order_number}")
            
            # 完成进度
            progress.setValue(len(order_numbers))
            progress.close()
            
            # 刷新显示
            self.load_sales()
            
            # 删除成功后清除缓存(销售数据已变化)
            # 使用模式匹配清除所有日期范围的销售订单缓存
            data_cache.invalidate_pattern('sales_orders_*')
            data_cache.invalidate('dashboard_stats')
            
            # 发出信号通知其他页面刷新(智能刷新)
            if deleted_count > 0:
                self.orders_imported.emit()
            
            # 显示结果
            if progress.wasCanceled():
                QMessageBox.information(
                    self,
                    '删除已取消',
                    f'已删除 {deleted_count}/{len(order_numbers)} 笔订单'
                )
            else:
                QMessageBox.information(
                    self,
                    '删除成功',
                    f'成功删除 {deleted_count} 笔订单'
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                '删除失败',
                f'删除订单时发生错误: {str(e)}'
            )
