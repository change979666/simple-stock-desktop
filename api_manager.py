import sys
import os
import subprocess
import time
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QTextEdit, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from database.session import SessionLocal, get_database_path
from database.models import ActionLog
from utils.operator import get_operator_info
from utils.ensure_db import ensure_database_exists


def get_recent_action_logs(limit=50):
    """获取最近的操作日志"""
    try:
        with SessionLocal() as db:
            logs = db.query(ActionLog).order_by(
                ActionLog.created_at.desc()
            ).limit(limit).all()
            
            result = []
            for log in logs:
                result.append({
                    'timestamp': log.created_at,
                    'operator': log.operator_info or '系统',
                    'description': log.action or '',  # 使用正确的字段名
                })
            return result
    except Exception:
        return []


class APIServerManager(QThread):
    """API服务器管理线程 - 优化版"""
    status_changed = pyqtSignal(str)  # 状态变化信号
    log_message = pyqtSignal(str)     # 日志消息信号
    
    def __init__(self):
        super().__init__()
        self.server_process = None
        self.is_running = False
        self.max_startup_attempts = 3  # 最大启动尝试次数
        self.startup_timeout = 10      # 启动超时时间(秒)
        
    def start_server(self):
        """启动API服务器 - 增强版"""
        # 先检查是否已经运行
        if self.server_process and self.server_process.poll() is None:
            self.log_message.emit("服务器已在运行中")
            self.status_changed.emit("运行中")
            self.is_running = True
            return
        
        # 确保没有残留进程
        self.cleanup_orphaned_processes()
            
        try:
            # 准备启动API服务器进程
            if sys.platform == "win32":
                flags = subprocess.CREATE_NO_WINDOW
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = 0  # SW_HIDE
            else:
                flags = 0
                startup_info = None
            
            # 创建日志目录
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # 准备日志文件
            log_file = os.path.join(logs_dir, f"api_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            
            # 启动进程并带上keep-alive参数，使用端口8001避免冲突
            self.server_process = subprocess.Popen(
                [sys.executable, "api_server.py", "--keep-alive", "--port", "8001"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                creationflags=flags,
                startupinfo=startup_info
            )
            
            self.log_message.emit(f"正在启动API服务器 (PID: {self.server_process.pid})...")
            
            # 带超时的等待服务器启动
            start_time = time.time()
            attempt = 0
            started = False
            
            while attempt < self.max_startup_attempts and time.time() - start_time < self.startup_timeout:
                try:
                    # 使用短超时进行尝试连接
                    with requests.Session() as session:
                        session.mount('http://', requests.adapters.HTTPAdapter(
                            max_retries=2,
                            pool_connections=1,
                            pool_maxsize=1
                        ))
                        
                        response = session.get(
                            "http://localhost:8001/api/health",
                            timeout=(2, 3),
                            verify=False,
                            headers={'User-Agent': 'APIManager/1.0'}
                        )
                        
                        if response.status_code == 200:
                            started = True
                            break
                except requests.exceptions.RequestException:
                    attempt += 1
                    wait_time = min(1.0 * attempt, 2.0)  # 指数退避，最多等待2秒
                    time.sleep(wait_time)
            
            # 检查启动结果
            if started:
                self.is_running = True
                self.status_changed.emit("运行中")
                self.log_message.emit("API服务器启动成功")
            else:
                # 检查进程是否仍然存在
                if self.server_process.poll() is None:
                    # 进程仍在运行，但API未响应
                    self.log_message.emit("API服务器进程已启动但未能正常响应请求")
                    self.status_changed.emit("运行中")
                    self.is_running = True
                else:
                    # 进程已退出
                    self.status_changed.emit("启动失败")
                    return_code = self.server_process.returncode
                    self.log_message.emit(f"API服务器启动失败，进程返回代码: {return_code}")
                    self.server_process = None
                
        except Exception as e:
            self.status_changed.emit("启动失败")
            self.log_message.emit(f"启动API服务器失败: {str(e)}")
            if self.server_process and self.server_process.poll() is None:
                try:
                    self.server_process.terminate()
                except Exception:
                    pass
            self.server_process = None
    
    def cleanup_orphaned_processes(self):
        """清理可能遗留的进程"""
        try:
            if sys.platform == "win32":
                # 在Windows上使用tasklist查找Python进程
                output = subprocess.check_output(
                    ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                    universal_newlines=True
                )
                
                # 仅终止那些运行api_server.py的进程
                for line in output.strip().split("\n")[1:]:  # 跳过标题行
                    if not line:
                        continue
                    parts = line.strip('"').split('","')
                    if len(parts) >= 2:
                        pid = parts[1]
                        try:
                            # 使用wmic获取命令行参数
                            cmd_line = subprocess.check_output(
                                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:csv"],
                                universal_newlines=True
                            )
                            if "api_server.py" in cmd_line:
                                subprocess.call(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                self.log_message.emit(f"清理了遗留的API服务器进程 (PID: {pid})")
                        except Exception:
                            pass
            else:
                # 在Linux/Mac上可以使用pgrep和pkill
                try:
                    pids = subprocess.check_output(
                        ["pgrep", "-f", "api_server.py"],
                        universal_newlines=True
                    ).strip()
                    for pid in pids.split("\n"):
                        if pid:
                            subprocess.call(["kill", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            self.log_message.emit(f"清理了遗留的API服务器进程 (PID: {pid})")
                except Exception:
                    pass
        except Exception as e:
            self.log_message.emit(f"清理遗留进程时出错: {str(e)}")
                
    
    def stop_server(self):
        """停止API服务器 - 增强版"""
        try:
            # 先获取PID，以便后续检查
            pid = None
            if self.server_process:
                pid = self.server_process.pid
                self.log_message.emit(f"正在停止API服务器 (PID: {pid})...")
                
                # 尝试优雅终止
                try:
                    self.server_process.terminate()
                    
                    # 等待进程终止，带超时
                    try:
                        exit_code = self.server_process.wait(timeout=5)
                        self.log_message.emit(f"API服务器已停止，退出代码: {exit_code}")
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制终止
                        self.log_message.emit("API服务器没有响应终止信号，尝试强制终止...")
                        self.server_process.kill()
                        try:
                            self.server_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.log_message.emit("无法终止API服务器进程")
                finally:
                    # 无论如何，重置进程引用
                    self.server_process = None
            
            # 查找并清理其他可能存在的API服务器进程
            self.cleanup_orphaned_processes()
            
            # 更新状态
            self.is_running = False
            self.status_changed.emit("已停止")
            
        except Exception as e:
            self.log_message.emit(f"停止API服务器失败: {str(e)}")
            self.is_running = False
            self.status_changed.emit("已停止")
            self.server_process = None  # 确保重置进程引用
    
    def check_server_status(self):
        """检查服务器状态 - 增强版"""
        # 首先检查进程是否还在运行
        if self.server_process is None or self.server_process.poll() is not None:
            # 进程不存在或已结束
            if self.is_running:
                self.is_running = False
                self.log_message.emit("API服务器进程已退出")
            return False
            
        # 再检查API是否响应
        try:
            # 使用会话管理和优化的超时设置
            with requests.Session() as session:
                session.mount('http://', requests.adapters.HTTPAdapter(
                    max_retries=1,
                    pool_connections=1,
                    pool_maxsize=1,
                    pool_block=True
                ))
                
                # 设置较短的超时，使用专用的健康检查端点
                response = session.get(
                    "http://localhost:8001/api/health",
                    timeout=(1.5, 2.0),  # 连接和读取超时
                    verify=False,
                    headers={'User-Agent': 'APIManager/1.0'}
                )
                
                if response.status_code == 200:
                    if not self.is_running:
                        self.is_running = True
                        self.log_message.emit("API服务器已恢复响应")
                    return True
                else:
                    self.log_message.emit(f"API服务器返回异常状态码: {response.status_code}")
                    return False
                    
        except requests.exceptions.RequestException:
            # 连接失败但进程仍在运行，可能是启动中或暂时卡住
            return self.is_running
        except Exception as e:
            self.log_message.emit(f"检查服务器状态时发生错误: {str(e)}")
            return self.is_running


class APIManagerWindow(QMainWindow):
    """API管理器主窗口 - 简化版"""
    
    def __init__(self):
        super().__init__()
        self.server_manager = APIServerManager()
        self.operator_info = get_operator_info()
        self.init_ui()
        self.setup_connections()
        self.setup_timers()
        
    def init_ui(self):
        """初始化用户界面 - 简化版，只显示服务状态和控制按钮"""
        self.setWindowTitle("API服务器控制")
        self.setGeometry(100, 100, 400, 250)  # 减小窗口尺寸
        self.setStyleSheet(self.get_stylesheet())
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 检查数据库是否可用
        db_path = get_database_path()
        self.add_message(f"使用数据库: {db_path}")
        
        if not ensure_database_exists():
            self.add_message("警告：数据库文件可能不可用，请检查数据库设置")
        
        # 服务控制区域
        control_group = self.create_server_control_group()
        main_layout.addWidget(control_group)
        
        # 简单日志显示
        log_group = QGroupBox("服务日志")
        log_layout = QVBoxLayout(log_group)
        
        self.system_log = QTextEdit()
        self.system_log.setFont(QFont("Consolas", 9))
        self.system_log.setReadOnly(True)
        log_layout.addWidget(self.system_log)
        
        main_layout.addWidget(log_group)
        
    def create_user_info_group(self):
        """创建用户信息组"""
        group = QGroupBox("👤 用户信息")
        layout = QVBoxLayout(group)
        
        # 用户昵称
        if isinstance(self.operator_info, dict):
            nickname = self.operator_info.get('name', '未设置昵称')
            ip_address = self.operator_info.get('ip', 'localhost')
            display_text = self.operator_info.get(
                'display', f'{nickname} ({ip_address})'
            )
        else:
            display_text = str(self.operator_info)
            nickname = '未设置昵称'
            ip_address = 'localhost'
        
        # 昵称标签
        self.nickname_label = QLabel(f"昵称: {nickname}")
        self.nickname_label.setFont(QFont("微软雅黑", 11, QFont.Weight.Bold))
        layout.addWidget(self.nickname_label)
        
        # IP地址标签
        self.ip_label = QLabel(f"IP地址: {ip_address}")
        self.ip_label.setFont(QFont("微软雅黑", 10))
        layout.addWidget(self.ip_label)
        
        # 完整显示
        self.full_info_label = QLabel(f"完整信息: {display_text}")
        self.full_info_label.setFont(QFont("微软雅黑", 9))
        self.full_info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.full_info_label)
        
        # 当前时间
        self.time_label = QLabel()
        self.time_label.setFont(QFont("微软雅黑", 9))
        self.time_label.setStyleSheet("color: #888;")
        layout.addWidget(self.time_label)
        
        return group
        
    def create_server_control_group(self):
        """创建服务器控制组 - 简化版"""
        group = QGroupBox("API服务器控制")
        layout = QVBoxLayout(group)
        
        # 显示本地IP地址
        import socket
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except:
                return 'localhost'
        
        local_ip = get_local_ip()
        
        # 服务地址 - 突出显示
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("服务IP地址:"))
        self.ip_label = QLabel(f"<b>{local_ip}</b>")
        self.ip_label.setFont(QFont("Consolas", 11))
        self.ip_label.setStyleSheet("color: #0066cc; background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        ip_layout.addWidget(self.ip_label)
        ip_layout.addStretch()
        layout.addLayout(ip_layout)
        
        # 端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_label = QLabel("<b>8001</b>")
        self.port_label.setFont(QFont("Consolas", 11))
        self.port_label.setStyleSheet("color: #0066cc; background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        port_layout.addWidget(self.port_label)
        port_layout.addStretch()
        layout.addLayout(port_layout)
        
        # 状态显示
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("服务状态:"))
        self.status_label = QLabel("未启动")
        self.status_label.setFont(QFont("微软雅黑", 11, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #f44336;")  # 红色表示未启动
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 控制按钮 - 简化为启动和停止
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("启动服务")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        self.stop_btn = QPushButton("停止服务")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        layout.addLayout(button_layout)
        
        return group
    
    def create_log_section(self):
        """创建日志区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建标签页式布局
        log_layout = QHBoxLayout()
        
        # 系统日志
        system_group = QGroupBox("📋 系统日志")
        system_layout = QVBoxLayout(system_group)
        
        self.system_log = QTextEdit()
        self.system_log.setFont(QFont("Consolas", 9))
        self.system_log.setMaximumHeight(200)
        system_layout.addWidget(self.system_log)
        
        # 清空日志按钮
        clear_system_btn = QPushButton("清空日志")
        clear_system_btn.clicked.connect(self.system_log.clear)
        system_layout.addWidget(clear_system_btn)
        
        log_layout.addWidget(system_group)
        
        # 在线用户表格
        action_group = QGroupBox("👥 在线用户")
        action_layout = QVBoxLayout(action_group)
        
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(3)
        self.action_table.setHorizontalHeaderLabels(["连接时间", "用户", "IP地址"])
        
        # 设置表格样式
        header = self.action_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        action_layout.addWidget(self.action_table)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新日志")
        refresh_btn.clicked.connect(self.load_action_logs)
        action_layout.addWidget(refresh_btn)
        
        log_layout.addWidget(action_group)
        layout.addLayout(log_layout)
        
        return widget
        
    def setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        
        # 服务器管理器信号连接
        self.server_manager.status_changed.connect(self.update_status)
        self.server_manager.log_message.connect(self.add_log_message)
        
    def setup_timers(self):
        """设置定时器"""
        # 状态检查定时器 - 适当的检查间隔
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_server_status_safe)
        self.status_timer.start(5000)  # 每5秒检查一次，保证状态更新及时
        
        # 初始化
        self.check_server_status_safe()
        
    def start_server(self):
        """启动服务器"""
        # 如果服务器已经在运行，则不再启动
        if self.server_manager.is_running:
            self.add_log_message("服务器已经在运行中")
            return
            
        self.add_log_message("正在启动API服务器...")
        self.start_btn.setEnabled(False)  # 禁用启动按钮，防止重复点击
        try:
            self.server_manager.start_server()
        except Exception as e:
            self.add_log_message(f"启动服务器时出错: {str(e)}")
        finally:
            self.start_btn.setEnabled(True)
        
    def stop_server(self):
        """停止服务器"""
        if not self.server_manager.is_running:
            self.add_log_message("服务器未运行")
            return
            
        # 弹出简单确认对话框
        reply = QMessageBox.question(
            self,
            '确认停止',
            '确定要停止API服务器吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.add_log_message("正在停止API服务器...")
            self.stop_btn.setEnabled(False)  # 禁用停止按钮，防止重复点击
            try:
                self.server_manager.stop_server()
            except Exception as e:
                self.add_log_message(f"停止服务器时出错: {str(e)}")
            finally:
                self.stop_btn.setEnabled(True)
        
    def test_connection(self):
        """测试连接"""
        self.add_log_message("开始测试服务器连接...")
        
        try:
            # 使用统一的会话管理
            with requests.Session() as session:
                session.mount('http://', requests.adapters.HTTPAdapter(
                    max_retries=3,
                    pool_connections=1,
                    pool_maxsize=1,
                    pool_block=True
                ))
                
                # 检查产品API接口
                self.add_log_message("检查产品API接口...")
                response = session.get(
                    "http://localhost:8000/products/",
                    timeout=(3, 5),  # 增加超时时间
                    verify=False,
                    headers={
                        'Accept': 'application/json',
                        'User-Agent': 'APIManager/1.0'
                    }
                )
                
                if response.status_code != 200:
                    raise requests.exceptions.RequestException(
                        f"产品API接口异常，状态码: {response.status_code}"
                    )
                    
                data = response.json()
                if not isinstance(data, list):
                    raise ValueError("API返回数据格式错误")
                    
                msg = f"✅ API接口测试成功\n获取到 {len(data)} 个产品"
                self.add_log_message(msg)
                
                # 检查API文档
                self.add_log_message("检查API文档访问...")
                response = session.get(
                    "http://localhost:8000/docs",
                    timeout=(3, 5),
                    verify=False,
                    headers={
                        'Accept': 'text/html',
                        'User-Agent': 'APIManager/1.0'
                    }
                )
                
                if response.status_code != 200:
                    raise requests.exceptions.RequestException(
                        f"API文档访问失败，状态码: {response.status_code}"
                    )
                    
                self.add_log_message("✅ API文档访问正常")
                
                # 更新状态
                if not self.server_manager.is_running:
                    self.update_status("运行中")
                    self.server_manager.is_running = True
                
                QMessageBox.information(
                    self,
                    "连接测试",
                    "API服务器运行正常\n" + msg
                )
                
        except requests.exceptions.ConnectionError:
            err_msg = "无法连接到服务器"
            self.add_log_message(f"❌ {err_msg}")
            QMessageBox.critical(self, "连接测试", err_msg)
            
        except requests.exceptions.Timeout:
            err_msg = "服务器响应超时，请检查服务器状态"
            self.add_log_message(f"❌ {err_msg}")
            QMessageBox.critical(self, "连接测试", err_msg)
            
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            self.add_log_message(f"❌ {err_msg}")
            QMessageBox.critical(self, "连接测试", err_msg)
            
        except Exception as e:
            err_msg = f"未知错误: {str(e)[:100]}"
            self.add_log_message(f"❌ {err_msg}")
            QMessageBox.critical(self, "连接测试", err_msg)
    
    def update_status(self, status):
        """更新状态显示"""
        # 检查进程状态
        is_process_running = (
            self.server_manager.server_process 
            and self.server_manager.server_process.poll() is None
        )
        
        if is_process_running and status != "运行中":
            status = "运行中"  # 强制更新状态
            self.server_manager.is_running = True
            
        self.status_label.setText(status)
        
        # 根据状态设置颜色和按钮状态
        if status == "运行中":
            style = "color: #4CAF50; font-weight: bold;"
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        elif status == "已停止":
            style = "color: #f44336; font-weight: bold;"
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        else:
            style = "color: #FF9800; font-weight: bold;"
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
        self.status_label.setStyleSheet(style)
    
    def add_log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.system_log.append(log_entry)
        
        # 自动滚动到底部
        cursor = self.system_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.system_log.setTextCursor(cursor)
        
    def add_message(self, message):
        """添加消息到日志（初始化时使用）"""
        if hasattr(self, 'system_log'):
            self.add_log_message(message)
        else:
            print(message)  # 如果UI还没初始化，则打印到控制台
    
    def check_server_status_safe(self):
        """以更安全的方式检查服务器状态"""
        if hasattr(self, '_is_checking') and self._is_checking:
            return  # 避免重复检查
            
        self._is_checking = True
        try:
            is_running = self.server_manager.check_server_status()
            self.update_status("运行中" if is_running else "已停止")
        except Exception as e:
            self.add_log_message(f"检查状态出错: {str(e)}")
            self.update_status("已停止")
        finally:
            self._is_checking = False
    
    def load_action_logs(self):
        """加载在线用户信息"""
        try:
            # 获取在线用户列表
            online_users = [
                {
                    'time': datetime.now(),
                    'name': self.operator_info.get('name', '未知用户'),
                    'ip': self.operator_info.get('ip', 'localhost')
                }
            ]
            
            # 更新表格
            self.action_table.setRowCount(len(online_users))
            
            for i, user in enumerate(online_users):
                # 连接时间
                time_str = user['time'].strftime("%H:%M:%S")
                time_item = QTableWidgetItem(time_str)
                time_item.setFont(QFont("Consolas", 9))
                self.action_table.setItem(i, 0, time_item)
                
                # 用户昵称
                name_item = QTableWidgetItem(user['name'])
                name_item.setFont(QFont("微软雅黑", 9))
                self.action_table.setItem(i, 1, name_item)
                
                # IP地址
                ip_item = QTableWidgetItem(user['ip'])
                ip_item.setFont(QFont("Consolas", 9))
                self.action_table.setItem(i, 2, ip_item)
            
        except Exception as e:
            self.add_log_message(f"更新在线用户列表失败: {str(e)}")
    
    def get_stylesheet(self):
        """获取样式表 - 简化版"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QLabel {
            color: #333333;
        }
        QTextEdit {
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fafafa;
        }
        QPushButton {
            min-height: 30px;
            border-radius: 4px;
            font-weight: bold;
        }
        """


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用现代化样式
    
    # 创建主窗口
    window = APIManagerWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec())


if __name__ == "__main__":
    main()