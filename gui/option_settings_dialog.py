"""选项设置对话框"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QWidget, QInputDialog
)
from PyQt6.QtCore import Qt
from config.product_options import (
    get_option_types, get_type_options, get_option_mapping,
    update_option_types, update_type_options, update_option_mapping
)


class DraggableListWidget(QListWidget):
    """支持拖拽排序的列表控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        
    def dropEvent(self, event):
        super().dropEvent(event)
        # 通知父窗口列表顺序已更改
        if hasattr(self.parent(), 'on_order_changed'):
            self.parent().on_order_changed()


class OptionSettingsDialog(QDialog):
    """产品选项设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('产品选项设置')
        self.resize(800, 600)
        
        # 初始化数据
        self.option_types = get_option_types()
        self.type_options = {t: get_type_options(t) for t in self.option_types}
        self.option_mapping = get_option_mapping()
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout()
        
        # 左侧：选项类型排序
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        left_layout.addWidget(QLabel('选项类型排序（可拖拽调整）：'))
        self.type_list = DraggableListWidget()
        self.type_list.itemClicked.connect(self.on_type_selected)
        left_layout.addWidget(self.type_list)
        
        # 选项类型的增删按钮
        btn_layout = QHBoxLayout()
        self.add_type_btn = QPushButton('添加类型')
        self.add_type_btn.clicked.connect(self.add_option_type)
        self.remove_type_btn = QPushButton('删除类型')
        self.remove_type_btn.clicked.connect(self.remove_option_type)
        btn_layout.addWidget(self.add_type_btn)
        btn_layout.addWidget(self.remove_type_btn)
        left_layout.addLayout(btn_layout)
        
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(200)
        layout.addWidget(left_widget)
        
        # 中间：选项值排序
        middle_widget = QWidget()
        middle_layout = QVBoxLayout()
        
        middle_layout.addWidget(QLabel('选项值排序（可拖拽调整）：'))
        self.values_list = DraggableListWidget()
        middle_layout.addWidget(self.values_list)
        
        # 选项值的增删按钮
        btn_layout = QHBoxLayout()
        self.add_value_btn = QPushButton('添加选项')
        self.add_value_btn.clicked.connect(self.add_option_value)
        self.remove_value_btn = QPushButton('删除选项')
        self.remove_value_btn.clicked.connect(self.remove_option_value)
        btn_layout.addWidget(self.add_value_btn)
        btn_layout.addWidget(self.remove_value_btn)
        middle_layout.addLayout(btn_layout)
        
        middle_widget.setLayout(middle_layout)
        middle_widget.setFixedWidth(200)
        layout.addWidget(middle_widget)
        
        # 右侧：名称映射表格
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        right_layout.addWidget(QLabel('选项名称映射：'))
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(2)
        self.mapping_table.setHorizontalHeaderLabels(['原名称', '标准名称'])
        header = self.mapping_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.mapping_table)
        
        # 映射的增删按钮
        btn_layout = QHBoxLayout()
        self.add_mapping_btn = QPushButton('添加映射')
        self.add_mapping_btn.clicked.connect(self.add_mapping)
        self.remove_mapping_btn = QPushButton('删除映射')
        self.remove_mapping_btn.clicked.connect(self.remove_mapping)
        btn_layout.addWidget(self.add_mapping_btn)
        btn_layout.addWidget(self.remove_mapping_btn)
        right_layout.addLayout(btn_layout)
        
        right_widget.setLayout(right_layout)
        layout.addWidget(right_widget)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(save_btn)
        bottom_layout.addWidget(cancel_btn)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        
    def load_data(self):
        """加载数据到界面"""
        # 加载选项类型
        self.type_list.clear()
        self.type_list.addItems(self.option_types)
        if self.option_types:
            self.type_list.setCurrentRow(0)
            self.load_option_values(self.option_types[0])
            
        # 加载名称映射
        self.load_mapping_table()
        
    def load_option_values(self, option_type):
        """加载指定选项类型的选项值"""
        self.values_list.clear()
        if option_type in self.type_options:
            self.values_list.addItems(self.type_options[option_type])
            
    def load_mapping_table(self):
        """加载名称映射表格"""
        self.mapping_table.setRowCount(len(self.option_mapping))
        for row, (key, value) in enumerate(self.option_mapping.items()):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(key))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(value))
            
    def on_type_selected(self, item):
        """选项类型被选中时触发"""
        if item:
            self.load_option_values(item.text())
            
    def on_order_changed(self):
        """处理排序改变事件"""
        # 更新选项类型顺序
        self.option_types = [
            self.type_list.item(i).text()
            for i in range(self.type_list.count())
        ]
        
        # 更新当前选中类型的选项值顺序
        current_type = self.type_list.currentItem()
        if current_type:
            type_name = current_type.text()
            self.type_options[type_name] = [
                self.values_list.item(i).text()
                for i in range(self.values_list.count())
            ]
            
    def add_option_type(self):
        """添加新的选项类型"""
        type_name, ok = QInputDialog.getText(
            self, '添加选项类型',
            '请输入新的选项类型名称：'
        )
        if ok and type_name:
            if type_name in self.option_types:
                QMessageBox.warning(
                    self, '错误',
                    f'选项类型 "{type_name}" 已存在！'
                )
                return
                
            self.option_types.append(type_name)
            self.type_options[type_name] = []
            self.type_list.addItem(type_name)
            
    def remove_option_type(self):
        """删除选中的选项类型"""
        current_item = self.type_list.currentItem()
        if not current_item:
            return
            
        type_name = current_item.text()
        if QMessageBox.question(
            self, '确认删除',
            f'确定要删除选项类型 "{type_name}" 吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            row = self.type_list.row(current_item)
            self.type_list.takeItem(row)
            del self.type_options[type_name]
            self.option_types.remove(type_name)
            
    def add_option_value(self):
        """添加新的选项值"""
        current_type = self.type_list.currentItem()
        if not current_type:
            QMessageBox.warning(
                self, '错误',
                '请先选择一个选项类型！'
            )
            return
            
        type_name = current_type.text()
        value, ok = QInputDialog.getText(
            self, '添加选项值',
            f'请输入 "{type_name}" 的新选项值：'
        )
        if ok and value:
            if value in self.type_options[type_name]:
                QMessageBox.warning(
                    self, '错误',
                    f'选项值 "{value}" 已存在！'
                )
                return
                
            self.type_options[type_name].append(value)
            self.values_list.addItem(value)
            
    def remove_option_value(self):
        """删除选中的选项值"""
        current_type = self.type_list.currentItem()
        current_value = self.values_list.currentItem()
        if not current_type or not current_value:
            return
            
        type_name = current_type.text()
        value = current_value.text()
        if QMessageBox.question(
            self, '确认删除',
            f'确定要删除 "{type_name}" 的选项值 "{value}" 吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            row = self.values_list.row(current_value)
            self.values_list.takeItem(row)
            self.type_options[type_name].remove(value)
            
    def add_mapping(self):
        """添加新的名称映射"""
        row = self.mapping_table.rowCount()
        self.mapping_table.insertRow(row)
        self.mapping_table.setItem(row, 0, QTableWidgetItem(''))
        self.mapping_table.setItem(row, 1, QTableWidgetItem(''))
        
    def remove_mapping(self):
        """删除选中的名称映射"""
        current_row = self.mapping_table.currentRow()
        if current_row >= 0:
            if QMessageBox.question(
                self, '确认删除',
                '确定要删除选中的名称映射吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.mapping_table.removeRow(current_row)
                
    def save_settings(self):
        """保存所有设置"""
        # 保存选项类型顺序
        update_option_types(self.option_types)
        
        # 保存选项值
        update_type_options(self.type_options)
        
        # 保存名称映射
        mapping = {}
        for row in range(self.mapping_table.rowCount()):
            key = self.mapping_table.item(row, 0)
            value = self.mapping_table.item(row, 1)
            if key and value and key.text() and value.text():
                mapping[key.text()] = value.text()
        update_option_mapping(mapping)
        
        QMessageBox.information(
            self, '保存成功',
            '选项设置已更新'
        )
        self.accept()