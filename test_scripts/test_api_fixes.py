"""
测试307重定向修复和产品导入功能
"""

import requests
import json

BASE_URL = "http://192.168.1.3:8001"


def test_307_redirect():
    """测试307重定向是否修复"""
    print("\n=== 测试307重定向修复 ===")
    
    endpoints = [
        "/api/products",
        "/api/shipments",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                timeout=10,
                allow_redirects=False  # 不自动跟随重定向
            )
            
            if response.status_code == 307:
                print(f"❌ {endpoint} - 仍然返回307重定向")
            elif response.status_code == 200:
                print(f"✅ {endpoint} - 正常返回200")
            else:
                print(f"⚠️  {endpoint} - 返回 {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint} - 请求异常: {str(e)}")


def test_product_import():
    """测试产品导入功能"""
    print("\n=== 测试产品导入功能 ===")
    
    test_data = {
        "products": [
            {
                "product_name": "测试产品AUTO",
                "sku": f"TEST_AUTO_SKU_{int(__import__('time').time())}",
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
    
    print(f"\n发送数据:")
    print(f"  产品名: {test_data['products'][0]['product_name']}")
    print(f"  SKU: {test_data['products'][0]['sku']}")
    print(f"  初始库存: {test_data['products'][0]['initial_stock']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/products/import",
            json=test_data,
            timeout=10
        )
        
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 产品导入成功")
            print(f"   成功: {result.get('success', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
            print(f"   消息: {result.get('message', '')}")
            
            if result.get('errors'):
                print(f"   错误详情: {result.get('errors')}")
                return False
            return True
        else:
            print(f"\n❌ 产品导入失败")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("API修复验证测试")
    print("=" * 60)
    
    # 测试307重定向
    test_307_redirect()
    
    # 测试产品导入
    test_product_import()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
