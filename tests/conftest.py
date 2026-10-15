"""
pytest 配置文件
定义测试夹具 (fixtures) 和通用设置
"""
import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def test_db_path():
    """测试数据库路径"""
    return str(project_root / "test_database.db")


@pytest.fixture(scope="session")
def test_config_path():
    """测试配置文件路径"""
    return str(project_root / "test_config.ini")


@pytest.fixture(autouse=True)
def cleanup_test_files(test_db_path, test_config_path):
    """测试前后自动清理测试文件"""
    yield
    # 测试完成后清理
    for path in [test_db_path, test_config_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@pytest.fixture
def sample_product_data():
    """示例产品数据"""
    return {
        "name": "测试产品",
        "parent_sku": "TEST001",
        "description": "测试产品描述",
        "category_id": 1
    }


@pytest.fixture
def sample_variant_data():
    """示例变体数据"""
    return {
        "sku": "TEST001-RED-L",
        "option_name": "红色-大码",
        "cost_price": 99.99
    }


@pytest.fixture
def operator_info():
    """测试操作员信息"""
    return {
        "name": "测试员",
        "ip": "127.0.0.1",
        "display": "测试员 (127.0.0.1)"
    }
