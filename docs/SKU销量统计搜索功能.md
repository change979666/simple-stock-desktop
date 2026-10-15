# SKU销量统计搜索功能

## 功能概述
在SKU销量统计页面新增智能搜索功能,支持搜索SKU名称并自动选择最佳时间范围显示销量数据。

## 功能特点

### 1. 搜索框位置
- 位于SKU销量统计页面顶部工具栏
- 在标题和时间范围选择器之间
- 包含搜索输入框和清空按钮

### 2. 智能时间范围选择
搜索时自动选择最合适的时间范围:

**优先级逻辑**:
1. **最近30天优先**: 如果近30天有销量,显示近30天数据
2. **今年数据**: 如果近30天无销量但今年有销量,显示今年数据
3. **0销量显示**: 如果今年都无销量但SKU存在,显示0销量结果
4. **未找到**: 如果SKU不存在,提示未找到

### 3. 搜索功能

#### 实时过滤 (输入时)
- 在搜索框输入时实时过滤当前时间范围的数据
- 模糊匹配: 输入"BD11"可匹配"BD11-Black-L"等
- 大小写不敏感

#### 智能搜索 (回车键)
- 按下回车键执行智能搜索
- 自动查询最近30天和今年的数据
- 根据销量情况自动选择最佳时间范围
- 如果没有销量但SKU存在,显示0销量

### 4. 搜索结果提示
在窗口中央状态栏显示搜索结果(3秒后自动消失):

- **近30天有销量**: `🔍 搜索 "BD11" 在最近30天找到 12 个SKU，总销量 533`
- **今年有销量**: `🔍 搜索 "BD11" 在今年找到 12 个SKU，总销量 533`
- **0销量**: `🔍 搜索 "BD11" 找到 12 个SKU，但今年无销量`
- **未找到**: `未找到匹配 "BD11" 的SKU`

## 使用场景

### 场景1: 查询热销SKU的最近销量
**需求**: 查看BD11系列最近的销量情况

**操作**:
1. 在搜索框输入"BD11"
2. 按回车键
3. 系统自动显示最近30天数据(因为有销量)

**结果**:
```
时间范围: 最近30天
🔍 搜索 "BD11" 在最近30天找到 12 个SKU，总销量 533

产品名称  SKU            选项      销售数量  订单数
BD11      BD11-Black-L   Black-L   233      26
BD11      BD11-Pink-M    Pink-M    42       37
BD11      BD11-Blue-L    Blue-L    35       19
...
```

### 场景2: 查询冷门SKU的销量
**需求**: 查看BD300系列的销量(最近没卖)

**操作**:
1. 在搜索框输入"BD300"
2. 按回车键
3. 系统发现近30天无销量,自动切换到"今年"

**结果**:
```
时间范围: 今年
🔍 搜索 "BD300" 在今年找到 5 个SKU，总销量 23

产品名称  SKU              选项        销售数量  订单数
BD300     BD300-Black-S    Black-S     10       5
BD300     BD300-White-M    White-M     8        4
...
```

### 场景3: 查询从未销售的SKU
**需求**: 查看新上架的BD500系列是否有销量

**操作**:
1. 在搜索框输入"BD500"
2. 按回车键
3. 系统发现今年无销量,但SKU存在

**结果**:
```
🔍 搜索 "BD500" 找到 8 个SKU，但今年无销量

产品名称  SKU              选项        销售数量  订单数
BD500     BD500-Black-S    Black-S     0        0
BD500     BD500-Black-M    Black-M     0        0
...
```

### 场景4: 实时过滤当前数据
**需求**: 在当前时间范围内快速筛选SKU

**操作**:
1. 选择时间范围"最近30天"
2. 在搜索框输入"BD11"(不按回车)
3. 系统实时过滤显示匹配的SKU

**特点**:
- 不改变时间范围
- 只过滤当前已加载的数据
- 适合快速查找

## 技术实现

### 前端修改
**文件**: `gui/sku_sales_stats_view.py`

#### 1. 添加搜索UI (第60-113行)
```python
# SKU搜索框
search_label = QLabel("🔎 搜索SKU:")
self.sku_search_input = QLineEdit()
self.sku_search_input.setPlaceholderText("输入SKU搜索...")
self.sku_search_input.textChanged.connect(self.on_search_changed)  # 实时过滤
self.sku_search_input.returnPressed.connect(self.on_search_sku)    # 智能搜索

# 清空搜索按钮
clear_search_btn = QPushButton('✖')
clear_search_btn.clicked.connect(self.clear_search)
```

#### 2. 实时过滤方法 (第610-620行)
```python
def on_search_changed(self, text):
    """搜索框文本变化时的处理(实时过滤)"""
    if not text.strip():
        self.display_stats(self.current_stats)
    else:
        self.filter_current_stats(text.strip().upper())
```

#### 3. 智能搜索方法 (第622-753行)
```python
def on_search_sku(self):
    """按下回车键搜索SKU(智能时间范围)"""
    # 1. 搜索最近30天
    stats_30days = dal.get_sku_sales_stats(start_30, end)
    matching_30 = [s for s in stats_30days if search in s['sku']]
    
    if matching_30:
        # 显示最近30天数据
        self.time_range_combo.setCurrentText("最近30天")
        return
    
    # 2. 搜索今年
    stats_year = dal.get_sku_sales_stats(start_year, end)
    matching_year = [s for s in stats_year if search in s['sku']]
    
    if matching_year:
        # 显示今年数据
        self.time_range_combo.setCurrentText("今年")
        return
    
    # 3. 查询SKU是否存在(0销量)
    variants = db.query(ProductVariant).filter(
        ProductVariant.sku.ilike(f'%{search}%')
    ).all()
    
    if variants:
        # 显示0销量结果
        zero_stats = [构造0销量数据]
        self.display_stats(zero_stats)
```

