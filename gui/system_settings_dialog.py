from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QFrame
)


class SystemSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化设置对话框UI"""
        self.setWindowTitle('系统设置')
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 设置项分组
        settings_frame = QFrame()
        settings_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        settings_frame.setStyleSheet('''
            QFrame {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
        ''')
        settings_layout = QVBoxLayout(settings_frame)
        
        # 全局库存警告阈值
        warning_layout = QHBoxLayout()
        warning_label = QLabel('全局库存警告阈值:')
        self.warning_spin = QSpinBox()
        self.warning_spin.setMinimum(1)
        self.warning_spin.setMaximum(1000)
        self.warning_spin.setValue(10)
        self.warning_spin.setStyleSheet('''
            QSpinBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                min-width: 80px;
            }
        ''')
        warning_layout.addWidget(warning_label)
        warning_layout.addWidget(self.warning_spin)
        warning_layout.addStretch()
        settings_layout.addLayout(warning_layout)
        
        # TODO: 添加其他设置项...
        
        layout.addWidget(settings_frame)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 20px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
        ''')
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 20px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bb2d3b;
            }
        ''')
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def save_settings(self):
        """保存设置"""
        # TODO: 在数据库中保存设置
        self.accept()