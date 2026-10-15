"""
服务器配置对话框
用于客户端首次启动时配置服务器连接信息
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import json
import socket
from pathlib import Path


class ServerConfigDialog(QDialog):
    """服务器配置对话框"""
    
    def __init__(self, parent=None, config_path: str = "erp_settings.json"):
        super().__init__(parent)
        self.config_path = config_path
        self.server_host = ""
        self.server_port = 8001
        self.operator_name = ""
        self.local_ip = self._get_local_ip()
        
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("服务器连接设置")
        self.setModal(True)
        self.resize(450, 300)
        
        layout = QVBoxLayout()
        
        # 说明文字
        info_label = QLabel(
            "📡 <b>客户端配置</b><br>"
            "请配置服务器连接信息，客户端将通过API访问数据。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px; background-color: #e3f2fd;")
        layout.addWidget(info_label)
        
        # 服务器配置组
        server_group = QGroupBox("🖥️ 服务器配置")
        server_layout = QFormLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如: 192.168.1.3")
        self.host_input.setToolTip("输入服务器的IP地址")
        server_layout.addRow("服务器IP:", self.host_input)
        
        self.port_input = QLineEdit()
        self.port_input.setText("8001")
        self.port_input.setToolTip("服务器端口，默认8001")
        server_layout.addRow("端口:", self.port_input)
        
        # 测试连接按钮
        test_btn = QPushButton("🔌 测试连接")
        test_btn.clicked.connect(self.test_connection)
        server_layout.addRow("", test_btn)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # 操作者配置组
        operator_group = QGroupBox("👤 操作者信息")
        operator_layout = QFormLayout()
        
        self.operator_input = QLineEdit()
        self.operator_input.setPlaceholderText("例如: 张三")
        self.operator_input.setToolTip("输入您的姓名或昵称，用于操作日志记录")
        operator_layout.addRow("操作者昵称:", self.operator_input)
        
        # 显示本机IP
        ip_label = QLabel(f"<b>{self.local_ip}</b>")
        ip_label.setStyleSheet("color: #1976d2;")
        operator_layout.addRow("本机IP:", ip_label)
        
        operator_group.setLayout(operator_layout)
        layout.addWidget(operator_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("💾 保存并连接")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_and_accept)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _get_local_ip(self) -> str:
        """获取本机局域网IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def load_config(self):
        """从配置文件加载设置"""
        if not Path(self.config_path).exists():
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 解析 server_address (格式: "192.168.1.3:8001")
            server_address = config.get('server_address', '')
            if server_address and ':' in server_address:
                host, port_str = server_address.split(':', 1)
                self.host_input.setText(host)
                self.port_input.setText(port_str)
            
            # 读取操作员名称
            operator = config.get('operator_name', '')
            self.operator_input.setText(operator)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 读取现有配置
            config = {}
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 更新服务器配置
            config['server_address'] = f"{self.server_host}:{self.server_port}"
            config['operator_name'] = self.operator_name
            
            # 确保其他默认配置存在
            config.setdefault('auto_connect', True)
            config.setdefault('remember_window_size', True)
            config.setdefault('default_warning_level', 96)
            config.setdefault('warning_enabled', True)
            config.setdefault('notification_enabled', True)
            
            # 写入文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "保存失败",
                f"配置文件保存失败:\n{str(e)}"
            )
            return False
    
    def test_connection(self):
        """测试服务器连接"""
        host = self.host_input.text().strip()
        port_text = self.port_input.text().strip()
        
        if not host:
            QMessageBox.warning(self, "提示", "请输入服务器IP地址")
            return
        
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "提示", "端口必须是数字")
            return
        
        # 测试连接
        from client.api_client import APIClient
        
        client = APIClient()
        client.configure(host, port, "测试连接")
        
        try:
            result = client.health_check()
            QMessageBox.information(
                self,
                "连接成功",
                f"✅ 成功连接到服务器！\n\n"
                f"服务器: {host}:{port}\n"
                f"状态: {result.get('status', '正常')}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "连接失败",
                f"❌ 无法连接到服务器\n\n"
                f"服务器: {host}:{port}\n"
                f"错误: {str(e)}\n\n"
                f"请检查:\n"
                f"1. 服务器IP地址是否正确\n"
                f"2. 服务器程序是否已启动\n"
                f"3. 网络连接是否正常"
            )
    
    def validate_input(self) -> bool:
        """验证输入"""
        host = self.host_input.text().strip()
        port_text = self.port_input.text().strip()
        operator = self.operator_input.text().strip()
        
        if not host:
            QMessageBox.warning(self, "提示", "请输入服务器IP地址")
            return False
        
        if not port_text:
            QMessageBox.warning(self, "提示", "请输入端口号")
            return False
        
        try:
            port = int(port_text)
            if port < 1 or port > 65535:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "提示", "端口号必须是1-65535之间的数字")
            return False
        
        if not operator:
            QMessageBox.warning(self, "提示", "请输入操作者昵称")
            return False
        
        self.server_host = host
        self.server_port = port
        self.operator_name = operator
        
        return True
    
    def save_and_accept(self):
        """保存配置并关闭对话框"""
        if not self.validate_input():
            return
        
        if self.save_config():
            self.accept()
    
    def get_config(self) -> dict:
        """获取配置信息"""
        return {
            'host': self.server_host,
            'port': self.server_port,
            'operator': self.operator_name,
            'local_ip': self.local_ip
        }
