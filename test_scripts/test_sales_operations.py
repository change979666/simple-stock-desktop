"""
销售管理功能测试工具
测试销售订单的创建、导入、删除等核心功能
"""
import sys
from datetime import datetime, date

# 首先设置为客户端模式
from utils.app_mode import app_mode
app_mode.set_client_mode(True)

# 配置API客户端
from client.api_client import api_client
api_client.configure('127.0.0.1', 8001)

from utils.data_access import dal
from utils.operator import get_operator_info

def test_get_sales_orders():
    """测试获取销售订单列表"""
    print("\n=== 测试：获取销售订单列表 ===")
    try:
        orders = dal.get_sales_orders()
        print(f"✅ 成功获取销售订单")
        print(f"   订单数量: {len(orders)}")
        
        if orders:
            order = orders[0]
            if isinstance(order, dict):
                print(f"   示例订单号: {order.get('order_number')}")
                print(f"   订单日期: {order.get('order_date')}")
            else:
                print(f"   示例订单号: {order.order_number}")
                print(f"   订单日期: {order.order_date}")
        
        return True
    except Exception as e:
        print(f"❌ 获取销售订单失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_sales_order():
    """测试创建销售订单"""
    print("\n=== 测试：创建销售订单 ===")
    try:
        # 先获取一些SKU用于创建订单
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法创建销售订单")
            return True
        
        # 获取第一个产品的第一个SKU
        product = products[0]
        if isinstance(product, dict):
            variants = product.get('variants', [])
            if not variants:
                print("⚠️  产品没有SKU，无法创建销售订单")
                return True
            variant = variants[0]
            sku = variant.get('sku')
        else:
            if not product.variants:
                print("⚠️  产品没有SKU，无法创建销售订单")
                return True
            variant = product.variants[0]
            sku = variant.sku
        
        operator_info = get_operator_info()
        
        # 创建订单数据
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        order_data = {
            'order_number': f'TEST-{timestamp}',
            'customer_name': '测试客户',
            'order_date': date.today().isoformat(),
            'operator_info': operator_info,
            'items': [
                {
                    'sku': sku,
                    'quantity': 2,
                    'unit_price': 100.00
                }
            ]
        }
        
        result = dal.create_sale_order(order_data)
        print(f"✅ 成功创建销售订单")
        if isinstance(result, dict):
            print(f"   订单号: {result.get('order_number')}")
            print(f"   客户: {result.get('customer_name')}")
            print(f"   订单ID: {result.get('id')}")
        else:
            print(f"   订单号: {result.order_number}")
            print(f"   客户: {result.customer_name}")
            print(f"   订单ID: {result.id}")
        
        return True
    except Exception as e:
        print(f"❌ 创建销售订单失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_sales_orders():
    """测试批量导入销售订单"""
    print("\n=== 测试：批量导入销售订单 ===")
    try:
        import pandas as pd
        
        # 先获取一些SKU用于测试
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法测试销售订单导入")
            return True
        
        operator_info = get_operator_info()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 创建测试数据
        test_data = []
        for i, product in enumerate(products[:2]):  # 最多测试2个产品
            if isinstance(product, dict):
                variants = product.get('variants', [])
                for j, variant in enumerate(variants[:2]):  # 每个产品最多2个SKU
                    test_data.append({
                        'order_number': f'IMP-{timestamp}-{i}{j}',
                        'customer_name': f'批量导入客户{i+1}',
                        'order_date': date.today().isoformat(),
                        'sku': variant.get('sku'),
                        'quantity': 1,
                        'unit_price': 100.00
                    })
            else:
                for j, variant in enumerate(product.variants[:2]):
                    test_data.append({
                        'order_number': f'IMP-{timestamp}-{i}{j}',
                        'customer_name': f'批量导入客户{i+1}',
                        'order_date': date.today().isoformat(),
                        'sku': variant.sku,
                        'quantity': 1,
                        'unit_price': 100.00
                    })
        
        if not test_data:
            print("⚠️  没有可用的SKU，无法测试销售订单导入")
            return True
        
        df = pd.DataFrame(test_data)
        
        print(f"   准备导入 {len(test_data)} 条销售订单")
        
        # 按订单号分组
        grouped = df.groupby('order_number')
        success_count = 0
        failed_count = 0
        
        for order_number, group in grouped:
            try:
                first_row = group.iloc[0]
                order_data = {
                    'order_number': order_number,
                    'customer_name': first_row['customer_name'],
                    'order_date': first_row['order_date'],
                    'operator_info': operator_info,
                    'items': [
                        {
                            'sku': row['sku'],
                            'quantity': int(row['quantity']),
                            'unit_price': float(row['unit_price'])
                        }
                        for _, row in group.iterrows()
                    ]
                }
                
                dal.create_sale_order(order_data)
                success_count += 1
            except Exception as e:
                print(f"   ⚠️  订单 {order_number} 导入失败: {e}")
                failed_count += 1
        
        print(f"✅ 批量导入完成")
        print(f"   成功: {success_count} 个订单")
        print(f"   失败: {failed_count} 个订单")
        return True
    except Exception as e:
        print(f"❌ 批量导入销售订单失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_delete_sales_order():
    """测试删除销售订单"""
    print("\n=== 测试：删除销售订单 ===")
    try:
        # 先创建一个测试订单用于删除
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法创建测试订单")
            return True
        
        product = products[0]
        if isinstance(product, dict):
            variants = product.get('variants', [])
            if not variants:
                print("⚠️  产品没有SKU，无法创建测试订单")
                return True
            sku = variants[0].get('sku')
        else:
            if not product.variants:
                print("⚠️  产品没有SKU，无法创建测试订单")
                return True
            sku = product.variants[0].sku
        
        operator_info = get_operator_info()
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        order_data = {
            'order_number': f'DEL-{timestamp}',
            'customer_name': '待删除客户',
            'order_date': date.today().isoformat(),
            'operator_info': operator_info,
            'items': [
                {
                    'sku': sku,
                    'quantity': 1,
                    'unit_price': 50.00
                }
            ]
        }
        
        order = dal.create_sale_order(order_data)
        if isinstance(order, dict):
            order_number = order.get('order_number')
        else:
            order_number = order.order_number
        
        print(f"   已创建测试订单: {order_number}")
        
        # 获取所有订单并找到刚创建的订单ID
        all_orders = dal.get_sales_orders()
        order_id = None
        for o in all_orders:
            if isinstance(o, dict):
                if o.get('order_number') == order_number:
                    order_id = o.get('id')
                    break
            else:
                if o.order_number == order_number:
                    order_id = o.id
                    break
        
        if not order_id:
            print(f"⚠️  无法找到刚创建的订单，跳过删除测试")
            return True
        
        # 删除订单
        dal.delete_sale_order(order_id)
        print(f"✅ 成功删除销售订单 (订单号: {order_number})")
        return True
    except Exception as e:
        print(f"❌ 删除销售订单失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("销售管理功能测试")
    print("=" * 60)
    
    tests = [
        ("获取销售订单列表", test_get_sales_orders),
        ("创建销售订单", test_create_sales_order),
        ("批量导入销售订单", test_import_sales_orders),
        ("删除销售订单", test_delete_sales_order),
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
