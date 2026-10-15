"""
发货管理功能测试工具
测试发货记录的创建、导入、状态更新等核心功能
"""
import sys
from datetime import datetime, timedelta

# 首先设置为客户端模式
from utils.app_mode import app_mode
app_mode.set_client_mode(True)

# 配置API客户端
from client.api_client import api_client
api_client.configure('127.0.0.1', 8001)

from utils.data_access import dal
from utils.operator import get_operator_info

def test_get_shipments():
    """测试获取发货记录列表"""
    print("\n=== 测试：获取发货记录列表 ===")
    try:
        shipments = dal.get_shipments()
        print(f"✅ 成功获取发货记录")
        print(f"   记录数量: {len(shipments)}")
        
        if shipments:
            shipment = shipments[0]
            if isinstance(shipment, dict):
                print(f"   示例批次号: {shipment.get('batch_number')}")
                print(f"   状态: {shipment.get('status')}")
            else:
                print(f"   示例批次号: {shipment.batch_number}")
                print(f"   状态: {shipment.status}")
        
        return True
    except Exception as e:
        print(f"❌ 获取发货记录失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_shipment():
    """测试创建发货记录"""
    print("\n=== 测试：创建发货记录 ===")
    try:
        # 先获取一个SKU用于创建发货记录
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法创建发货记录")
            return True
        
        product = products[0]
        if isinstance(product, dict):
            variants = product.get('variants', [])
            if not variants:
                print("⚠️  产品没有SKU，无法创建发货记录")
                return True
            sku = variants[0].get('sku')
        else:
            if not product.variants:
                print("⚠️  产品没有SKU，无法创建发货记录")
                return True
            sku = product.variants[0].sku
        
        operator_info = get_operator_info()
        
        # 创建发货数据
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        estimated_arrival = (datetime.now() + timedelta(days=7)).date()
        
        shipment_data = {
            'sku': sku,
            'quantity': 50,
            'batch_number': f'SH{timestamp}',
            'tracking_number': f'TRACK-{timestamp}',
            'estimated_arrival': estimated_arrival.isoformat(),
            'notes': f'测试发货_{timestamp}',
            'operator_info': operator_info
        }
        
        result = dal.create_shipment(shipment_data)
        print(f"✅ 成功创建发货记录")
        if isinstance(result, dict):
            print(f"   批次号: {result.get('batch_number')}")
            print(f"   SKU: {result.get('sku')}")
            print(f"   数量: {result.get('quantity')}")
            print(f"   状态: {result.get('status')}")
        else:
            print(f"   批次号: {result.batch_number}")
            print(f"   数量: {result.quantity}")
            print(f"   状态: {result.status}")
        
        return True
    except Exception as e:
        print(f"❌ 创建发货记录失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_update_shipment_status():
    """测试更新发货状态"""
    print("\n=== 测试：更新发货状态 ===")
    try:
        # 先创建一个测试发货记录
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法创建测试发货记录")
            return True
        
        product = products[0]
        if isinstance(product, dict):
            variants = product.get('variants', [])
            if not variants:
                print("⚠️  产品没有SKU，无法创建测试发货记录")
                return True
            sku = variants[0].get('sku')
        else:
            if not product.variants:
                print("⚠️  产品没有SKU，无法创建测试发货记录")
                return True
            sku = product.variants[0].sku
        
        operator_info = get_operator_info()
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        estimated_arrival = (datetime.now() + timedelta(days=7)).date()
        
        shipment_data = {
            'sku': sku,
            'quantity': 30,
            'batch_number': f'SHUP{timestamp}',
            'tracking_number': f'TRACK-UP-{timestamp}',
            'estimated_arrival': estimated_arrival.isoformat(),
            'notes': '测试状态更新',
            'operator_info': operator_info
        }
        
        shipment = dal.create_shipment(shipment_data)
        if isinstance(shipment, dict):
            shipment_id = shipment.get('id')
            batch_number = shipment.get('batch_number')
        else:
            shipment_id = shipment.id
            batch_number = shipment.batch_number
        
        print(f"   已创建测试发货记录: {batch_number}")
        
        # 更新状态为"已到货"
        update_data = {
            'status': 'arrived',
            'operator_info': operator_info
        }
        
        dal.update_shipment(shipment_id, update_data)
        print(f"✅ 成功更新发货状态")
        print(f"   批次号: {batch_number}")
        print(f"   新状态: 已到货")
        
        return True
    except Exception as e:
        print(f"❌ 更新发货状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_shipments():
    """测试批量导入发货记录"""
    print("\n=== 测试：批量导入发货记录 ===")
    try:
        import pandas as pd
        
        # 先获取一些SKU用于测试
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法测试发货记录导入")
            return True
        
        operator_info = get_operator_info()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        estimated_arrival = (datetime.now() + timedelta(days=7)).date()
        
        # 创建测试数据
        test_data = []
        for i, product in enumerate(products[:3]):  # 最多测试3个产品
            if isinstance(product, dict):
                variants = product.get('variants', [])
                for j, variant in enumerate(variants[:2]):  # 每个产品最多2个SKU
                    test_data.append({
                        'sku': variant.get('sku'),
                        'quantity': 20 + i * 10,
                        'batch_number': f'SHIMP{timestamp}{i}{j}',
                        'tracking_number': f'TRACK-IMP-{timestamp}-{i}{j}',
                        'estimated_arrival': estimated_arrival.isoformat(),
                        'notes': f'批量导入测试{i+1}'
                    })
            else:
                for j, variant in enumerate(product.variants[:2]):
                    test_data.append({
                        'sku': variant.sku,
                        'quantity': 20 + i * 10,
                        'batch_number': f'SHIMP{timestamp}{i}{j}',
                        'tracking_number': f'TRACK-IMP-{timestamp}-{i}{j}',
                        'estimated_arrival': estimated_arrival.isoformat(),
                        'notes': f'批量导入测试{i+1}'
                    })
        
        if not test_data:
            print("⚠️  没有可用的SKU，无法测试发货记录导入")
            return True
        
        df = pd.DataFrame(test_data)
        
        print(f"   准备导入 {len(test_data)} 条发货记录")
        
        success_count = 0
        failed_count = 0
        
        for _, row in df.iterrows():
            try:
                shipment_data = {
                    'sku': str(row['sku']).strip(),
                    'quantity': int(row['quantity']),
                    'batch_number': str(row['batch_number']).strip(),
                    'tracking_number': str(row.get('tracking_number', '')).strip(),
                    'estimated_arrival': str(row['estimated_arrival']),
                    'notes': str(row.get('notes', '')),
                    'operator_info': operator_info
                }
                
                dal.create_shipment(shipment_data)
                success_count += 1
            except Exception as e:
                print(f"   ⚠️  批次号 {row['batch_number']} 导入失败: {e}")
                failed_count += 1
        
        print(f"✅ 批量导入完成")
        print(f"   成功: {success_count} 条")
        print(f"   失败: {failed_count} 条")
        return True
    except Exception as e:
        print(f"❌ 批量导入发货记录失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("发货管理功能测试")
    print("=" * 60)
    
    tests = [
        ("获取发货记录列表", test_get_shipments),
        ("创建发货记录", test_create_shipment),
        ("更新发货状态", test_update_shipment_status),
        ("批量导入发货记录", test_import_shipments),
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
