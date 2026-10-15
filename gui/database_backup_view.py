"""
数据库备份管理视图
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QFileDialog, QTableWidget,
    QTableWidgetItem, QFrame, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import os
import shutil
from datetime import datetime
from pathlib import Path


class DatabaseBackupView(QWidget):
    """数据库备份管理视图"""
    
    def __init__(self):
        super().__init__()
        self.backup_dir = Path('backups')
        self.backup_dir.mkdir(exist_ok=True)
        self.db_path = Path('database.db')
        self.init_ui()
        self.refresh_backup_list()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_frame = self._create_title_section()
        layout.addWidget(title_frame)
        
        # 操作按钮区
        button_layout = QHBoxLayout()
        
        # 创建备份按钮
        backup_btn = QPushButton('📦 创建新备份')
        backup_btn.clicked.connect(self.create_backup)
        backup_btn.setStyleSheet(self._get_primary_button_style())
        button_layout.addWidget(backup_btn)
        
        # 恢复备份按钮
        restore_btn = QPushButton('🔄 恢复备份')
        restore_btn.clicked.connect(self.restore_backup)
        restore_btn.setStyleSheet(self._get_warning_button_style())
        button_layout.addWidget(restore_btn)
        
        # 删除备份按钮
        delete_btn = QPushButton('🗑️ 删除备份')
        delete_btn.clicked.connect(self.delete_backup)
        delete_btn.setStyleSheet(self._get_danger_button_style())
        button_layout.addWidget(delete_btn)
        
        # 刷新列表按钮
        refresh_btn = QPushButton('🔄 刷新列表')
        refresh_btn.clicked.connect(self.refresh_backup_list)
        refresh_btn.setStyleSheet(self._get_secondary_button_style())
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 备份列表表格
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels([
            '备份文件名', '创建时间', '文件大小', '备注'
        ])
        self.backup_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.backup_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.backup_table.setAlternatingRowColors(True)
        
        # 设置列宽 - 让文件名列更宽以显示完整名称
        header = self.backup_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 文件名自动拉伸
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)     # 创建时间固定宽度
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)     # 文件大小固定宽度
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # 备注自动拉伸
        self.backup_table.setColumnWidth(1, 180)  # 创建时间列宽度
        self.backup_table.setColumnWidth(2, 100)  # 文件大小列宽度
        
        self.backup_table.setStyleSheet(self._get_table_style())
        
        layout.addWidget(self.backup_table)
        
        # 状态栏
        self.status_label = QLabel('就绪')
        self.status_label.setStyleSheet('color: #666; padding: 5px;')
        layout.addWidget(self.status_label)
    
    def _create_title_section(self):
        """创建标题区域"""
        frame = QFrame()
        frame.setStyleSheet('''
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 15px;
            }
        ''')
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(5)
        
        title = QLabel('💾 数据库备份管理')
        title.setStyleSheet('''
            QLabel {
                color: #1890ff;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }
        ''')
        
        subtitle = QLabel('定期备份数据库，防止数据丢失')
        subtitle.setStyleSheet('''
            QLabel {
                color: #666666;
                font-size: 13px;
                background: transparent;
            }
        ''')
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        return frame
    
    def refresh_backup_list(self):
        """刷新备份列表"""
        try:
            self.backup_table.setRowCount(0)
            
            if not self.backup_dir.exists():
                self.backup_dir.mkdir(exist_ok=True)
                return
            
            # 获取所有备份文件
            backup_files = sorted(
                self.backup_dir.glob('database_backup_*.db'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            for backup_file in backup_files:
                row = self.backup_table.rowCount()
                self.backup_table.insertRow(row)
                
                # 文件名
                name_item = QTableWidgetItem(backup_file.name)
                self.backup_table.setItem(row, 0, name_item)
                
                # 创建时间
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                time_item = QTableWidgetItem(
                    mtime.strftime('%Y-%m-%d %H:%M:%S')
                )
                self.backup_table.setItem(row, 1, time_item)
                
                # 文件大小
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                size_item = QTableWidgetItem(f'{size_mb:.2f} MB')
                self.backup_table.setItem(row, 2, size_item)
                
                # 备注
                note_item = QTableWidgetItem('自动备份')
                self.backup_table.setItem(row, 3, note_item)
            
            self.status_label.setText(
                f'✅ 找到 {len(backup_files)} 个备份文件'
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, '错误',
                f'刷新备份列表失败:\n\n{str(e)}'
            )
    
    def create_backup(self):
        """创建新备份"""
        try:
            if not self.db_path.exists():
                QMessageBox.warning(
                    self, '警告',
                    '数据库文件不存在！'
                )
                return
            
            # 生成备份文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f'database_backup_{timestamp}.db'
            
            # 复制数据库文件
            self.status_label.setText('正在创建备份...')
            shutil.copy2(self.db_path, backup_file)
            
            QMessageBox.information(
                self, '成功',
                f'✅ 数据库备份创建成功！\n\n'
                f'备份文件: {backup_file.name}\n'
                f'文件大小: {backup_file.stat().st_size / (1024*1024):.2f} MB'
            )
            
            # 刷新列表
            self.refresh_backup_list()
            
        except Exception as e:
            QMessageBox.critical(
                self, '错误',
                f'创建备份失败:\n\n{str(e)}'
            )
            self.status_label.setText('❌ 备份失败')
    
    def restore_backup(self):
        """恢复备份"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self, '提示',
                '请先选择要恢复的备份文件！'
            )
            return
        
        # 获取选中的备份文件
        filename = self.backup_table.item(current_row, 0).text()
        backup_file = self.backup_dir / filename
        
        # 确认对话框
        reply = QMessageBox.question(
            self, '确认恢复',
            f'⚠️ 警告：恢复备份将覆盖当前数据库！\n\n'
            f'备份文件: {filename}\n'
            f'创建时间: {self.backup_table.item(current_row, 1).text()}\n\n'
            f'是否继续？\n\n'
            f'建议：在恢复前先创建当前数据库的备份。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        try:
            # 先备份当前数据库
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = self.backup_dir / f'database_backup_pre_restore_{timestamp}.db'
            if self.db_path.exists():
                shutil.copy2(self.db_path, pre_restore_backup)
            
            # 恢复备份
            self.status_label.setText('正在恢复备份...')
            shutil.copy2(backup_file, self.db_path)
            
            QMessageBox.information(
                self, '成功',
                f'✅ 数据库恢复成功！\n\n'
                f'已从备份恢复: {filename}\n'
                f'原数据库已备份为: {pre_restore_backup.name}\n\n'
                f'⚠️ 建议重启程序以确保数据正确加载。'
            )
            
            self.status_label.setText('✅ 恢复成功，建议重启程序')
            
        except Exception as e:
            QMessageBox.critical(
                self, '错误',
                f'恢复备份失败:\n\n{str(e)}'
            )
            self.status_label.setText('❌ 恢复失败')
    
    def delete_backup(self):
        """删除备份"""
        current_row = self.backup_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self, '提示',
                '请先选择要删除的备份文件！'
            )
            return
        
        # 获取选中的备份文件
        filename = self.backup_table.item(current_row, 0).text()
        backup_file = self.backup_dir / filename
        
        # 确认对话框
        reply = QMessageBox.question(
            self, '确认删除',
            f'确定要删除备份文件吗？\n\n'
            f'文件名: {filename}\n'
            f'创建时间: {self.backup_table.item(current_row, 1).text()}\n\n'
            f'此操作不可恢复！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        try:
            backup_file.unlink()
            QMessageBox.information(
                self, '成功',
                f'✅ 备份文件已删除: {filename}'
            )
            self.refresh_backup_list()
            
        except Exception as e:
            QMessageBox.critical(
                self, '错误',
                f'删除备份失败:\n\n{str(e)}'
            )
    
    def _get_primary_button_style(self):
        """主按钮样式"""
        return '''
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
        '''
    
    def _get_secondary_button_style(self):
        """次要按钮样式"""
        return '''
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #d9d9d9;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #bfbfbf;
            }
        '''
    
    def _get_warning_button_style(self):
        """警告按钮样式"""
        return '''
            QPushButton {
                background-color: #faad14;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ffc53d;
            }
            QPushButton:pressed {
                background-color: #d48806;
            }
        '''
    
    def _get_danger_button_style(self):
        """危险按钮样式"""
        return '''
            QPushButton {
                background-color: #ff4d4f;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ff7875;
            }
            QPushButton:pressed {
                background-color: #cf1322;
            }
        '''
    
    def _get_table_style(self):
        """表格样式"""
        return '''
            QTableWidget {
                background-color: white;
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #e6f7ff;
                color: #000;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #1890ff;
                font-weight: bold;
                color: #333;
            }
        '''