#### 4. 过滤当前数据 (第755-763行)
```python
def filter_current_stats(self, search_text):
    """过滤当前统计数据"""
    matching_stats = [
        s for s in self.current_stats
        if search_text in s.get('sku', '').upper()
    ]
    self.display_stats(matching_stats)
```

#### 5. 清空搜索 (第765-768行)
```python
def clear_search(self):
    """清空搜索框"""
    self.sku_search_input.clear()
    self.display_stats(self.current_stats)
```

### 数据流程

#### 实时过滤流程
```
用户输入 → textChanged信号 → on_search_changed()
    ↓
过滤当前数据(current_stats)
    ↓
display_stats(过滤结果)
```

#### 智能搜索流程
```
用户按回车 → returnPressed信号 → on_search_sku()
    ↓
查询最近30天数据
    ↓
有销量? ──是→ 显示最近30天 → 结束
    ↓ 否
查询今年数据
    ↓
有销量? ──是→ 显示今年数据 → 结束
    ↓ 否
查询SKU是否存在
    ↓
存在? ──是→ 显示0销量 → 结束
    ↓ 否
提示未找到 → 结束
```

## 数据结构

### 销量统计数据格式
```python
{
    'sku': 'BD11-Black-L',           # SKU名称
    'product_name': 'BD11',          # 产品名称
    'options': 'Black-L',            # 选项(颜色-尺码)
    'quantity': 233,                 # 销售数量
    'amount': 4660.0,                # 销售金额
    'order_count': 26                # 订单数
}
```

### 0销量数据格式
```python
{
    'product_name': 'BD500',
    'sku': 'BD500-Black-S',
    'variant_name': 'Black-S',
    'quantity': 0,                   # 销量为0
    'order_count': 0                 # 订单数为0
}
```

## 测试验证

### 测试脚本
运行 `test_sku_search.py` 测试搜索功能:

```bash
python test_sku_search.py
```

### 测试结果
```
============================================================
测试SKU销量搜索功能
============================================================

🔍 搜索 'BD11' 的销量数据
------------------------------------------------------------

📅 最近30天 (2025-10-04 ~ 2025-11-02):
   ✅ 找到 12 个匹配的SKU
      - BD11-Black-L: 销量 233, 订单 26
      - BD11-Pink-M: 销量 42, 订单 37
      - BD11-Blue-L: 销量 35, 订单 19
      - BD11-Pink-S: 销量 35, 订单 18
      - BD11-Black-M: 销量 31, 订单 27

📅 今年 (2025-01-01 ~ 2025-11-02):
   ✅ 找到 12 个匹配的SKU
      - BD11-Black-L: 销量 233, 订单 26
      ... (同上)

📦 查询数据库中的SKU:
   ✅ 找到 12 个匹配的SKU
      - BD11-Black-S: BD11
      - BD11-Black-M: BD11
      ... (共12个)

🤖 智能搜索逻辑:
   ➡️ 显示最近30天数据 (有 12 个SKU)
   📊 总销量: 533

============================================================
✅ 测试完成!
============================================================
```

## UI设计

### 搜索框样式
- **背景色**: white
- **边框**: 1px solid #ced4da
- **圆角**: 4px
- **焦点边框**: #1890ff (蓝色)
- **最小宽度**: 200px
- **占位符**: "输入SKU搜索..."

### 清空按钮
- **大小**: 28×28px
- **背景色**: #6c757d (灰色)
- **悬停色**: #5a6268 (深灰)
- **图标**: ✖

### 搜索结果提示
- 显示位置: 窗口中央状态栏
- 显示时长: 3秒自动消失
- 提示格式: 
  - `🔍 搜索 "{SKU}" 在{时间范围}找到 X 个SKU，总销量 XXX`
  - `🔍 搜索 "{SKU}" 找到 X 个SKU，但今年无销量`

## 使用技巧

### 1. 快速查找 vs 深度搜索
- **实时过滤**: 输入后不按回车,只在当前时间范围内筛选(快)
- **智能搜索**: 按回车键,自动查找最佳时间范围(全面)

### 2. 搜索关键词选择
- **产品系列**: 输入"BD11"查看整个系列
- **特定变体**: 输入"BD11-Black"查看特定颜色
- **完整SKU**: 输入"BD11-Black-L"查看精确SKU

### 3. 时间范围组合
- 先选择时间范围,再输入搜索 → 实时过滤该时间范围数据
- 直接输入搜索并回车 → 自动选择最佳时间范围

### 4. 清空搜索
- 点击"✖"按钮 → 清空搜索,显示当前时间范围所有数据
- 清空输入框 → 自动恢复显示所有数据

## 注意事项

1. **搜索性能**: 智能搜索需要查询两个时间范围(30天+今年),可能需要几秒钟
2. **大小写**: 搜索自动转换为大写,不区分大小写
3. **模糊匹配**: 部分SKU名称即可匹配
4. **0销量显示**: 如果SKU存在但无销量,会显示0而不是隐藏
5. **时间范围切换**: 智能搜索会自动切换时间范围选择器

## 更新日志

### v2.2.0 (2025-11-02)
- ✨ 新增SKU销量统计搜索功能
- 🔍 支持实时过滤和智能搜索两种模式
- 🤖 智能时间范围选择(30天→今年→0销量)
- 📊 显示搜索结果统计和总销量
- 🎨 优化UI布局,添加清空按钮
- 📝 搜索提示信息3秒后自动消失
