"""
进度提示对话框组件
用于显示批量导入等耗时操作的进度
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class ProgressDialog(QDialog):
    """进度提示对话框"""
    
    def __init__(self, parent=None, title="处理中", message="正在处理,请稍候..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        # 设置窗口标志(禁用关闭按钮)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        
        # ⚡ 性能优化：缓存上次更新的值，避免重复设置
        self._last_value = -1
        self._last_maximum = -1
        self._last_detail = ""
        
        # 初始化UI
        self.init_ui(message)
        
        # 自动关闭定时器
        self.auto_close_timer = None
        
    def init_ui(self, message):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 提示消息
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        self.message_label.setFont(font)
        layout.addWidget(self.message_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_bar)
        
        # 详细信息标签(可选)
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.detail_label)
        
        self.setLayout(layout)
    
    def set_range(self, minimum, maximum):
        """设置进度范围"""
        if self.progress_bar.minimum() != minimum:
            self.progress_bar.setMinimum(minimum)
        if self.progress_bar.maximum() != maximum:
            self.progress_bar.setMaximum(maximum)
            self._last_maximum = maximum
    
    def set_value(self, value):
        """设置当前进度值"""
        if self._last_value != value:
            self.progress_bar.setValue(value)
            self._last_value = value
    
    def set_message(self, message):
        """更新提示消息"""
        self.message_label.setText(message)
    
    def set_detail(self, detail):
        """设置详细信息"""
        self.detail_label.setText(detail)
    
    def update_progress(self, current, total, detail=""):
        """
        更新进度
        
        Args:
            current: 当前进度
            total: 总数
            detail: 详细信息(可选)
        """
        # ⚡ 性能优化：仅在值变化时更新
        if self._last_maximum != total:
            self.progress_bar.setMaximum(total)
            self._last_maximum = total
        
        if self._last_value != current:
            self.progress_bar.setValue(current)
            self._last_value = current
        
        # 更新详细信息
        new_detail = detail if detail else f"已处理 {current}/{total}"
        if self._last_detail != new_detail:
            self.detail_label.setText(new_detail)
            self._last_detail = new_detail
    
    def set_indeterminate(self):
        """设置为不确定进度模式"""
        self.progress_bar.setRange(0, 0)
    
    def complete(self, message="处理完成!", auto_close_delay=1500):
        """
        标记为完成状态并自动关闭
        
        Args:
            message: 完成提示消息
            auto_close_delay: 自动关闭延迟(毫秒),默认1.5秒
        """
        self.set_message(message)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.detail_label.setText("✓ 操作成功")
        self.detail_label.setStyleSheet("color: #28a745; font-size: 9pt;")
        
        # 设置自动关闭
        if auto_close_delay > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.accept)
            self.auto_close_timer.start(auto_close_delay)
    
    def error(self, message="处理失败!", detail="", auto_close_delay=2000):
        """
        标记为错误状态并自动关闭
        
        Args:
            message: 错误提示消息
            detail: 详细错误信息
            auto_close_delay: 自动关闭延迟(毫秒),默认2秒
        """
        self.set_message(message)
        if detail:
            self.detail_label.setText(f"✗ {detail}")
        else:
            self.detail_label.setText("✗ 操作失败")
        self.detail_label.setStyleSheet("color: #dc3545; font-size: 9pt;")
        
        # 设置自动关闭
        if auto_close_delay > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.reject)
            self.auto_close_timer.start(auto_close_delay)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 如果有自动关闭定时器,停止它
        if self.auto_close_timer:
            self.auto_close_timer.stop()
        event.accept()


# 便捷函数
def show_progress(parent, title, message, total):
    """
    显示进度对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 提示消息
        total: 总数(用于进度条最大值)
    
    Returns:
        ProgressDialog实例
    """
    dialog = ProgressDialog(parent, title, message)
    dialog.set_range(0, total)
    dialog.show()
    return dialog
