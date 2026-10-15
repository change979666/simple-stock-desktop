# 发货管理SKU搜索功能

## 功能概述
在发货管理界面新增SKU搜索功能,用户可以通过输入SKU名称快速查找该SKU的所有发货记录(包括待发货、运输中、已上架、已取消等所有状态)。

## 功能特点

### 1. 搜索框位置
- 位于发货管理界面工具栏右侧
- 在"状态筛选"后面
- 包含搜索输入框和清空按钮

### 2. 搜索功能
- **实时搜索**: 输入SKU名称时实时过滤显示结果
- **模糊匹配**: 支持部分SKU名称匹配(例如输入"BD99"可匹配"BD99-Black"、"BD99-Beige"等)
- **大小写不敏感**: 输入"bd99"或"BD99"效果相同
- **全状态显示**: 搜索时显示该SKU的所有发货记录,不受状态筛选限制

### 3. 搜索结果
- 显示包含搜索SKU的所有发货批次
- 每个批次展开显示具体SKU明细
- 显示搜索结果统计:"🔍 搜索 'XXX' 找到 X 笔发货记录"

### 4. 状态筛选组合
搜索功能可以与状态筛选组合使用:

| 状态筛选 | 搜索框 | 显示结果 |
|---------|--------|---------|
| 🔍 全部状态 | 空 | 待发货 + 运输中 (默认隐藏已上架和已取消) |
| 🔍 全部状态 | BD99 | 包含BD99的所有状态记录 |
| ⏳ 待发货 | 空 | 所有待发货记录 |
| ⏳ 待发货 | BD99 | 包含BD99的待发货记录 |
| 🚚 运输中 | BD99 | 包含BD99的运输中记录 |
| ✅ 已上架 | BD99 | 包含BD99的已上架记录 |
| ❌ 已取消 | BD99 | 包含BD99的已取消记录 |

## 使用场景

### 场景1: 查看某SKU的发货历史
**需求**: 查看BD99这个产品过去所有的发货记录

**操作步骤**:
1. 打开"发货管理"页面
2. 在搜索框输入"BD99"
3. 系统自动显示所有包含BD99的发货记录
4. 可以看到该SKU在不同批次、不同状态的发货情况

**结果示例**:
```
🔍 搜索 "BD99" 找到 3 笔发货记录

📦 批次: BD251017 (🚚 运输中)
   └─ BD99-Black × 150
   └─ BD99-Beige × 150
   └─ BD99-Pink × 150

📦 批次: BD250920 (✅ 已上架)
   └─ BD99-Black × 200
   └─ BD99-Coffee × 100

📦 批次: BD250815 (❌ 已取消)
   └─ BD99-Pink × 80
```

### 场景2: 查看某SKU运输中的发货
**需求**: 查看BD99目前有哪些批次在运输途中

**操作步骤**:
1. 状态筛选选择"🚚 运输中"
2. 搜索框输入"BD99"
3. 只显示BD99运输中的记录

### 场景3: 查看某SKU历史已上架记录
**需求**: 查看BD99过去上架过几次,每次数量多少

**操作步骤**:
1. 状态筛选选择"✅ 已上架"
2. 搜索框输入"BD99"
3. 显示BD99所有历史上架记录

## 技术实现

### 前端修改
**文件**: `gui/shipment_view.py`

1. **添加搜索UI组件** (第128-178行)
```python
# SKU搜索区域
search_frame = QFrame()
search_layout = QHBoxLayout(search_frame)

search_label = QLabel('🔎 搜索SKU:')
self.sku_search_input = QLineEdit()
self.sku_search_input.setPlaceholderText('输入SKU名称搜索...')
self.sku_search_input.textChanged.connect(self.filter_shipments)

clear_search_btn = QPushButton('✖')
clear_search_btn.clicked.connect(lambda: self.sku_search_input.clear())
```

