"""
子SKU销量统计视图
按时间范围统计各SKU的销售数量、金额、订单数
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QComboBox, QHeaderView, QMessageBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any

from config.column_width_manager import get_column_width_manager
import json
import os

from utils.operator import get_operator_info


class NumericTableWidgetItem(QTableWidgetItem):
    """自定义表格项类，支持数值排序"""

    def __init__(self, value, display_text=None):
        """
        初始化
        :param value: 实际数值
        :param display_text: 显示文本（如果为None，使用str(value)）
        """
        super().__init__(display_text if display_text else str(value))
        self.numeric_value = value

    def __lt__(self, other):
        """重载小于运算符，用于排序"""
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class SkuSalesStatsView(QWidget):
    """子SKU销量统计页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_stats = []  # 当前统计数据
        self.all_stats = []  # 全部统计数据（用于分页）
        self.stats_cache = {}  # 缓存统计数据: {time_range: stats}
        self.settings_file = 'erp_settings.json'
        
        # 分页状态
        self.current_page = 1
        self.page_size = 50
        self.total_pages = 1
        
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 标题和时间筛选器
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📊 子SKU销量统计")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # SKU搜索框
        from PyQt6.QtWidgets import QLineEdit
        
        search_label = QLabel("🔎 搜索SKU:")
        search_label.setStyleSheet("font-weight: bold; color: #495057;")
        header_layout.addWidget(search_label)
        
        self.sku_search_input = QLineEdit()
        self.sku_search_input.setPlaceholderText("输入SKU搜索...")
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
        self.sku_search_input.textChanged.connect(self.on_search_changed)
        self.sku_search_input.returnPressed.connect(self.on_search_sku)
        header_layout.addWidget(self.sku_search_input)
        
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
        header_layout.addWidget(clear_search_btn)
        
        header_layout.addSpacing(20)
        
        # 时间范围选择
        time_range_label = QLabel("时间范围:")
        time_range_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(time_range_label)
        
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems([
            "今天",
            "昨天", 
            "最近7天",
            "最近30天",
            "本月",
            "上个月",
            "今年"
        ])
        self.time_range_combo.setCurrentText("最近30天")
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        self.time_range_combo.setMinimumWidth(120)
        header_layout.addWidget(self.time_range_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        self.refresh_btn.setMinimumWidth(80)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        header_layout.addWidget(self.refresh_btn)
        
        # 导出按钮
        export_btn = QPushButton("📊 导出Excel")
        export_btn.clicked.connect(self.export_to_excel)
        export_btn.setMinimumWidth(100)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # 统计信息栏
        stats_layout = QHBoxLayout()
        
        self.total_skus_label = QLabel("SKU数量: 0")
        self.total_skus_label.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.total_skus_label)
        
        self.total_quantity_label = QLabel("总销量: 0")
        self.total_quantity_label.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                background-color: #2ecc71;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.total_quantity_label)
        
        self.total_orders_label = QLabel("订单数: 0")
        self.total_orders_label.setStyleSheet("""
            QLabel {
                padding: 8px 15px;
                background-color: #9b59b6;
                color: white;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        stats_layout.addWidget(self.total_orders_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # SKU销量统计表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels([
            "产品名称", "SKU", "选项", "销售数量", "订单数"
        ])
        
        # 表格样式
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.stats_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        
        # 设置行高
        vertical_header = self.stats_table.verticalHeader()
        vertical_header.setDefaultSectionSize(45)  # 设置默认行高为45像素
        vertical_header.setVisible(False)  # 隐藏行号
        
        # 设置列宽 - 允许用户调整
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumHeight(40)  # 设置表头高度
        
        # 监听列宽变化
        header.sectionResized.connect(self.on_column_resized)
        
        # 加载保存的列宽
        self.load_column_widths()
        
        # 启用排序
        self.stats_table.setSortingEnabled(True)
        
        # 表头点击排序
        header.sectionClicked.connect(self.on_header_clicked)
        
        layout.addWidget(self.stats_table)
        
        # 添加分页控件
        from gui.widgets.pagination import PaginationWidget
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self.on_page_changed)
        layout.addWidget(self.pagination)
        
        self.setLayout(layout)
        
        # 自动加载数据
        self.load_stats()
    
    def get_date_range(self, range_text: str) -> tuple:
        """根据选择的时间范围返回开始和结束日期"""
        today = QDate.currentDate()
        
        if range_text == "今天":
            start_date = today
            end_date = today
        elif range_text == "昨天":
            yesterday = today.addDays(-1)
            start_date = yesterday
            end_date = yesterday
        elif range_text == "最近7天":
            start_date = today.addDays(-6)
            end_date = today
        elif range_text == "最近30天":
            start_date = today.addDays(-29)
            end_date = today
        elif range_text == "本月":
            start_date = QDate(today.year(), today.month(), 1)
            end_date = today
        elif range_text == "上个月":
            last_month = today.addMonths(-1)
            start_date = QDate(last_month.year(), last_month.month(), 1)
            # 上个月最后一天
            end_date = QDate(today.year(), today.month(), 1).addDays(-1)
        elif range_text == "今年":
            start_date = QDate(today.year(), 1, 1)
            end_date = today
        else:
            # 默认最近30天
            start_date = today.addDays(-29)
            end_date = today
        
        return start_date, end_date
    
    def on_time_range_changed(self, range_text: str):
        """时间范围改变时重新加载数据"""
        self.load_stats()
    
    def on_refresh_clicked(self):
        """刷新按钮点击事件（清除缓存并重新加载）"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("加载中...")
        # 清除缓存，强制重新加载
        self.stats_cache.clear()
        self.current_page = 1  # 重置到第一页
        print("🗑️ 清除SKU统计缓存")
        self.load_stats()
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新")
    
    def on_page_changed(self, new_page: int):
        """页码切换回调"""
        print(f"📄 切换到第 {new_page} 页")
        self.current_page = new_page
        
        # 重新显示当前页数据
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        self.current_stats = self.all_stats[start_idx:end_idx]
        
        # 更新分页控件状态
        import math
        total_items = len(self.all_stats)
        if self.page_size > 0:
            total_pages = math.ceil(total_items / self.page_size)
        else:
            total_pages = 1
        
        self.pagination.set_page_info(
            current_page=self.current_page,
            total_pages=total_pages,
            total_items=total_items,
            page_size=self.page_size
        )
        
        # 显示数据
        self.display_stats(self.current_stats)
    
    def load_stats(self, trigger='manual'):
        """加载SKU销量统计数据（带缓存和分页）"""
        try:
            from utils.data_access import dal
            import math
            
            # 获取时间范围
            range_text = self.time_range_combo.currentText()
            
            # 检查缓存
            if range_text in self.stats_cache:
                print(f"✅ 使用缓存的SKU统计数据 ({range_text})")
                self.all_stats = self.stats_cache[range_text]
            else:
                start_date, end_date = self.get_date_range(range_text)
                
                # 转换为Python datetime
                start_datetime = datetime(
                    start_date.year(), start_date.month(), start_date.day()
                )
                end_datetime = datetime(
                    end_date.year(), end_date.month(), end_date.day(),
                    23, 59, 59
                )
                
                # 获取SKU销量统计
                stats = dal.get_sku_sales_stats(start_datetime, end_datetime)
                
                # 缓存结果
                self.stats_cache[range_text] = stats
                self.all_stats = stats
                print(f"📥 加载SKU统计数据并缓存 ({range_text})")
            
            # 计算分页
            total_items = len(self.all_stats)
            if self.page_size > 0:
                self.total_pages = math.ceil(total_items / self.page_size)
            else:
                self.total_pages = 1
            
            # 获取当前页数据
            start_idx = (self.current_page - 1) * self.page_size
            end_idx = start_idx + self.page_size
            self.current_stats = self.all_stats[start_idx:end_idx]
            
            # 更新分页控件
            self.pagination.set_page_info(
                current_page=self.current_page,
                total_pages=self.total_pages,
                total_items=total_items,
                page_size=self.page_size
            )
            
            print(f"📄 显示第 {self.current_page}/{self.total_pages} 页 "
                  f"(共{total_items}个SKU)")
            self.display_stats(self.current_stats)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '错误',
                f'加载统计数据失败: {str(e)}'
            )
    
    def display_stats(self, stats: List[Dict[str, Any]]):
        """显示统计数据（优化版本）"""
        # 🚀 性能优化：禁用更新信号和排序
        self.stats_table.setUpdatesEnabled(False)
        self.stats_table.setSortingEnabled(False)
        self.stats_table.blockSignals(True)
        
        try:
            self.stats_table.setRowCount(0)
            
            # 计算汇总数据（基于全部数据，而不是当前页）
            if hasattr(self, 'all_stats') and self.all_stats:
                total_skus = len(self.all_stats)
                total_quantity = sum(
                    s.get('quantity', 0) for s in self.all_stats
                )
                total_orders = sum(
                    s.get('order_count', 0) for s in self.all_stats
                )
            else:
                total_skus = len(stats)
                total_quantity = sum(s.get('quantity', 0) for s in stats)
                total_orders = sum(s.get('order_count', 0) for s in stats)
            
            # 更新统计标签
            self.total_skus_label.setText(f"SKU数量: {total_skus}")
            self.total_quantity_label.setText(f"总销量: {total_quantity:,}")
            self.total_orders_label.setText(f"订单数: {total_orders}")
            
            # 🚀 批量插入行（一次性分配内存）
            self.stats_table.setRowCount(len(stats))
            
            # 填充表格 - 列顺序：产品名称、SKU、选项、销售数量、订单数
            for row, stat in enumerate(stats):
                # 产品名称
                name_item = QTableWidgetItem(stat.get('product_name', ''))
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stats_table.setItem(row, 0, name_item)
                
                # SKU
                sku_item = QTableWidgetItem(stat.get('sku', ''))
                sku_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                sku_item.setForeground(QColor("#1890ff"))
                self.stats_table.setItem(row, 1, sku_item)
                
                # 选项
                options_item = QTableWidgetItem(stat.get('options', ''))
                options_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stats_table.setItem(row, 2, options_item)
                
                # 销售数量
                quantity = stat.get('quantity', 0)
                quantity_item = QTableWidgetItem(str(quantity))
                quantity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stats_table.setItem(row, 3, quantity_item)
                
                # 订单数
                order_count = stat.get('order_count', 0)
                order_item = QTableWidgetItem(str(order_count))
                order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.stats_table.setItem(row, 4, order_item)
            
        finally:
            # 🚀 恢复更新和信号
            self.stats_table.blockSignals(False)
            self.stats_table.setSortingEnabled(True)
            self.stats_table.setUpdatesEnabled(True)
    
    def on_header_clicked(self, logical_index: int):
        """表头点击事件（已由setSortingEnabled处理）"""
        pass
    
    def export_to_excel(self):
        """导出统计数据到Excel"""
        if not self.current_stats:
            QMessageBox.warning(
                self,
                '提示',
                '没有数据可以导出'
            )
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog
            import os
            
            # 生成默认文件名
            range_text = self.time_range_combo.currentText()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f'SKU销量统计_{range_text}_{timestamp}.xlsx'
            
            # 选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                '导出Excel',
                default_filename,
                'Excel文件 (*.xlsx)'
            )
            
            if not file_path:
                return
            
            # 准备导出数据 - 列顺序：产品名称、SKU、选项、销售数量、订单数
            export_data = []
            for stat in self.current_stats:
                export_data.append({
                    '产品名称': stat.get('product_name', ''),
                    'SKU': stat.get('sku', ''),
                    '选项': stat.get('options', ''),
                    '销售数量': stat.get('quantity', 0),
                    '订单数': stat.get('order_count', 0)
                })
            
            # 创建DataFrame并导出
            df = pd.DataFrame(export_data)
            
            # 获取时间范围
            start_date, end_date = self.get_date_range(range_text)
            
            # 使用ExcelWriter添加多个sheet
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 写入数据
                df.to_excel(writer, sheet_name='SKU销量统计', index=False)
                
                # 写入汇总信息
                start_str = start_date.toString("yyyy-MM-dd")
                end_str = end_date.toString("yyyy-MM-dd")
                total_quantity = sum(
                    s.get('quantity', 0) for s in self.current_stats
                )
                total_orders = sum(
                    s.get('order_count', 0) for s in self.current_stats
                )
                
                summary_data = {
                    '统计项目': [
                        '时间范围', 'SKU数量', '总销量', '订单数'
                    ],
                    '数值': [
                        f'{start_str} 至 {end_str}',
                        len(self.current_stats),
                        total_quantity,
                        total_orders
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='汇总信息', index=False)
            
            QMessageBox.information(
                self,
                '成功',
                f'数据已导出到:\n{file_path}'
            )
            
            # 询问是否打开文件
            reply = QMessageBox.question(
                self,
                '提示',
                '是否打开导出的文件？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(file_path)
                
        except Exception as e:
            QMessageBox.critical(
                self,
                '错误',
                f'导出失败: {str(e)}'
            )
    
    def load_column_widths(self):
        """从配置文件加载列宽"""
        try:
            # 使用统一的列宽管理器加载
            width_manager = get_column_width_manager()
            saved_widths = width_manager.get_column_widths('sku_sales_stats_view')
            
            # 如果有保存的列宽，应用它们（新版本5列）
            if saved_widths and len(saved_widths) == 5:
                for col, width in enumerate(saved_widths):
                    self.stats_table.setColumnWidth(col, width)
            else:
                # 使用默认列宽
                self.set_default_column_widths()
        except Exception as e:
            print(f"加载列宽失败: {e}")
            self.set_default_column_widths()
    
    def set_default_column_widths(self):
        """设置默认列宽"""
        # 新列顺序：产品名称、SKU、选项、销售数量、订单数
        default_widths = [200, 365, 280, 177, 100]
        for col, width in enumerate(default_widths):
            self.stats_table.setColumnWidth(col, width)
    
    def on_column_resized(self, logical_index, old_size, new_size):
        """列宽改变时保存到配置文件"""
        try:
            # 获取所有列宽
            widths = []
            for col in range(self.stats_table.columnCount()):
                widths.append(self.stats_table.columnWidth(col))
            
            # 使用统一的列宽管理器保存
            width_manager = get_column_width_manager()
            width_manager.save_column_widths('sku_sales_stats_view', widths)
        except Exception as e:
            print(f"保存列宽失败: {e}")
    
    def showEvent(self, event):
        """页面显示时刷新数据"""
        super().showEvent(event)
        # 只在第一次显示时加载，避免频繁刷新
        if not hasattr(self, '_first_show'):
            self._first_show = True
            self.load_stats()
    
    def on_search_changed(self, text):
        """搜索框文本变化时的处理(实时过滤)"""
        if not text.strip():
            # 搜索框为空,显示当前时间范围的所有数据
            self.display_stats(self.current_stats)
        else:
            # 过滤当前数据
            self.filter_current_stats(text.strip().upper())
    
    def on_search_sku(self):
        """按下回车键搜索SKU(智能时间范围)"""
        search_text = self.sku_search_input.text().strip().upper()
        if not search_text:
            QMessageBox.warning(self, '提示', '请输入要搜索的SKU')
            return
        
        try:
            from utils.data_access import dal
            
            # 首先搜索最近30天
            today = QDate.currentDate()
            start_30days = today.addDays(-29)
            start_datetime_30 = datetime(
                start_30days.year(), start_30days.month(), start_30days.day()
            )
            end_datetime = datetime(
                today.year(), today.month(), today.day(), 23, 59, 59
            )
            
            stats_30days = dal.get_sku_sales_stats(
                start_datetime_30, end_datetime
            )
            
            # 过滤匹配的SKU
            matching_stats_30 = [
                s for s in stats_30days
                if search_text in s.get('sku', '').upper()
            ]
            
            if matching_stats_30:
                # 如果近30天有销量,显示近30天数据
                self.time_range_combo.setCurrentText("最近30天")
                self.current_stats = stats_30days
                self.display_stats(matching_stats_30)
                
                # 显示提示信息
                main_window = self.window()
                if hasattr(main_window, 'center_message_label'):
                    total_qty = sum(
                        s.get('quantity', 0) for s in matching_stats_30
                    )
                    main_window.center_message_label.setText(
                        f'🔍 搜索 "{search_text}" 在最近30天找到 '
                        f'{len(matching_stats_30)} 个SKU，总销量 {total_qty}'
                    )
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(
                        3000, 
                        lambda: main_window.center_message_label.setText('')
                    )
                return
            
            # 如果近30天没有销量,搜索今年
            start_year = QDate(today.year(), 1, 1)
            start_datetime_year = datetime(
                start_year.year(), start_year.month(), start_year.day()
            )
            
            stats_year = dal.get_sku_sales_stats(
                start_datetime_year, end_datetime
            )
            
            matching_stats_year = [
                s for s in stats_year
                if search_text in s.get('sku', '').upper()
            ]
            
            if matching_stats_year:
                # 如果今年有销量,显示今年数据
                self.time_range_combo.setCurrentText("今年")
                self.current_stats = stats_year
                self.display_stats(matching_stats_year)
                
                # 显示提示信息
                main_window = self.window()
                if hasattr(main_window, 'center_message_label'):
                    total_qty = sum(
                        s.get('quantity', 0) for s in matching_stats_year
                    )
                    main_window.center_message_label.setText(
                        f'🔍 搜索 "{search_text}" 在今年找到 '
                        f'{len(matching_stats_year)} 个SKU，总销量 {total_qty}'
                    )
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(
                        3000,
                        lambda: main_window.center_message_label.setText('')
                    )
                return
            
            # 如果今年也没有销量,显示0销量的结果
            # 需要查询产品信息
            from database.session import SessionLocal
            from database.models import ProductVariant
            
            db = SessionLocal()
            try:
                # 查询匹配的SKU
                variants = db.query(ProductVariant).filter(
                    ProductVariant.sku.ilike(f'%{search_text}%')
                ).all()
                
                if variants:
                    # 构造0销量的统计数据
                    zero_stats = []
                    for variant in variants:
                        product = variant.product
                        zero_stats.append({
                            'product_name': product.name if product else '未知',
                            'sku': variant.sku,
                            'variant_name': variant.name or '',
                            'total_quantity': 0,
                            'order_count': 0
                        })
                    
                    self.display_stats(zero_stats)
                    
                    # 显示提示信息
                    main_window = self.window()
                    if hasattr(main_window, 'center_message_label'):
                        main_window.center_message_label.setText(
                            f'🔍 搜索 "{search_text}" 找到 {len(zero_stats)} '
                            f'个SKU，但今年无销量'
                        )
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(
                            3000,
                            lambda: main_window.center_message_label.setText('')
                        )
                else:
                    QMessageBox.information(
                        self, '提示', f'未找到匹配 "{search_text}" 的SKU'
                    )
            finally:
                db.close()
                
        except Exception as e:
            QMessageBox.critical(
                self,
                '错误',
                f'搜索失败: {str(e)}'
            )
    
    def filter_current_stats(self, search_text):
        """根据SKU搜索过滤统计数据（支持分页）"""
        import math
        
        if not self.all_stats:
            return
        
        # 从全部数据中过滤
        filtered_stats = [
            s for s in self.all_stats
            if search_text in s.get('sku', '').upper()
        ]
        
        print(f"🔍 搜索'{search_text}'，找到 {len(filtered_stats)} 条")
        
        # 更新分页（基于过滤结果）
        self.current_page = 1
        total_items = len(filtered_stats)
        if self.page_size > 0:
            self.total_pages = math.ceil(total_items / self.page_size)
        else:
            self.total_pages = 1
        
        # 获取第一页数据
        start_idx = 0
        end_idx = self.page_size
        self.current_stats = filtered_stats[start_idx:end_idx]
        
        # 临时保存过滤结果到all_stats用于分页
        self.all_stats = filtered_stats
        
        # 更新分页控件
        self.pagination.set_page_info(
            current_page=self.current_page,
            total_pages=self.total_pages,
            total_items=total_items,
            page_size=self.page_size
        )
        
        # 显示过滤后的数据
        self.display_stats(self.current_stats)
    
    def clear_search(self):
        """清空SKU搜索"""
        self.sku_search_input.clear()
        self.current_page = 1  # 重置到第一页
        # 重新加载完整数据
        self.load_stats(trigger='clear_search')
