"""
数据分析视图
展示库存趋势、销量排行、颜色分布等图表
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QScrollArea, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer, QEvent
import pyqtgraph as pg
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class DataLoadThread(QThread):
    """后台数据加载线程"""
    data_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client, days=30, start_date=None, end_date=None):
        super().__init__()
        self.api_client = api_client
        self.days = days
        self.start_date = start_date
        self.end_date = end_date
    
    def run(self):
        try:
            # 批量获取所有数据
            params = {'days': self.days, 'top_limit': 10}
            if self.start_date:
                params['start_date'] = self.start_date
            if self.end_date:
                params['end_date'] = self.end_date
            
            data = self.api_client._request(
                'GET',
                '/api/analytics/batch',
                params=params
            )
            self.data_loaded.emit(data)
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.error_occurred.emit(str(e))


class AnalyticsView(QWidget):
    """数据分析主视图"""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.load_thread = None
        self.init_ui()
        # 初始化后自动加载数据
        QTimer.singleShot(100, self.load_data)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 让图表的滚轮事件传递给滚动区域"""
        if event.type() == QEvent.Type.Wheel:
            # 忽略图表控件的滚轮事件,让它传递给父控件(滚动区域)
            return False
        return super().eventFilter(obj, event)
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # 确保滚动区域接收滚轮事件
        scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        scroll.viewport().setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 图表容器
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setSpacing(5)
        
        # 1. 销量趋势图（柱状图）
        self.sales_trend_group = self.create_chart_group(
            "📊 销量趋势图",
            ""
        )
        # 禁用鼠标交互（不可拖动）
        self.sales_trend_chart.setMouseEnabled(x=False, y=False)
        charts_layout.addWidget(self.sales_trend_group)
        
        # 2. 每日订单量趋势图（柱状图）
        self.daily_orders_group = self.create_chart_group(
            "📦 每日订单量",
            ""
        )
        self.daily_orders_chart.setMouseEnabled(x=False, y=False)
        charts_layout.addWidget(self.daily_orders_group)
        
        # 3. TOP 10 热销产品（柱状图）
        self.top_products_group = self.create_chart_group(
            "🏆 TOP 10 热销产品",
            ""
        )
        # 禁用鼠标交互（不可拖动）
        self.top_products_chart.setMouseEnabled(x=False, y=False)
        charts_layout.addWidget(self.top_products_group)
        
        # 4. 多件订单统计（柱状图）
        self.multi_item_orders_group = self.create_chart_group(
            "📊 多件订单统计",
            ""
        )
        self.multi_item_orders_chart.setMouseEnabled(x=False, y=False)
        charts_layout.addWidget(self.multi_item_orders_group)
        
        scroll.setWidget(charts_widget)
        layout.addWidget(scroll)
        
        # 设置PyQtGraph全局样式（浅灰色背景）
        pg.setConfigOption('background', '#f5f5f5')  # 浅灰色背景
        pg.setConfigOption('foreground', '#2c3e50')  # 深色文字
        
    def create_toolbar(self) -> QWidget:
        """创建工具栏"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("📊 数据分析中心")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 时间范围选择
        layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近7天", "最近30天", "上个月"])
        self.time_range_combo.setCurrentIndex(0)  # 默认7天
        self.time_range_combo.currentIndexChanged.connect(self.on_time_range_changed)
        layout.addWidget(self.time_range_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新数据")
        self.refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(self.refresh_btn)
        
        return toolbar
    
    def create_chart_group(self, title: str, description: str) -> QGroupBox:
        """创建图表组"""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 5, 10, 10)  # 减小上边距
        layout.setSpacing(5)  # 减小控件间距
        
        # 设置组框样式,确保不拦截滚动事件
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        # 描述文字
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(desc_label)
        
        # 图表控件
        chart_widget = pg.PlotWidget()
        chart_widget.setMinimumHeight(300)
        # 确保图表不拦截滚轮事件 - 安装事件过滤器
        chart_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        chart_widget.viewport().installEventFilter(self)
        layout.addWidget(chart_widget)
        
        # 保存引用
        if "销量趋势" in title:
            self.sales_trend_chart = chart_widget
        elif "热销产品" in title:
            self.top_products_chart = chart_widget
        elif "每日订单量" in title:
            self.daily_orders_chart = chart_widget
        elif "多件订单" in title:
            self.multi_item_orders_chart = chart_widget
        
        return group
    
    def on_time_range_changed(self):
        """时间范围变化"""
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        if self.load_thread and self.load_thread.isRunning():
            return
        
        # 禁用刷新按钮
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ 加载中...")
        
        # 获取时间范围
        time_range_text = self.time_range_combo.currentText()
        
        start_date = None
        end_date = None
        days = 30
        
        if time_range_text == "上个月":
            # 计算上个月的完整日期范围
            from datetime import datetime, timedelta
            today = datetime.now().date()
            # 本月第一天
            first_day_current_month = today.replace(day=1)
            # 上个月最后一天
            last_day_last_month = first_day_current_month - timedelta(days=1)
            # 上个月第一天
            first_day_last_month = last_day_last_month.replace(day=1)
            
            # 传递具体的日期范围
            start_date = first_day_last_month.strftime('%Y-%m-%d')
            end_date = last_day_last_month.strftime('%Y-%m-%d')
            days = (last_day_last_month - first_day_last_month).days + 1
            logger.info(f"上个月: {start_date} 到 {end_date}, 共{days}天")
        else:
            days_map = {"最近7天": 7, "最近30天": 30}
            days = days_map.get(time_range_text, 30)
            logger.info(f"时间范围: {time_range_text}, 天数: {days}")
        
        # 启动后台线程
        self.load_thread = DataLoadThread(self.api_client, days, start_date, end_date)
        self.load_thread.data_loaded.connect(self.on_data_loaded)
        self.load_thread.error_occurred.connect(self.on_error)
        self.load_thread.finished.connect(self.on_load_finished)
        self.load_thread.start()
    
    def on_data_loaded(self, data: Dict[str, Any]):
        """数据加载完成"""
        try:
            # 渲染销量趋势图（柱状图）
            if 'sales_trend' in data and data['sales_trend']['data']:
                self.render_bar_chart(
                    self.sales_trend_chart,
                    data['sales_trend']['data'],
                    'date',
                    'total_sales',
                    '销售数量'
                )
            
            # 渲染每日订单量图（柱状图）
            if 'daily_orders' in data and data['daily_orders']['data']:
                self.render_bar_chart(
                    self.daily_orders_chart,
                    data['daily_orders']['data'],
                    'date',
                    'order_count',
                    '订单数量'
                )
            
            # 渲染TOP产品柱状图
            if 'top_products' in data and data['top_products']['data']:
                self.render_bar_chart(
                    self.top_products_chart,
                    data['top_products']['data'],
                    'product_name',
                    'total_sold',
                    '销量'
                )
            
            # 渲染多件订单统计图（柱状图）
            if 'multi_item_orders' in data and data['multi_item_orders']['data']:
                self.render_bar_chart(
                    self.multi_item_orders_chart,
                    data['multi_item_orders']['data'],
                    'label',
                    'order_count',
                    '订单数量'
                )
                
        except Exception as e:
            logger.error(f"渲染图表失败: {e}")
            QMessageBox.warning(self, "错误", f"渲染图表失败: {e}")
    
    def render_line_chart(self, chart: pg.PlotWidget, data: List[Dict], 
                         x_key: str, y_key: str, y_label: str, color='#3498db'):
        """渲染折线图"""
        chart.clear()
        
        if not data:
            chart.setTitle("暂无数据")
            return
        
        # 提取数据
        x_values = list(range(len(data)))
        y_values = [item[y_key] for item in data]
        x_labels = [item[x_key] for item in data]
        
        # 绘制折线
        pen = pg.mkPen(color=color, width=2)
        chart.plot(x_values, y_values, pen=pen, symbol='o', symbolSize=6, symbolBrush=color)
        
        # 设置标签
        chart.setLabel('left', y_label)
        chart.setLabel('bottom', '日期')
        
        # 设置X轴标签（每隔几天显示一个）
        step = max(1, len(x_labels) // 10)
        ticks = [(i, x_labels[i]) for i in range(0, len(x_labels), step)]
        ax = chart.getAxis('bottom')
        ax.setTicks([ticks])
        
        # 设置网格
        chart.showGrid(x=True, y=True, alpha=0.3)
    
    def render_bar_chart(self, chart: pg.PlotWidget, data: List[Dict],
                        x_key: str, y_key: str, y_label: str):
        """渲染柱状图"""
        chart.clear()
        
        if not data:
            chart.setTitle("暂无数据")
            return
        
        # 提取数据
        x_values = list(range(len(data)))
        y_values = [max(0, item[y_key]) for item in data]  # 确保不显示负数
        
        # 智能处理X轴标签（日期格式优化）
        if x_key == 'date':
            # 对于日期，只显示月-日格式（去掉年份）
            x_labels = []
            for item in data:
                date_str = item[x_key]
                # 从 "2025-11-15" 提取 "11-15"
                if len(date_str) >= 10:
                    x_labels.append(date_str[5:10])  # 提取月-日部分
                else:
                    x_labels.append(date_str)
        else:
            # 对于产品名，保持原逻辑
            x_labels = [item[x_key][:10] + '...' if len(item[x_key]) > 10 else item[x_key] for item in data]
        
        # 绘制柱状图
        bar_width = 0.6
        bg = pg.BarGraphItem(x=x_values, height=y_values, width=bar_width, brush='#3498db')
        chart.addItem(bg)
        
        # 在柱子顶部添加数值标签（大字体、加粗）
        max_value = max(y_values) if y_values else 1
        for i, (x, y) in enumerate(zip(x_values, y_values)):
            if y > 0:  # 只显示非零值
                # 使用HTML设置字体样式：14px加粗
                text = pg.TextItem(
                    html=f'<div style="font-size: 14px; font-weight: bold; color: #2c3e50;">{y}</div>',
                    anchor=(0.5, 1.2)
                )
                text.setPos(x, y)
                chart.addItem(text)
        
        # 设置标签
        chart.setLabel('left', y_label)
        if x_key == 'date':
            chart.setLabel('bottom', '日期')
        else:
            chart.setLabel('bottom', '产品')
        
        # 设置X轴标签（根据数量智能显示）
        if len(x_labels) <= 10:
            # 数量少，全部显示
            ticks = [(i, x_labels[i]) for i in range(len(x_labels))]
        else:
            # 数量多，间隔显示（显示约10个刻度）
            step = max(1, len(x_labels) // 10)
            ticks = [(i, x_labels[i]) for i in range(0, len(x_labels), step)]
            # 确保最后一个也显示
            if (len(x_labels) - 1) % step != 0:
                ticks.append((len(x_labels) - 1, x_labels[-1]))
        
        ax = chart.getAxis('bottom')
        ax.setTicks([ticks])
        
        # 设置网格
        chart.showGrid(x=False, y=True, alpha=0.3)
        
        # 设置Y轴从0开始，固定范围（增加30%上边距以容纳标签）
        chart.setYRange(0, max_value * 1.3, padding=0)
        # 设置Y轴最小值为0（不显示负数）
        chart.setLimits(yMin=0)
    
    def on_error(self, error_msg: str):
        """加载错误"""
        QMessageBox.warning(self, "加载失败", f"无法加载数据:\n{error_msg}")
    
    def on_load_finished(self):
        """加载完成"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新数据")
    
    def showEvent(self, event):
        """视图显示时自动加载数据（懒加载）"""
        super().showEvent(event)
        # 只在首次显示时加载
        if not hasattr(self, '_data_loaded'):
            self._data_loaded = True
            self.load_data()
