# 测试文档

## 测试结构

```
tests/
├── __init__.py
├── conftest.py              # pytest 配置和通用 fixtures
├── README.md                # 本文件
├── test_api/                # API 接口测试
│   ├── __init__.py
│   ├── test_products_api.py
│   ├── test_inventory_api.py
│   └── test_sales_api.py
├── test_crud/               # 数据库 CRUD 测试
│   ├── __init__.py
│   ├── test_product_crud.py
│   └── test_inventory_crud.py
└── test_integration/        # 集成测试
    ├── __init__.py
    └── test_complete_flow.py
```

## 运行测试

### 运行所有测试
```bash
pytest tests/
```

### 运行特定模块测试
```bash
pytest tests/test_api/
pytest tests/test_crud/
```

### 运行单个测试文件
```bash
pytest tests/test_api/test_products_api.py
```

### 运行特定测试函数
```bash
pytest tests/test_api/test_products_api.py::test_create_product
```

### 显示详细输出
```bash
pytest tests/ -v
```

### 显示打印输出
```bash
pytest tests/ -s
```

### 生成覆盖率报告
```bash
pytest tests/ --cov=. --cov-report=html
```

## 测试原则

1. **隔离性**: 每个测试应该独立运行，不依赖其他测试的结果
2. **可重复性**: 测试应该可以重复运行，每次结果一致
3. **清晰性**: 测试名称应该清晰描述测试内容
4. **完整性**: 应该覆盖正常流程和异常情况

## 编写测试

### 测试命名规范
- 测试文件: `test_<module_name>.py`
- 测试类: `Test<ClassName>`
- 测试函数: `test_<function_description>`

### 示例测试
```python
def test_create_product(sample_product_data):
    """测试创建产品"""
    # Arrange (准备)
    product_data = sample_product_data
    
    # Act (执行)
    result = create_product(product_data)
    
    # Assert (断言)
    assert result is not None
    assert result['parent_sku'] == 'TEST001'
```

## 注意事项

1. 测试使用独立的测试数据库 `test_database.db`
2. 测试完成后会自动清理测试文件
3. 不要在测试中修改生产数据库
4. 使用 fixtures 共享测试数据
