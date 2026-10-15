"""
分页控件 - 通用分页UI组件
提供首页、上一页、下一页、末页、页码跳转功能
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIntValidator


class PaginationWidget(QWidget):
    """分页控件
    
    信号:
        page_changed: 页码改变信号 (int: 新页码)
        page_size_changed: 每页数量改变信号 (int: 新的每页数量)
    """
    page_changed = pyqtSignal(int)  # 页码改变信号
    page_size_changed = pyqtSignal(int)  # 每页数量改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self.total_items = 0
        self.page_size = 50
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 左侧弹簧
        layout.addItem(QSpacerItem(
            40, 20, 
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Minimum
        ))
        
        # 总数标签
        self.total_label = QLabel('共 0 条')
        self.total_label.setStyleSheet('''
            QLabel {
                color: #595959;
                font-size: 13px;
                padding: 0 8px;
            }
        ''')
        layout.addWidget(self.total_label)
        
        # 第一页按钮
        self.first_btn = QPushButton('⏮ 首页')
        self.first_btn.setFixedWidth(80)
        self.first_btn.clicked.connect(lambda: self.goto_page(1))
        layout.addWidget(self.first_btn)
        
        # 上一页按钮
        self.prev_btn = QPushButton('◀ 上一页')
        self.prev_btn.setFixedWidth(90)
        self.prev_btn.clicked.connect(self.prev_page)
        layout.addWidget(self.prev_btn)
        
        # 页码输入区域
        page_input_widget = QWidget()
        page_input_layout = QHBoxLayout(page_input_widget)
        page_input_layout.setContentsMargins(0, 0, 0, 0)
        page_input_layout.setSpacing(4)
        
        page_input_layout.addWidget(QLabel('第'))
        
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(50)
        self.page_input.setPlaceholderText('页码')
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999))
        self.page_input.returnPressed.connect(self.on_page_input)
        page_input_layout.addWidget(self.page_input)
        
        page_input_layout.addWidget(QLabel('页'))
        
        # 页码标签
        self.page_label = QLabel('/ 1')
        self.page_label.setMinimumWidth(40)
        page_input_layout.addWidget(self.page_label)
        
        layout.addWidget(page_input_widget)
        
        # 下一页按钮
        self.next_btn = QPushButton('下一页 ▶')
        self.next_btn.setFixedWidth(90)
        self.next_btn.clicked.connect(self.next_page)
        layout.addWidget(self.next_btn)
        
        # 最后一页按钮
        self.last_btn = QPushButton('末页 ⏭')
        self.last_btn.setFixedWidth(80)
        self.last_btn.clicked.connect(lambda: self.goto_page(self.total_pages))
        layout.addWidget(self.last_btn)
        
        # 右侧弹簧
        layout.addItem(QSpacerItem(
            40, 20, 
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Minimum
        ))
        
        # 设置样式
        self.setStyleSheet('''
            QPushButton {
                padding: 6px 12px;
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
            QPushButton:disabled {
                background-color: #d9d9d9;
                color: #999;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #1890ff;
            }
            QLabel {
                color: #262626;
                font-size: 13px;
            }
        ''')
    
    def set_page_info(self, current_page: int, total_pages: int, 
                     total_items: int = 0, page_size: int = None):
        """设置分页信息
        
        Args:
            current_page: 当前页码 (从1开始)
            total_pages: 总页数
            total_items: 总条目数 (可选)
            page_size: 每页数量 (可选)
        """
        self.current_page = max(1, current_page)
        self.total_pages = max(1, total_pages)
        self.total_items = total_items
        
        if page_size is not None:
            self.page_size = page_size
        
        # 更新页码标签
        self.page_label.setText(f'/ {self.total_pages}')
        self.page_input.setText(str(self.current_page))
        
        # 更新总数标签
        if total_items > 0:
            start_item = (self.current_page - 1) * self.page_size + 1
            end_item = min(self.current_page * self.page_size, total_items)
            self.total_label.setText(
                f'共 {total_items} 条  |  显示 {start_item}-{end_item}'
            )
        else:
            self.total_label.setText('共 0 条')
        
        # 更新按钮状态
        self.first_btn.setEnabled(current_page > 1)
        self.prev_btn.setEnabled(current_page > 1)
        self.next_btn.setEnabled(current_page < total_pages)
        self.last_btn.setEnabled(current_page < total_pages)
        self.page_input.setEnabled(total_pages > 1)
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.goto_page(self.current_page - 1)
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.goto_page(self.current_page + 1)
    
    def goto_page(self, page: int):
        """跳转到指定页
        
        Args:
            page: 目标页码 (从1开始)
        """
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.page_changed.emit(page)
    
    def on_page_input(self):
        """处理页码输入"""
        try:
            page = int(self.page_input.text())
            if 1 <= page <= self.total_pages:
                self.goto_page(page)
            else:
                # 输入超出范围，恢复当前页码
                self.page_input.setText(str(self.current_page))
        except ValueError:
            # 输入无效，恢复当前页码
            self.page_input.setText(str(self.current_page))
    
    def reset(self):
        """重置分页控件到初始状态"""
        self.set_page_info(1, 1, 0)
