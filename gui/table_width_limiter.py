"""
表格列宽度限制器
防止列拖拽超出窗口边界
"""
from PyQt6.QtWidgets import QHeaderView


def limit_column_width(table_widget, index: int, old_size: int, new_size: int):
    """
    限制表格列宽度不超出可视区域
    
    Args:
        table_widget: QTableWidget 或 QTreeWidget 实例
        index: 被调整的列索引
        old_size: 旧的列宽
        new_size: 新的列宽
        
    Returns:
        实际应用的列宽（可能被限制）
    """
    try:
        # 获取表格可视区域宽度
        viewport_width = table_widget.viewport().width()
        
        # 计算当前所有列的总宽度
        column_count = table_widget.columnCount()
        total_width = sum(
            table_widget.columnWidth(i) for i in range(column_count)
        )
        
        # 如果总宽度超过可视区域，限制当前调整的列
        if total_width > viewport_width:
            # 计算超出的宽度
            overflow = total_width - viewport_width
            # 将调整的列缩小相应宽度
            max_width = new_size - overflow
            if max_width < 50:  # 最小列宽50px
                max_width = 50
            
            # 暂时阻止信号避免递归
            header = table_widget.header() if hasattr(table_widget, 'header') else table_widget.horizontalHeader()
            header.blockSignals(True)
            table_widget.setColumnWidth(index, max_width)
            header.blockSignals(False)
            
            return max_width
        
        return new_size
        
    except Exception as e:
        print(f"限制列宽失败: {e}")
        return new_size


def setup_column_width_limiter(table_widget, on_resize_callback=None):
    """
    为表格设置列宽度限制器
    
    Args:
        table_widget: QTableWidget 或 QTreeWidget 实例
        on_resize_callback: 可选的回调函数，在列宽改变后调用
                           签名: callback(index, old_size, new_size)
    """
    def handle_resize(index: int, old_size: int, new_size: int):
        # 先限制宽度
        actual_size = limit_column_width(table_widget, index, old_size, new_size)
        
        # 如果有回调函数，执行它（例如保存配置）
        if on_resize_callback:
            on_resize_callback(index, old_size, actual_size)
    
    # 连接信号
    header = table_widget.header() if hasattr(table_widget, 'header') else table_widget.horizontalHeader()
    header.sectionResized.connect(handle_resize)
