"""通过API检查服务器上的产品数据"""
import requests
import json

server_url = "http://192.168.1.3:8001"

try:
    # 获取产品列表
    print("正在连接服务器...")
    response = requests.get(f"{server_url}/api/products", timeout=10)
    
    if response.status_code == 200:
        products = response.json()
        print(f"\n服务器上的产品数量: {len(products)}")
        
        if products:
            print("\n前10个产品:")
            for i, product in enumerate(products[:10], 1):
                parent_sku = product.get('parent_sku', 'N/A')
                variant_count = len(product.get('variants', []))
                print(f"{i}. 父SKU: {parent_sku}, 变体数: {variant_count}")
                
                # 显示前3个变体
                for v in product.get('variants', [])[:3]:
                    sku = v.get('sku', 'N/A')
                    option = v.get('option_name', 'N/A')
                    cost = v.get('cost_price', 0)
                    print(f"   - {sku}: {option}, 成本: {cost}")
        else:
            print("\n⚠️ 服务器上没有任何产品数据！")
            print("这就是为什么界面上看不到数据。")
            
    else:
        print(f"❌ 请求失败: HTTP {response.status_code}")
        print(f"响应: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ 无法连接到服务器 192.168.1.3:8001")
    print("请确保服务器正在运行")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
