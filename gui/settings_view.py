from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QCheckBox, QFrame,
    QGroupBox, QFormLayout, QPushButton, QMessageBox,
    QScrollArea, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette

from config.settings import (
    load_settings, update_setting
)


class SettingsView(QWidget):
    # 定义信号：设置保存成功时发出
    settings_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化现代化UI - 紧凑布局支持滚动"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 主布局无边距
        main_layout.setSpacing(0)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f8f9fa;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #d0d0d0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #b0b0b0;
            }
        """)
        
        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # 设置页面标题
        title_container = self._create_title_section()
        content_layout.addWidget(title_container)
        
        # 创建设置卡片容器
        cards_container = QVBoxLayout()
        cards_container.setSpacing(6)
        
        # 操作员信息卡片（新增）
        user_card = self._create_user_info_card()
        cards_container.addWidget(user_card)
        
        # 库存设置卡片
        inventory_card = self._create_inventory_settings_card()
        cards_container.addWidget(inventory_card)
        
        # 系统设置卡片
        system_card = self._create_system_settings_card()
        cards_container.addWidget(system_card)
        
        content_layout.addLayout(cards_container)
        
        # 保存按钮
        save_button = self._create_save_button()
        content_layout.addWidget(save_button)
        
        content_layout.addStretch()
        
        # 设置滚动区域内容
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
    
    def _create_title_section(self):
        """创建标题部分 - 紧凑布局"""
        title_frame = QFrame()
        title_frame.setStyleSheet('''
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 8px;
            }
        ''')
        
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(12, 8, 12, 8)  # 减少内边距
        title_layout.setSpacing(2)  # 减少行间距
        
        title_label = QLabel('系统设置')
        title_label.setStyleSheet('''
            QLabel {
                color: #1890ff;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
                padding: 0;
                margin: 0;
            }
        ''')
        
        subtitle_label = QLabel('配置您的个性化偏好设置')
        subtitle_label.setStyleSheet('''
            QLabel {
                color: #666666;
                font-size: 13px;
                background: transparent;
                padding: 0;
                margin: 0;
            }
        ''')
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        return title_frame
    
    def _create_user_info_card(self):
        """创建操作员信息卡片"""
        card = QFrame()
        card.setStyleSheet(self._get_card_style())
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # 卡片标题
        title = QLabel('👤 操作员信息')
        title.setStyleSheet(self._get_card_title_style())
        layout.addWidget(title)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(6)
        form_layout.setVerticalSpacing(4)
        
        # 操作员昵称
        self.user_nickname = QLineEdit()
        self.user_nickname.setPlaceholderText('请输入昵称，建议使用数字或英文')
        self.user_nickname.setStyleSheet(self._get_input_style())
        self.user_nickname.setMaxLength(50)
        form_layout.addRow(self._create_label('操作员昵称:'),
                           self.user_nickname)
        
        # IP地址（只读显示）
        self.user_ip = QLabel()
        self.user_ip.setStyleSheet(self._get_readonly_style())
        form_layout.addRow(self._create_label('IP 地址:'), self.user_ip)
        
        # 角色（只读显示）
        self.user_role = QLabel()
        self.user_role.setStyleSheet(self._get_readonly_style())
        form_layout.addRow(self._create_label('用户角色:'), self.user_role)
        
        # 提示信息
        hint_label = QLabel(
            '💡 提示：修改昵称后保存，下次启动将显示新名称'
        )
        hint_label.setStyleSheet('''
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 4px 8px;
                background: #f0f9ff;
                border-left: 3px solid #1890ff;
                border-radius: 4px;
                margin-top: 4px;
            }
        ''')
        hint_label.setWordWrap(True)
        form_layout.addRow(hint_label)
        
        layout.addLayout(form_layout)
        return card
    
    def _create_inventory_settings_card(self):
        """创建库存设置卡片 - 紧凑布局"""
        card = QFrame()
        card.setStyleSheet(self._get_card_style())
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)  # 减少内边距
        layout.setSpacing(6)  # 减少间距
        
        # 卡片标题
        title = QLabel('📦 库存管理')
        title.setStyleSheet(self._get_card_title_style())
        layout.addWidget(title)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(6)  # 减少间距
        form_layout.setVerticalSpacing(4)  # 减少垂直间距
        
        # 默认预警值
        self.warning_level = QSpinBox()
        self.warning_level.setRange(0, 9999)
        self.warning_level.setSuffix(' 件')
        self.warning_level.setStyleSheet(self._get_spinbox_style())
        form_layout.addRow(self._create_label('默认预警阈值:'), self.warning_level)
        
        # 启用预警
        self.warning_enabled = QCheckBox('启用库存预警提醒')
        self.warning_enabled.setStyleSheet(self._get_checkbox_style())
        form_layout.addRow(self.warning_enabled)
        
        # 预警通知
        self.notification_enabled = QCheckBox('启用桌面通知')
        self.notification_enabled.setStyleSheet(self._get_checkbox_style())
        form_layout.addRow(self.notification_enabled)
        
        layout.addLayout(form_layout)
        return card
    
    def _create_system_settings_card(self):
        """创建系统设置卡片 - 紧凑布局"""
        card = QFrame()
        card.setStyleSheet(self._get_card_style())
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)  # 减少内边距
        layout.setSpacing(6)  # 减少间距
        
        # 卡片标题
        title = QLabel('⚙️ 系统配置')
        title.setStyleSheet(self._get_card_title_style())
        layout.addWidget(title)
        

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(6)  # 减少间距
        form_layout.setVerticalSpacing(4)  # 减少垂直间距

        # 自动刷新间隔
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(30, 300)
        self.refresh_interval.setValue(60)
        self.refresh_interval.setSuffix(' 秒')
        self.refresh_interval.setStyleSheet(self._get_spinbox_style())
        form_layout.addRow(self._create_label('自动刷新间隔:'),
                           self.refresh_interval)

        # 启用调试模式
        self.debug_mode = QCheckBox('启用调试模式')
        self.debug_mode.setStyleSheet(self._get_checkbox_style())
        form_layout.addRow(self.debug_mode)

        layout.addLayout(form_layout)
        return card
    
    def _create_save_button(self):
        """创建保存按钮 - 极简样式"""
        save_btn = QPushButton('💾 保存所有设置')
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet('''
            QPushButton {
                background-color: #52c41a;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #73d13d;
            }
            QPushButton:pressed {
                background-color: #389e0d;
            }
        ''')
        return save_btn
    
    def _get_card_style(self):
        """获取卡片样式 - 极简边框，确保内容完整显示"""
        return '''
            QFrame {
                background: white;
                border: 1px solid #f0f0f0;
                border-radius: 6px;
                margin: 1px;
                min-height: 50px;
            }
            QFrame:hover {
                border-color: #e0e0e0;
            }
        '''
    
    def _get_card_title_style(self):
        """获取卡片标题样式 - 极简边框"""
        return '''
            QLabel {
                color: #1890ff;
                font-size: 16px;
                font-weight: bold;
                padding: 0 0 6px 0;
                border-bottom: 1px solid #f5f5f5;
                margin-bottom: 6px;
            }
        '''
    
    def _create_label(self, text):
        """创建样式化标签 - 紧凑布局"""
        label = QLabel(text)
        label.setStyleSheet('''
            QLabel {
                color: #333;
                font-size: 13px;
                font-weight: 500;
                padding: 2px 0;
            }
        ''')
        return label
    
    def _get_input_style(self):
        """获取输入框样式 - 极简边框"""
        return '''
            QLineEdit {
                padding: 6px 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
                background: white;
                min-height: 18px;
            }
            QLineEdit:focus {
                border-color: #1890ff;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #d0d0d0;
            }
        '''
    
    def _get_readonly_style(self):
        """获取只读样式 - 极简边框"""
        return '''
            QLabel {
                padding: 6px 8px;
                border: 1px solid #f0f0f0;
                border-radius: 4px;
                background: #fafafa;
                color: #666;
                font-size: 13px;
            }
        '''
    
    def _get_checkbox_style(self):
        """获取复选框样式 - 极简边框"""
        return '''
            QCheckBox {
                font-size: 13px;
                color: #333;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #d0d0d0;
                border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:hover {
                border-color: #1890ff;
            }
            QCheckBox::indicator:checked {
                background: #1890ff;
                border-color: #1890ff;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEwIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik04LjUgMUwzLjUgNkwxLjUgNCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPHN2Zz4K);
            }
        '''
    
    def _get_spinbox_style(self):
        """获取数字输入框样式 - 极简边框"""
        return '''
            QSpinBox {
                padding: 6px 8px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                font-size: 13px;
                background: white;
                min-width: 100px;
            }
            QSpinBox:focus {
                border-color: #1890ff;
            }
            QSpinBox:hover {
                border-color: #d0d0d0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                border: none;
                background: #f5f5f5;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #e8e8e8;
            }
        '''

    def load_settings(self):
        """加载设置"""
        settings = load_settings()
        
        # 操作员名称（扁平格式）
        self.user_nickname.setText(settings.get('operator_name', ''))
        
        # 获取本机IP地址（而不是服务器IP）
        from utils.operator import get_operator_info
        operator_info = get_operator_info()
        self.user_ip.setText(operator_info['ip'])
        
        # 角色固定为操作员
        self.user_role.setText('操作员')
        
        # 库存设置（扁平格式）
        self.warning_level.setValue(
            settings.get('default_warning_level', 96))
        self.warning_enabled.setChecked(
            settings.get('warning_enabled', True))
        self.notification_enabled.setChecked(
            settings.get('notification_enabled', True))

    def save_settings(self):
        """保存设置 - 直接保存到本地配置文件"""
        try:
            from config.settings import save_settings, load_settings
            
            # 操作员信息
            user_nickname = self.user_nickname.text().strip()
            
            # 库存设置
            warning_level_value = self.warning_level.value()
            warning_enabled = self.warning_enabled.isChecked()
            notification_enabled = self.notification_enabled.isChecked()
            
            if not user_nickname:
                QMessageBox.warning(self, '提示', '请输入操作员昵称')
                return
            
            # 加载现有配置
            settings = load_settings()
            
            # 更新配置（扁平格式）
            settings['operator_name'] = user_nickname
            settings['default_warning_level'] = warning_level_value
            settings['warning_enabled'] = warning_enabled
            settings['notification_enabled'] = notification_enabled
            
            # 保存配置
            if save_settings(settings):
                # 发送信号通知其他视图刷新
                self.settings_saved.emit()
                
                # 显示成功消息
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle('保存成功')
                msg.setText('✅ 设置已成功保存！')
                info_text = (
                    f'操作员昵称: {user_nickname}\n'
                    f'库存预警阈值: {warning_level_value} 件\n'
                    f'预警启用: {"是" if warning_enabled else "否"}\n'
                    f'通知启用: {"是" if notification_enabled else "否"}\n\n'
                    f'💡 提示：\n'
                    f'• 修改昵称后下次操作记录将显示新昵称\n'
                    f'• 预警设置将立即生效'
                )
                msg.setInformativeText(info_text)
                msg.setStyleSheet('''
                    QMessageBox {
                        background: white;
                        border-radius: 8px;
                    }
                    QMessageBox QLabel {
                        color: #333;
                        font-size: 14px;
                    }
                ''')
                msg.exec()
            else:
                raise Exception("保存配置失败")
            
        except Exception as e:
            # 显示错误消息
            err_msg = QMessageBox()
            err_msg.setIcon(QMessageBox.Icon.Critical)
            err_msg.setWindowTitle('保存失败')
            err_msg.setText(f'❌ 保存设置时出错')
            err_msg.setInformativeText(f'错误信息: {str(e)}')
            err_msg.setStyleSheet('''
                QMessageBox {
                    background: white;
                }
                QMessageBox QLabel {
                    color: #d32f2f;
                }
            ''')
            err_msg.exec()
