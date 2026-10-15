"""测试API返回的产品数据"""
from client.api_client import api_client
from config.settings import load_settings
import json

# 配置客户端
settings = load_settings()
server_address = settings.get('server_address', '').strip()
if ':' in server_address:
    host, port_str = server_address.split(':', 1)
    port = int(port_str)
else:
    host = server_address
    port = 8001

api_client.configure(host=host, port=port, operator_info='测试')

print("=" * 60)
print("测试 API 返回的产品数据")
print("=" * 60)

try:
    products = api_client.get_products()
    
    print(f"获取到 {len(products)} 个产品")
    print()
    
    if products:
        # 检查第一个产品的数据结构
        first_product = products[0]
        print("第一个产品的数据类型:", type(first_product))
        print()
        
        print("=" * 60)
        print("检查关键字段:")
        print("=" * 60)
        
        if isinstance(first_product, dict):
            print(f"parent_sku: {first_product.get('parent_sku')}")
            print(f"stock_warning_level: {first_product.get('stock_warning_level')}")
            print(f"字段列表: {list(first_product.keys())}")
        else:
            print(f"parent_sku: {getattr(first_product, 'parent_sku', 'N/A')}")
            print(f"stock_warning_level: {getattr(first_product, 'stock_warning_level', 'N/A')}")
        print()
        
        # 检查所有产品的 stock_warning_level
        print("=" * 60)
        print("所有产品的 stock_warning_level:")
        print("=" * 60)
        for p in products[:10]:
            if isinstance(p, dict):
                sku = p.get('parent_sku')
                warning = p.get('stock_warning_level')
            else:
                sku = getattr(p, 'parent_sku', 'N/A')
                warning = getattr(p, 'stock_warning_level', 'N/A')
            print(f"{sku}: {warning}")
        
except Exception as e:
    print(f"❌ API调用失败: {e}")
    import traceback
    traceback.print_exc()
