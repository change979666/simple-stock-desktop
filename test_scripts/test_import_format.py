"""
测试导入功能的数据格式一致性
验证客户端、API、服务端的请求/响应格式是否匹配
"""

import json
import requests

# 配置
BASE_URL = "http://192.168.1.3:8001"

def test_sales_import_format():
    """测试销售订单导入格式"""
    print("\n=== 测试销售订单导入 ===")
    
    # 模拟GUI发送的数据结构
    test_data = {
        "orders": [
            {
                "order_number": "TEST_ORD001",
                "customer_name": "测试客户",
                "order_date": "2025-01-15T10:00:00",
                "items": [
                    {
                        "parent_sku": "BD71-Black-105CM",
                        "variant_sku": "BD71-Black-105CM",
                        "quantity": 2,
                        "item_price": 59.90
                    }
                ]
            }
        ],
        "operator_info": json.dumps({
            "operator_name": "测试员",
            "ip_address": "127.0.0.1"
        }, ensure_ascii=False)
    }
    
    print(f"发送数据结构:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sales/import",
            json=test_data,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 销售订单导入格式正确")
            print(f"   成功: {result.get('success', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
            if result.get('errors'):
                print(f"   错误: {result.get('errors')}")
        else:
            print(f"❌ 销售订单导入失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")


def test_shipment_import_format():
    """测试发货记录导入格式"""
    print("\n=== 测试发货记录导入 ===")
    
    # 模拟GUI发送的数据结构
    test_data = {
        "shipments": [
            {
                "order_number": "ORD20250014",
                "logistics_number": "TEST_LOG001",
                "logistics_company": "顺丰速运",
                "logistics_fee": 15.00,
                "shipment_date": "2025-01-15T10:00:00"
            }
        ],
        "operator_info": json.dumps({
            "operator_name": "测试员",
            "ip_address": "127.0.0.1"
        }, ensure_ascii=False)
    }
    
    print(f"发送数据结构:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/shipments/import",
            json=test_data,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 发货记录导入格式正确")
            print(f"   成功: {result.get('success', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
            if result.get('errors'):
                print(f"   错误: {result.get('errors')}")
        else:
            print(f"❌ 发货记录导入失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")


def test_product_import_format():
    """测试产品导入格式"""
    print("\n=== 测试产品导入 ===")
    
    # 模拟GUI发送的数据结构
    test_data = {
        "products": [
            {
                "product_name": "测试产品",
                "sku": "TEST_SKU001",
                "option1_value": "黑色",
                "option2_value": "M",
                "cost_price": 100.0,
                "initial_stock": 50
            }
        ],
        "operator_info": json.dumps({
            "operator_name": "测试员",
            "ip_address": "127.0.0.1"
        }, ensure_ascii=False)
    }
    
    print(f"发送数据结构:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/products/import",
            json=test_data,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 产品导入格式正确")
            print(f"   成功: {result.get('success', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
            if result.get('message'):
                print(f"   消息: {result.get('message')}")
        else:
            print(f"❌ 产品导入失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("导入功能格式测试")
    print("=" * 60)
    
    # 测试三个导入功能
    test_sales_import_format()
    test_shipment_import_format()
    test_product_import_format()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