2. **修改加载逻辑** (第336-450行)
```python
def load_shipments(self):
    sku_search = self.sku_search_input.text().strip().upper()
    
    for shipment in shipments:
        # SKU搜索过滤
        if sku_search:
            shipment_items = get_attr(shipment, 'shipment_items', [])
            has_matching_sku = False
            for item in shipment_items:
                variant = get_attr(item, 'variant')
                if variant:
                    item_sku = get_attr(variant, 'sku', '').upper()
                    if sku_search in item_sku:
                        has_matching_sku = True
                        break
            
            if not has_matching_sku:
                continue
```

3. **搜索结果统计** (第540-563行)
```python
displayed_count = self.tree.topLevelItemCount()

if sku_search:
    main_window.center_message_label.setText(
        f'🔍 搜索 "{sku_search}" 找到 {displayed_count} 笔发货记录'
    )
```

### 数据流程
```
用户输入SKU
    ↓
textChanged信号
    ↓
filter_shipments()
    ↓
load_shipments()
    ↓
获取所有发货记录(缓存/API)
    ↓
遍历每条发货记录
    ↓
检查shipment_items中是否有匹配的SKU
    ↓
过滤并显示匹配结果
    ↓
显示统计信息
```

### 搜索逻辑
```python
# 模糊匹配逻辑
sku_search = "BD99"  # 用户输入
item_sku = "BD99-Black"  # 数据库中的SKU

if sku_search.upper() in item_sku.upper():
    # 匹配成功,显示此发货记录
    pass
```

## 测试验证

### 测试脚本
运行 `test_shipment_search.py` 可以测试搜索功能:

```bash
python test_shipment_search.py
```

### 测试结果示例
```
============================================================
测试发货管理SKU搜索功能
============================================================

📦 数据库中共有 1 笔发货记录

📊 按状态统计:
   🚚 运输中: 1 笔

📋 涉及的SKU数量: 57
   前10个SKU: ['BD100-Black-Shuang', 'BD100-Grey-Shuang', ...]

🔍 搜索包含 'BD99' 的发货记录:
   找到 1 笔匹配的发货记录

   📦 批次: BD251017
      状态: 🚚 运输中
      创建时间: 2025-10-19 16:30
      包含SKU:
         - BD99-Black: BD99 × 150
         - BD99-Beige: BD99 × 150
         - BD99-Pink: BD99 × 150
         - BD99-Coffee: BD99 × 150

============================================================
✅ 测试完成!
============================================================
```

## UI设计

### 搜索框样式
- **背景色**: #f8f9fa (浅灰)
- **边框**: 1px solid #dee2e6
- **圆角**: 6px
- **焦点边框**: #1890ff (蓝色)
- **最小宽度**: 200px
- **占位符文本**: "输入SKU名称搜索..."

### 清空按钮
- **大小**: 28×28px
- **背景色**: #6c757d (灰色)
- **悬停色**: #5a6268 (深灰)
- **图标**: ✖
- **功能**: 一键清空搜索框内容

### 搜索结果提示
显示在窗口中央状态栏,3秒后自动消失:
- 有搜索: `🔍 搜索 "BD99" 找到 3 笔发货记录`
- 有筛选: `✅ 已加载 5 笔 🚚 运输中 记录`
- 默认刷新: `✅ 发货记录刷新成功，已加载 10 笔记录`

## 注意事项

1. **搜索与缓存**: 搜索使用缓存数据,如需最新数据请先点击"🔄 刷新"按钮
2. **大小写**: 搜索自动转换为大写进行匹配,不区分大小写
3. **部分匹配**: 输入部分SKU即可匹配(如"BD"可匹配所有BD开头的SKU)
4. **组合筛选**: 搜索框可以与状态筛选组合使用,实现精确过滤
5. **清空搜索**: 点击"✖"按钮或手动清空搜索框即可恢复正常显示

## 更新日志

### v2.2.0 (2025-11-02)
- ✨ 新增发货管理SKU搜索功能
- 🔍 支持实时搜索和模糊匹配
- 📊 显示搜索结果统计
- 🎨 优化UI布局,添加清空按钮
- 📝 搜索时显示所有状态记录(不受默认筛选限制)
