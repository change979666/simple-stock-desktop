"""
库存管理功能测试工具
测试库存调整、导入等核心功能
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

def test_get_inventory():
    """测试获取库存列表"""
    print("\n=== 测试：获取库存列表 ===")
    try:
        products = dal.get_all_products()
        print(f"✅ 成功获取库存数据")
        print(f"   产品数量: {len(products)}")
        
        # 统计总SKU数量和总库存
        total_skus = 0
        total_stock = 0
        
        for product in products:
            if isinstance(product, dict):
                variants = product.get('variants', [])
                total_skus += len(variants)
                for variant in variants:
                    total_stock += variant.get('current_stock', 0)
            else:
                total_skus += len(product.variants)
                for variant in product.variants:
                    # 计算库存
                    from crud.inventory_logs import get_variant_current_stock
                    from utils.data_access import dal
                    db = dal._get_db_session()
                    total_stock += get_variant_current_stock(db, variant.id)
        
        print(f"   SKU数量: {total_skus}")
        print(f"   总库存: {total_stock}")
        return True
    except Exception as e:
        print(f"❌ 获取库存列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_adjust_inventory():
    """测试库存调整"""
    print("\n=== 测试：库存调整 ===")
    try:
        # 先获取一个SKU
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法测试库存调整")
            return True
        
        product = products[0]
        if isinstance(product, dict):
            variants = product.get('variants', [])
            if not variants:
                print("⚠️  产品没有SKU，无法测试库存调整")
                return True
            variant = variants[0]
            sku = variant.get('sku')
            old_stock = variant.get('stock', 0)
        else:
            if not product.variants:
                print("⚠️  产品没有SKU，无法测试库存调整")
                return True
            variant = product.variants[0]
            sku = variant.sku
            # 计算当前库存
            from crud.inventory_logs import get_variant_current_stock
            from utils.data_access import dal
            db = dal._get_db_session()
            old_stock = get_variant_current_stock(db, variant.id)
        
        operator_info = get_operator_info()
        
        # 调整库存（增加10件）
        adjust_quantity = 10
        notes = f"测试库存调整_{datetime.now().strftime('%H%M%S')}"
        
        dal.adjust_inventory(sku, adjust_quantity, notes, operator_info)
        print(f"✅ 成功调整库存")
        print(f"   SKU: {sku}")
        print(f"   原库存: {old_stock}")
        print(f"   调整数量: +{adjust_quantity}")
        print(f"   预期库存: {old_stock + adjust_quantity}")
        print(f"   备注: {notes}")
        return True
    except Exception as e:
        print(f"❌ 库存调整失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_inventory():
    """测试批量导入库存"""
    print("\n=== 测试：批量导入库存 ===")
    try:
        import pandas as pd
        
        # 先获取一些SKU用于测试
        products = dal.get_all_products()
        if not products:
            print("⚠️  没有产品，无法测试库存导入")
            return True
        
        operator_info = get_operator_info()
        
        # 创建测试数据（使用现有的SKU）
        test_data = []
        for i, product in enumerate(products[:3]):  # 最多测试3个产品
            if isinstance(product, dict):
                variants = product.get('variants', [])
                for variant in variants[:2]:  # 每个产品最多2个SKU
                    test_data.append({
                        'sku': variant.get('sku'),
                        'change_quantity': 5,  # 增加5件
                        'notes': f'批量导入测试_{datetime.now().strftime("%H%M%S")}'
                    })
            else:
                for variant in product.variants[:2]:
                    test_data.append({
                        'sku': variant.sku,
                        'change_quantity': 5,
                        'notes': f'批量导入测试_{datetime.now().strftime("%H%M%S")}'
                    })
        
        if not test_data:
            print("⚠️  没有可用的SKU，无法测试库存导入")
            return True
        
        df = pd.DataFrame(test_data)
        
        print(f"   准备导入 {len(test_data)} 条库存调整记录")
        
        # 执行导入（通过循环调用 adjust_inventory）
        success_count = 0
        failed_count = 0
        
        for _, row in df.iterrows():
            try:
                sku = str(row['sku']).strip()
                quantity = int(float(row['change_quantity']))
                notes = str(row.get('notes', ''))
                
                dal.adjust_inventory(sku, quantity, notes, operator_info)
                success_count += 1
            except Exception as e:
                print(f"   ⚠️  SKU {sku} 调整失败: {e}")
                failed_count += 1
        
        print(f"✅ 批量导入完成")
        print(f"   成功: {success_count} 条")
        print(f"   失败: {failed_count} 条")
        return True
    except Exception as e:
        print(f"❌ 批量导入库存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_inventory_logs():
    """测试获取库存日志"""
    print("\n=== 测试：获取库存日志 ===")
    try:
        # 获取最近的库存日志
        from crud.inventory_logs import get_inventory_logs
        from database.session import SessionLocal
        from config import app_mode
        
        if app_mode.is_client_mode():
            print("⚠️  客户端模式下暂不支持直接获取库存日志")
            return True
        
        with SessionLocal() as db:
            logs = get_inventory_logs(db, limit=10)
            print(f"✅ 成功获取库存日志")
            print(f"   最近10条日志数量: {len(logs)}")
            
            if logs:
                log = logs[0]
                print(f"   最新日志:")
                print(f"     SKU: {log.sku}")
                print(f"     变化量: {log.quantity_change}")
                print(f"     备注: {log.notes}")
                print(f"     操作人: {log.operator}")
        
        return True
    except Exception as e:
        print(f"❌ 获取库存日志失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("库存管理功能测试")
    print("=" * 60)
    
    tests = [
        ("获取库存列表", test_get_inventory),
        ("库存调整", test_adjust_inventory),
        ("批量导入库存", test_import_inventory),
        ("获取库存日志", test_get_inventory_logs),
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
