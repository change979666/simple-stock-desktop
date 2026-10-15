"""直接测试API端点返回的数据"""
import requests

url = "http://192.168.1.3:8001/api/products"

try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
        products = response.json()
        print(f"API返回 {len(products)} 个产品")
        print()
        
        if products:
            first = products[0]
            print("第一个产品:")
            print(f"  parent_sku: {first.get('parent_sku')}")
            print(f"  stock_warning_level: {first.get('stock_warning_level')}")
            print()
            
            print("所有产品的 stock_warning_level:")
            for p in products:
                print(f"  {p.get('parent_sku')}: {p.get('stock_warning_level')}")
    else:
        print(f"API返回错误: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"请求失败: {e}")
