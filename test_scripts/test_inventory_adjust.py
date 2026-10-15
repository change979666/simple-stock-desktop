"""
快速测试库存调整功能
验证 ProductVariant.current_stock 属性修复
"""

import requests
import json

BASE_URL = "http://192.168.1.3:8001"

def test_adjust_inventory():
    """测试库存调整API"""
    print("=== 测试库存调整 ===")
    
    # 测试数据
    test_data = {
        "sku": "BD71-Black-105CM",
        "quantity": 5,
        "notes": "测试库存调整",
        "operator_info": {
            "operator_name": "测试员",
            "ip_address": "127.0.0.1"
        }
    }
    
    print(f"\n发送数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/inventory/adjust",
            json=test_data,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 库存调整成功")
            print(f"   SKU: {result.get('sku')}")
            print(f"   调整数量: {result.get('quantity_change')}")
            print(f"   新库存: {result.get('new_stock')}")
            return True
        else:
            print(f"\n❌ 库存调整失败")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_adjust_inventory()
