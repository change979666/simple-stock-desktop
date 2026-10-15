"""
产品管理功能测试工具
测试产品的添加、修改、删除、导入等核心功能
"""
import sys
from datetime import datetime

# 首先设置为客户端模式
from utils.app_mode import app_mode
app_mode.set_client_mode(True)

# 配置API客户端
from client.api_client import api_client
api_client.configure('127.0.0.1', 8001)

from utils.data_access import dal
from utils.operator import get_operator_info

def test_get_products():
    """测试获取产品列表"""
    print("\n=== 测试：获取产品列表 ===")
    try:
        products = dal.get_all_products()
        print(f"✅ 成功获取 {len(products)} 个产品")
        if products:
            # 显示第一个产品的信息
            product = products[0]
            if isinstance(product, dict):
                print(f"   示例产品: {product.get('name')} (ID: {product.get('id')})")
                print(f"   SKU数量: {len(product.get('variants', []))}")
            else:
                print(f"   示例产品: {product.name} (ID: {product.id})")
                print(f"   SKU数量: {len(product.variants)}")
        return True
    except Exception as e:
        print(f"❌ 获取产品列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_add_product():
    """测试添加产品（与GUI格式完全一致）"""
    print("\n=== 测试：添加产品 ===")
    try:
        operator_info = get_operator_info()
        
        # 创建测试产品数据 - 与GUI格式一致
        product_data = {
            'name': f'测试产品_{datetime.now().strftime("%H%M%S")}',
            'category_id': None,  # GUI使用category_id，不是category字符串
            'option1_name': '颜色',  # GUI使用option1_name
            'option2_name': '尺寸',  # GUI使用option2_name
            'operator_info': operator_info,
            'variants': [
                {
                    'sku': f'TEST-SKU-{datetime.now().strftime("%H%M%S")}-01',
                    'option1_value': '红色',  # GUI使用option_value
                    'option2_value': 'M',
                    'initial_stock': 100,
                    'cost_price': 50.00
                },
                {
                    'sku': f'TEST-SKU-{datetime.now().strftime("%H%M%S")}-02',
                    'option1_value': '蓝色',
                    'option2_value': 'L',
                    'initial_stock': 50,
                    'cost_price': 55.00
                }
            ]
        }
        
        result = dal.create_product(product_data)
        print(f"✅ 成功添加产品")
        if isinstance(result, dict):
            print(f"   产品名称: {result.get('name')}")
            print(f"   产品ID: {result.get('id')}")
        else:
            print(f"   产品名称: {result.name}")
            print(f"   产品ID: {result.id}")
        return True
    except Exception as e:
        print(f"❌ 添加产品失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_update_product():
    """测试修改产品"""
    print("\n=== 测试：修改产品 ===")
    try:
        # 先获取一个产品
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品可以修改，跳过测试")
            return True
        
        product = products[0]
        if isinstance(product, dict):
            product_id = product.get('id')
            old_name = product.get('name')
        else:
            product_id = product.id
            old_name = product.name
        
        operator_info = get_operator_info()
        
        # 修改产品名称
        update_data = {
            'name': f'{old_name}_已修改_{datetime.now().strftime("%H%M%S")}',
            'operator_info': operator_info
        }
        
        result = dal.update_product(product_id, update_data)
        print(f"✅ 成功修改产品")
        if isinstance(result, dict):
            print(f"   旧名称: {old_name}")
            print(f"   新名称: {result.get('name')}")
        else:
            print(f"   旧名称: {old_name}")
            print(f"   新名称: {result.name}")
        return True
    except Exception as e:
        print(f"❌ 修改产品失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_delete_product():
    """测试删除产品"""
    print("\n=== 测试：删除产品 ===")
    try:
        # 先添加一个测试产品用于删除
        operator_info = get_operator_info()
        # 创建测试产品用于删除
        product_data = {
            'name': f'待删除产品_{datetime.now().strftime("%H%M%S")}',
            'category_id': None,
            'option1_name': '颜色',
            'option2_name': '尺寸',
            'operator_info': operator_info,
            'variants': [
                {
                    'sku': f'DEL-SKU-{datetime.now().strftime("%H%M%S")}',
                    'option1_value': '黑色',
                    'option2_value': 'S',
                    'initial_stock': 10,
                    'cost_price': 30.00
                }
            ]
        }
        
        product = dal.create_product(product_data)
        if isinstance(product, dict):
            product_id = product.get('id')
            product_name = product.get('name')
        else:
            product_id = product.id
            product_name = product.name
        
        print(f"   已创建测试产品: {product_name} (ID: {product_id})")
        
        # 删除产品
        dal.delete_product(product_id, operator_info)
        print(f"✅ 成功删除产品 (ID: {product_id})")
        return True
    except Exception as e:
        print(f"❌ 删除产品失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_products():
    """测试批量导入产品"""
    print("\n=== 测试：批量导入产品 ===")
    try:
        import pandas as pd
        
        operator_info = get_operator_info()
        
        # 创建测试数据
        timestamp = datetime.now().strftime("%H%M%S")
        test_data = [
            {
                'product_name': f'批量导入产品A_{timestamp}',
                'category': '测试分类',
                'sku': f'IMPORT-A-{timestamp}',
                'color': '红色',
                'size': 'M',
                'stock': 100,
                'cost_price': 40.0,
                'selling_price': 70.0
            },
            {
                'product_name': f'批量导入产品B_{timestamp}',
                'category': '测试分类',
                'sku': f'IMPORT-B-{timestamp}',
                'color': '蓝色',
                'size': 'L',
                'stock': 80,
                'cost_price': 45.0,
                'selling_price': 75.0
            }
        ]
        
        df = pd.DataFrame(test_data)
        
        # 导入产品
        result = dal.import_products(df, operator_info)
        
        if isinstance(result, dict):
            print(f"✅ 批量导入完成")
            print(f"   成功: {result.get('success', 0)} 个")
            print(f"   失败: {result.get('failed', 0)} 个")
            if result.get('errors'):
                print(f"   错误信息: {result.get('errors')}")
        else:
            print(f"✅ 批量导入完成")
        return True
    except Exception as e:
        print(f"❌ 批量导入产品失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_export_products():
    """测试导出产品"""
    print("\n=== 测试：导出产品 ===")
    try:
        products = dal.export_products()
        print(f"✅ 成功导出产品数据")
        
        if isinstance(products, list):
            print(f"   导出数量: {len(products)} 个产品")
            if products:
                product = products[0]
                if isinstance(product, dict):
                    print(f"   示例产品: {product.get('product_name')}")
                    print(f"   包含字段: {list(product.keys())[:5]}...")
        return True
    except Exception as e:
        print(f"❌ 导出产品失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("产品管理功能测试")
    print("=" * 60)
    
    tests = [
        ("获取产品列表", test_get_products),
        ("添加产品", test_add_product),
        ("修改产品", test_update_product),
        ("删除产品", test_delete_product),
        ("批量导入产品", test_import_products),
        ("导出产品", test_export_products),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    return passed == total

if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
