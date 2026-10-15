"""
自然排序树形项 - 支持SKU等混合字母数字的智能排序
"""

from PyQt6.QtWidgets import QTreeWidgetItem
import re


class NaturalSortTreeWidgetItem(QTreeWidgetItem):
    """
    支持自然排序的树形项
    
    自然排序规则：
    - BD1, BD2, BD10, BD100（而不是 BD1, BD10, BD100, BD2）
    - 分离文本和数字部分进行比较
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sort_keys = {}  # 缓存排序键
    
    @staticmethod
    def natural_sort_key(text):
        """
        生成自然排序键
        
        Examples:
            BD10 -> ['BD', 10]
            BD100 -> ['BD', 100]
            BD2 -> ['BD', 2]
            排序后: BD2 < BD10 < BD100
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 分离文本和数字
        parts = []
        for part in re.split(r'(\d+)', text):
            if part.isdigit():
                parts.append(int(part))  # 数字部分转为整数
            else:
                parts.append(part.lower())  # 文本部分转为小写
        
        return parts
    
    def __lt__(self, other):
        """
        重载小于运算符，实现自然排序
        
        排序优先级：
        1. 尝试按当前排序列进行比较
        2. 如果失败，回退到默认比较
        """
        if not isinstance(other, QTreeWidgetItem):
            return super().__lt__(other)
        
        # 获取当前排序列
        tree = self.treeWidget()
        if tree is None:
            return super().__lt__(other)
        
        sort_column = tree.sortColumn()
        
        # 获取两个项的文本
        self_text = self.text(sort_column)
        other_text = other.text(sort_column)
        
        # 生成排序键并缓存
        if sort_column not in self.sort_keys:
            self.sort_keys[sort_column] = self.natural_sort_key(self_text)
        
        if not hasattr(other, 'sort_keys'):
            other.sort_keys = {}
        if sort_column not in other.sort_keys:
            other.sort_keys[sort_column] = self.natural_sort_key(other_text)
        
        # 比较排序键
        try:
            return self.sort_keys[sort_column] < other.sort_keys[sort_column]
        except Exception:
            # 如果比较失败，回退到默认比较
            return super().__lt__(other)


class NumericSortTreeWidgetItem(QTreeWidgetItem):
    """
    支持数值排序的树形项（用于纯数字列）
    
    适用场景：
    - 库存数量列
    - 销量列
    - 金额列
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.numeric_values = {}  # 缓存数值
    
    def set_numeric_value(self, column, value):
        """设置指定列的数值"""
        self.numeric_values[column] = value
    
    def __lt__(self, other):
        """重载小于运算符，实现数值排序"""
        if not isinstance(other, QTreeWidgetItem):
            return super().__lt__(other)
        
        tree = self.treeWidget()
        if tree is None:
            return super().__lt__(other)
        
        sort_column = tree.sortColumn()
        
        # 如果有缓存的数值，使用数值比较
        if (sort_column in self.numeric_values and
                hasattr(other, 'numeric_values') and
                sort_column in other.numeric_values):
            try:
                return (self.numeric_values[sort_column] <
                        other.numeric_values[sort_column])
            except Exception:
                pass
        
        # 否则尝试解析文本为数字
        try:
            self_text = self.text(sort_column).replace(',', '').replace('¥', '')
            other_text = other.text(sort_column).replace(',', '').replace('¥', '')
            
            self_num = float(self_text) if self_text else 0
            other_num = float(other_text) if other_text else 0
            
            return self_num < other_num
        except (ValueError, AttributeError):
            # 如果无法转换为数字，使用默认比较
            return super().__lt__(other)


class HybridSortTreeWidgetItem(QTreeWidgetItem):
    """
    混合排序树形项 - 结合自然排序和数值排序
    
    智能判断每列的排序方式：
    - SKU列：自然排序（BD2 < BD10 < BD100）
    - 数值列：数值排序（1 < 2 < 10 < 100）
    - 文本列：默认排序
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sort_keys = {}
        self.numeric_values = {}
        self.column_types = {}  # 记录列类型
    
    def set_column_type(self, column, column_type):
        """
        设置列类型
        :param column: 列索引
        :param column_type: 'natural'（自然排序）, 'numeric'（数值排序）, 'text'（文本排序）
        """
        self.column_types[column] = column_type
    
    def set_numeric_value(self, column, value):
        """设置数值列的值"""
        self.numeric_values[column] = value
        self.column_types[column] = 'numeric'
    
    @staticmethod
    def natural_sort_key(text):
        """生成自然排序键"""
        if not isinstance(text, str):
            text = str(text)
        
        parts = []
        for part in re.split(r'(\d+)', text):
            if part.isdigit():
                parts.append(int(part))
            else:
                parts.append(part.lower())
        
        return parts
    
    def __lt__(self, other):
        """智能排序"""
        if not isinstance(other, QTreeWidgetItem):
            return super().__lt__(other)
        
        tree = self.treeWidget()
        if tree is None:
            return super().__lt__(other)
        
        sort_column = tree.sortColumn()
        
        # 获取列类型
        column_type = self.column_types.get(sort_column, 'auto')
        
        # 数值排序
        if column_type == 'numeric':
            if (sort_column in self.numeric_values and
                    hasattr(other, 'numeric_values') and
                    sort_column in other.numeric_values):
                try:
                    return (self.numeric_values[sort_column] <
                            other.numeric_values[sort_column])
                except Exception:
                    pass
        
        # 自然排序
        elif column_type == 'natural':
            self_text = self.text(sort_column)
            other_text = other.text(sort_column)
            
            if sort_column not in self.sort_keys:
                self.sort_keys[sort_column] = self.natural_sort_key(self_text)
            
            if not hasattr(other, 'sort_keys'):
                other.sort_keys = {}
            if sort_column not in other.sort_keys:
                other.sort_keys[sort_column] = self.natural_sort_key(other_text)
            
            try:
                return self.sort_keys[sort_column] < other.sort_keys[sort_column]
            except Exception:
                pass
        
        # 自动判断（根据第一列内容判断）
        elif column_type == 'auto' and sort_column == 0:
            # 第一列默认使用自然排序（通常是SKU）
            self_text = self.text(sort_column)
            other_text = other.text(sort_column)
            
            try:
                self_key = self.natural_sort_key(self_text)
                other_key = self.natural_sort_key(other_text)
                return self_key < other_key
            except Exception:
                pass
        
        # 默认比较
        return super().__lt__(other)
