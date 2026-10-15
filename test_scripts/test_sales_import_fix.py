"""
销售订单导入事务修复验证脚本

用于测试修复后的批量导入功能，验证：
1. 正常订单导入成功
2. 重复订单自动跳过
3. 缺少必填字段时失败但不影响其他订单
4. 日志记录完整
"""

import requests
import json
from datetime import datetime


def test_sales_import():
    """测试销售订单批量导入"""
    
    # 服务器地址（根据实际配置修改）
    BASE_URL = "http://192.168.1.3:8001"
    
    print("=" * 60)
    print("销售订单导入事务修复验证")
    print("=" * 60)
    
    # 测试1: 正常导入
    print("\n测试1: 正常导入订单")
    print("-" * 60)
    
    test_order_number = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    data = {
        "orders": [
            {
                "order_number": test_order_number,
                "customer_name": "测试客户A",
                "order_date": datetime.now().isoformat(),
                "total_amount": 200.0,
                "items": [
                    {
                        "parent_sku": "TEST-SKU",
                        "variant_sku": "TEST-SKU-001",
                        "quantity": 2,
                        "item_price": 100.0
                    }
                ]
            }
        ],
        "operator_info": json.dumps({"name": "测试员"})
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/sales/import", json=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print("✅ 测试1通过: 正常订单导入成功")
        else:
            print(f"❌ 测试1失败: 返回状态码 {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试1失败: {str(e)}")
    
    # 测试2: 重复订单（应跳过）
    print("\n测试2: 重复订单号（应自动跳过）")
    print("-" * 60)
    
    try:
        response = requests.post(f"{BASE_URL}/api/sales/import", json=data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if (response.status_code == 200 and 
            result['skipped'] == 1 and 
            result['success'] == 0):
            print("✅ 测试2通过: 重复订单自动跳过")
        else:
            print("❌ 测试2失败: 重复订单未正确跳过")
            
    except Exception as e:
        print(f"❌ 测试2失败: {str(e)}")
    
    # 测试3: 批量导入（包含成功、跳过、失败）
    print("\n测试3: 混合批量导入（成功+跳过+失败）")
    print("-" * 60)
    
    mixed_data = {
        "orders": [
            # 订单1: 正常（应成功）
            {
                "order_number": f"TEST-OK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "customer_name": "正常客户",
                "order_date": datetime.now().isoformat(),
                "total_amount": 100.0,
                "items": [
                    {
                        "parent_sku": "OK-SKU",
                        "variant_sku": "OK-SKU-001",
                        "quantity": 1,
                        "item_price": 100.0
                    }
                ]
            },
            # 订单2: 重复（应跳过）
            {
                "order_number": test_order_number,  # 使用测试1的订单号
                "customer_name": "重复客户",
                "order_date": datetime.now().isoformat(),
                "total_amount": 50.0,
                "items": [
                    {
                        "parent_sku": "DUP-SKU",
                        "variant_sku": "DUP-SKU-001",
                        "quantity": 1,
                        "item_price": 50.0
                    }
                ]
            },
            # 订单3: 缺少订单号（应失败）
            {
                # "order_number": "",  # 缺少订单号
                "customer_name": "失败客户",
                "order_date": datetime.now().isoformat(),
                "items": [
                    {
                        "parent_sku": "FAIL-SKU",
                        "variant_sku": "FAIL-SKU-001",
                        "quantity": 1,
                        "item_price": 30.0
                    }
                ]
            },
            # 订单4: 正常（应成功）
            {
                "order_number": f"TEST-OK2-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "customer_name": "正常客户2",
                "order_date": datetime.now().isoformat(),
                "total_amount": 80.0,
                "items": [
                    {
                        "parent_sku": "OK2-SKU",
                        "variant_sku": "OK2-SKU-001",
                        "quantity": 1,
                        "item_price": 80.0
                    }
                ]
            }
        ],
        "operator_info": json.dumps({"name": "测试员"})
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/sales/import", json=mixed_data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if (response.status_code == 200 and 
            result['success'] == 2 and 
            result['skipped'] == 1 and 
            result['failed'] == 1):
            print("✅ 测试3通过: 混合批量导入结果正确")
            print(f"   - 成功: {result['success']} 个")
            print(f"   - 跳过: {result['skipped']} 个")
            print(f"   - 失败: {result['failed']} 个")
        else:
            print("❌ 测试3失败: 混合批量导入结果不符合预期")
            print(f"   预期: 成功2, 跳过1, 失败1")
            print(f"   实际: 成功{result['success']}, "
                  f"跳过{result['skipped']}, 失败{result['failed']}")
            
    except Exception as e:
        print(f"❌ 测试3失败: {str(e)}")
    
    # 测试4: 验证不存在的SKU（应成功但有警告日志）
    print("\n测试4: 不存在的SKU（订单应成功创建，但库存不扣减）")
    print("-" * 60)
    
    nonexist_data = {
        "orders": [
            {
                "order_number": f"TEST-NOSKU-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "customer_name": "测试客户-不存在SKU",
                "order_date": datetime.now().isoformat(),
                "total_amount": 10.0,
                "items": [
                    {
                        "parent_sku": "NONEXIST",
                        "variant_sku": "NONEXIST-VARIANT-999",
                        "quantity": 1,
                        "item_price": 10.0
                    }
                ]
            }
        ],
        "operator_info": json.dumps({"name": "测试员"})
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/sales/import", json=nonexist_data)
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and result['success'] == 1:
            print("✅ 测试4通过: 不存在SKU的订单创建成功")
            print("   提示: 请检查后端日志，应有警告信息：")
            print("   'SKU NONEXIST-VARIANT-999 未找到对应的产品变体'")
        else:
            print("❌ 测试4失败: 不存在SKU的订单处理异常")
            
    except Exception as e:
        print(f"❌ 测试4失败: {str(e)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n请检查后端日志，验证以下内容：")
    print("1. 每个订单的处理进度 [idx/total]")
    print("2. 订单创建成功的日志（包含订单ID）")
    print("3. 跳过订单的日志（订单号已存在）")
    print("4. 失败订单的错误堆栈跟踪")
    print("5. 不存在SKU的警告信息")
    print("6. 批次提交成功的操作日志")
    print("\n推荐使用以下 SQL 验证数据库记录：")
    print("-- 查看刚才导入的订单")
    print(f"SELECT * FROM sale_orders WHERE order_number LIKE 'TEST-%' "
          f"ORDER BY created_at DESC LIMIT 10;")
    print("\n-- 查看操作日志")
    print("SELECT * FROM action_logs WHERE action LIKE '%批量导入%' "
          "ORDER BY created_at DESC LIMIT 5;")


if __name__ == "__main__":
    test_sales_import()
