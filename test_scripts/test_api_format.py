"""测试API返回数据格式"""
import requests
import json
from pprint import pprint

BASE_URL = "http://192.168.1.3:8001"

def test_products_api():
    """测试产品API"""
    print("\n" + "="*60)
    print("测试产品API: GET /api/products/")
    print("="*60)
    
    r = requests.get(f"{BASE_URL}/api/products/")
    print(f"状态码: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"产品数量: {len(data)}")
        if data:
            print("\n第一个产品结构:")
            pprint(data[0])
            if data[0].get('variants'):
                print("\n第一个变体结构:")
                pprint(data[0]['variants'][0])
    else:
        print(f"错误: {r.text}")


def test_operation_logs_api():
    """测试操作日志API"""
    print("\n" + "="*60)
    print("测试操作日志API: GET /api/logs/operations")
    print("="*60)
    
    r = requests.get(f"{BASE_URL}/api/logs/operations")
    print(f"状态码: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"日志数量: {len(data)}")
        if data:
            print("\n第一条日志结构:")
            pprint(data[0])
            print("\n日志字段:", list(data[0].keys()))
    else:
        print(f"错误: {r.text}")


def test_sales_orders_api():
    """测试销售订单API"""
    print("\n" + "="*60)
    print("测试销售订单API: GET /api/sales/orders")
    print("="*60)
    
    r = requests.get(f"{BASE_URL}/api/sales/orders")
    print(f"状态码: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"订单数量: {len(data)}")
        if data:
            print("\n第一个订单结构:")
            pprint(data[0])
            print("\n订单字段:", list(data[0].keys()))
    else:
        print(f"错误: {r.text}")


def test_delete_product():
    """测试删除产品"""
    print("\n" + "="*60)
    print("测试删除产品API (模拟)")
    print("="*60)
    
    operator_info = {
        "operator_name": "测试用户",
        "ip_address": "192.168.1.3",
        "timestamp": "2025-10-15T14:00:00"
    }
    
    # 不实际删除，只测试参数格式
    print("操作者信息格式:")
    pprint(operator_info)
    print("\nJSON格式:")
    print(json.dumps(operator_info, ensure_ascii=False))


if __name__ == "__main__":
    test_products_api()
    test_operation_logs_api()
    test_sales_orders_api()
    test_delete_product()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
