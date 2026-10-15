import sys
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSlider, QSpinBox, QCheckBox, QPushButton, 
                             QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt

# 添加项目根目录到路径，以便导入 config
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    from config.settings import CONFIG_FILE, load_settings, save_settings
except ImportError:
    # 如果导入失败，尝试直接定位文件
    CONFIG_FILE = Path("erp_settings.json")
    def load_settings():
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    def save_settings(settings):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True

class CacheControlTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("服务端缓存刷新频率控制")
        self.setFixedSize(400, 300)
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 说明区域
        info_label = QLabel("此工具用于控制客户端自动刷新数据的频率。\n"
                          "降低刷新频率可以显著减少服务端卡顿。\n"
                          "设置为 0 表示关闭自动刷新。")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 控制区域
        group = QGroupBox("刷新频率设置")
        group_layout = QVBoxLayout(group)

        # 启用/禁用
        self.enable_cb = QCheckBox("启用自动刷新")
        self.enable_cb.stateChanged.connect(self.on_enable_changed)
        group_layout.addWidget(self.enable_cb)

        # 滑块和数字框容器
        controls_layout = QHBoxLayout()
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(5, 300) # 5秒到5分钟
        self.slider.setSingleStep(5)
        self.slider.valueChanged.connect(self.on_slider_changed)
        
        self.spinbox = QSpinBox()
        self.spinbox.setRange(5, 300)
        self.spinbox.setSuffix(" 秒")
        self.spinbox.valueChanged.connect(self.on_spinbox_changed)
        
        controls_layout.addWidget(self.slider)
        controls_layout.addWidget(self.spinbox)
        
        group_layout.addLayout(controls_layout)
        
        # 预设按钮
        presets_layout = QHBoxLayout()
        self.btn_fast = QPushButton("高频 (10s)")
        self.btn_fast.clicked.connect(lambda: self.set_interval(10))
        self.btn_normal = QPushButton("标准 (60s)")
        self.btn_normal.clicked.connect(lambda: self.set_interval(60))
        self.btn_slow = QPushButton("低频 (300s)")
        self.btn_slow.clicked.connect(lambda: self.set_interval(300))
        
        presets_layout.addWidget(self.btn_fast)
        presets_layout.addWidget(self.btn_normal)
        presets_layout.addWidget(self.btn_slow)
        
        group_layout.addLayout(presets_layout)
        layout.addWidget(group)

        # 保存按钮
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("background-color: #0078d7; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_btn)

        layout.addStretch()

    def load_current_settings(self):
        settings = load_settings()
        # 读取 client.refresh_interval，默认为 60000 (60秒)
        # 注意：配置文件中通常存的是毫秒，但这里我们用秒展示
        interval_ms = settings.get('client', {}).get('refresh_interval', 60000)
        
        if interval_ms <= 0:
            self.enable_cb.setChecked(False)
            self.set_interval(60) # 默认显示60
            self.slider.setEnabled(False)
            self.spinbox.setEnabled(False)
        else:
            self.enable_cb.setChecked(True)
            self.set_interval(int(interval_ms / 1000))

    def on_enable_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.slider.setEnabled(enabled)
        self.spinbox.setEnabled(enabled)
        self.btn_fast.setEnabled(enabled)
        self.btn_normal.setEnabled(enabled)
        self.btn_slow.setEnabled(enabled)

    def on_slider_changed(self, value):
        self.spinbox.setValue(value)

    def on_spinbox_changed(self, value):
        self.slider.setValue(value)

    def set_interval(self, seconds):
        self.slider.setValue(seconds)
        self.spinbox.setValue(seconds)

    def save_config(self):
        try:
            settings = load_settings()
            if 'client' not in settings:
                settings['client'] = {}
            
            if self.enable_cb.isChecked():
                # 保存为毫秒
                settings['client']['refresh_interval'] = self.spinbox.value() * 1000
            else:
                # 0 表示关闭
                settings['client']['refresh_interval'] = 0
            
            if save_settings(settings):
                QMessageBox.information(self, "成功", "设置已保存！\n请重启客户端以生效。")
            else:
                QMessageBox.warning(self, "失败", "保存设置失败，请检查文件权限。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CacheControlTool()
    window.show()
    sys.exit(app.exec())
