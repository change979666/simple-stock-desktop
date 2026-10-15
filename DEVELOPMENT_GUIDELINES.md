# 开发规范文档

**版本**: 1.0  
**创建日期**: 2025年11月23日  
**最后更新**: 2025年11月23日

---

## 📋 目录

1. [数据访问规范](#数据访问规范)
2. [类型安全规范](#类型安全规范)
3. [代码风格规范](#代码风格规范)
4. [测试规范](#测试规范)
5. [代码审查检查清单](#代码审查检查清单)

---

## 🔌 数据访问规范

### 1. 必须使用 DAL 层访问数据

**原则**: 所有数据访问必须通过 `DataAccessLayer` (DAL) 进行，禁止直接访问数据库或 API。

**正确示例**:
```python
from utils.data_access import DataAccessLayer

dal = DataAccessLayer()
products = dal.get_all_products()  # ✅ 正确
```

**错误示例**:
```python
from database.models import Product
from sqlalchemy import create_engine

engine = create_engine(...)
products = session.query(Product).all()  # ❌ 错误：绕过 DAL 层
```

### 2. DAL 方法统一返回字典

**原则**: 所有 DAL 方法统一返回字典或字典列表，无论在 Local 还是 Client 模式下。

**正确示例**:
```python
def get_all_products(self) -> List[Dict]:
    """获取所有产品（统一返回字典列表）"""
    if app_mode.is_client_mode():
        return client.get_products()  # 返回字典列表
    else:
        products = db.query(Product).all()
        return self._convert_products_to_dict(products)  # 转换为字典
```

### 3. 添加新数据访问方法的步骤

1. **在 DAL 层添加方法** (`utils/data_access.py`)
2. **实现客户端模式分支** (调用 API Client)
3. **实现本地模式分支** (调用 CRUD 方法)
4. **确保返回类型统一** (使用转换方法)
5. **添加类型提示** (返回值和参数)
6. **更新文档字符串**

---

## 🛡️ 类型安全规范

### 1. 使用统一的类型安全工具

**原则**: 使用 `utils.type_safe` 模块中的工具函数，不要自己实现。

**可用工具函数**:
```python
from utils.type_safe import (
    safe_get_attr,       # 安全获取属性/键
    safe_get_nested,     # 嵌套属性访问
    to_dict,             # SQLAlchemy → Dict
    to_dict_list,        # 批量转换
    ensure_dict,         # 确保是字典
    ensure_dict_list,    # 确保是字典列表
    safe_int,            # 安全类型转换
    safe_float,
    safe_str
)
```

**正确示例**:
```python
from utils.type_safe import safe_get_attr

# 安全访问属性/键（支持字典、对象、SQLAlchemy对象）
name = safe_get_attr(product, 'name', 'N/A')
price = safe_get_attr(variant, 'price', 0.0)

# 嵌套访问
customer_name = safe_get_nested(order, 'customer.name', 'Unknown')
```

**错误示例**:
```python
# ❌ 不要自己实现类型检查
if hasattr(obj, 'name'):
    name = obj.name
elif isinstance(obj, dict):
    name = obj.get('name')
else:
    name = 'N/A'

# ✅ 使用统一工具
name = safe_get_attr(obj, 'name', 'N/A')
```

### 2. 添加类型提示

**原则**: 所有函数和方法必须添加类型提示。

**正确示例**:
```python
from typing import List, Dict, Any, Optional

def get_products(
    self,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """获取分页产品列表
    
    Args:
        page: 页码（从1开始）
        page_size: 每页数量
        search: 搜索关键词
        
    Returns:
        包含 items, total, page 等键的字典
    """
    pass
```

### 3. SQLAlchemy 对象转换

**原则**: 在 DAL 本地模式中，必须将 SQLAlchemy 对象转换为字典。

**正确示例**:
```python
from utils.type_safe import to_dict, to_dict_list

# 单个对象转换
product_dict = to_dict(product_obj)

# 列表批量转换
products_list = to_dict_list(product_objects)

# DAL 中的转换方法
def _convert_products_to_dict(self, products: List[Any]) -> List[Dict]:
    """将 SQLAlchemy Product 对象转换为字典"""
    from utils.type_safe import to_dict
    result = []
    for product in products:
        product_dict = to_dict(product)
        # 转换嵌套的 variants
        if hasattr(product, 'variants'):
            product_dict['variants'] = [
                to_dict(v) for v in product.variants
            ]
        result.append(product_dict)
    return result
```

---

## 🎨 代码风格规范

### 1. Python 代码风格

遵循 PEP 8 规范：

- 缩进：4 个空格
- 行长度：最大 79 字符
- 命名：
  - 函数/变量：`snake_case`
  - 类：`PascalCase`
  - 常量：`UPPER_CASE`

### 2. 导入顺序

```python
# 1. 标准库
import os
import sys
from typing import List, Dict

# 2. 第三方库
from PyQt6.QtWidgets import QWidget
import pandas as pd

# 3. 本地模块
from utils.data_access import DataAccessLayer
from utils.type_safe import safe_get_attr
from config.settings import load_settings
```

### 3. 文档字符串

```python
def method_name(param1: str, param2: int) -> Dict:
    """简短的一行描述
    
    详细说明（可选）...
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ExceptionType: 异常说明
    """
    pass
```

---

## 🧪 测试规范

### 1. 测试原则

- **双模式测试**: 所有功能必须在客户端模式下测试
- **数据隔离**: 使用测试数据，不影响生产数据
- **自动化**: 关键功能要有自动化测试

### 2. 测试示例

```python
def test_dal_product_methods():
    """测试产品相关 DAL 方法"""
    dal = DataAccessLayer()
    
    # 测试获取所有产品
    products = dal.get_all_products()
    assert isinstance(products, list)
    if products:
        assert isinstance(products[0], dict)
        assert 'name' in products[0]
        assert 'sku' in products[0]
    
    # 测试获取单个变体
    if products and products[0].get('variants'):
        variant_id = products[0]['variants'][0]['id']
        variant = dal.get_variant_by_id(variant_id)
        assert isinstance(variant, dict)
        assert variant['id'] == variant_id
```

### 3. 测试覆盖要求

- DAL 层：100% 方法覆盖
- CRUD 层：核心方法覆盖
- GUI 层：关键交互覆盖

---

## ✅ 代码审查检查清单

### 添加新功能时检查

- [ ] 数据访问是否通过 DAL 层？
- [ ] DAL 方法是否在两种模式下都能工作？
- [ ] 返回类型是否统一为字典？
- [ ] 是否使用了 `safe_get_attr` 访问属性？
- [ ] 是否添加了类型提示？
- [ ] 是否有完整的文档字符串？
- [ ] 是否遵循 PEP 8 代码风格？
- [ ] 是否处理了异常情况？
- [ ] 是否添加了日志（关键操作）？
- [ ] 是否在客户端模式下测试过？

### 修改现有代码时检查

- [ ] 修改是否向后兼容？
- [ ] 是否影响其他模块？
- [ ] 是否更新了相关文档？
- [ ] 是否更新了测试？
- [ ] 是否测试了边界情况？

### 提交代码前检查

- [ ] 所有测试是否通过？
- [ ] 是否有 lint 错误？
- [ ] 是否有未使用的导入？
- [ ] 是否有调试代码（print）？
- [ ] commit 信息是否清晰？

---

## 🚫 常见错误

### 1. 绕过 DAL 层直接访问数据库

```python
# ❌ 错误
from database.models import Product
products = db.query(Product).all()

# ✅ 正确
from utils.data_access import DataAccessLayer
dal = DataAccessLayer()
products = dal.get_all_products()
```

### 2. 假设返回类型

```python
# ❌ 错误（假设是 SQLAlchemy 对象）
name = product.name

# ✅ 正确（安全访问）
from utils.type_safe import safe_get_attr
name = safe_get_attr(product, 'name', 'N/A')
```

### 3. 不处理 None 值

```python
# ❌ 错误
price = float(variant['price']) * 1.1

# ✅ 正确
from utils.type_safe import safe_float
price = safe_float(variant.get('price'), 0.0) * 1.1
```

### 4. 硬编码字符串

```python
# ❌ 错误
if status == "已发货":
    ...

# ✅ 正确
from database.inventory import ShipmentStatus
if status == ShipmentStatus.SHIPPED:
    ...
```

---

## 📚 相关文档

- [数据访问层文档](./utils/data_access.py)
- [类型安全工具文档](./utils/type_safe.py)
- [API 客户端文档](./client/api_client.py)
- [TODO 优化清单](./TODO_数据类型安全优化.md)

---

## 🔄 文档更新

本文档会随着项目发展不断更新。如有建议或发现问题，请及时反馈。

**维护者**: 开发团队  
**审核周期**: 每月

---

**最后更新**: 2025年11月23日
