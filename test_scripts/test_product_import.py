"""
测试产品导入功能 - 使用实际模板
"""

import requests
import json
import pandas as pd

BASE_URL = "http://192.168.1.3:8001"


def test_product_import_with_template():
    """使用实际模板测试产品导入"""
    print("\n=== 测试产品导入功能（使用模板数据）===")
    
    # 读取模板数据
    template_path = r"docs\产品导入模板_v2.0.1.xlsx"
    
    try:
        df = pd.read_excel(template_path)
        print(f"\n模板列名: {list(df.columns)}")
        print(f"数据行数: {len(df)}")
        
        # 只取前2行测试
        test_df = df.head(2)
        print(f"\n测试数据:")
        print(test_df)
        
        # 转换为API格式
        products = test_df.to_dict('records')
        
        # 构造请求数据
        test_data = {
            "products": products,
            "operator_info": json.dumps({
                "operator_name": "测试员",
                "ip_address": "127.0.0.1"
            }, ensure_ascii=False)
        }
        
        print(f"\n发送的产品数据:")
        for p in products:
            print(f"  parent_sku: {p.get('parent_sku')}")
            print(f"  sku: {p.get('sku')}")
            print(f"  option_name: {p.get('option_name')}")
            print(f"  cost_price: {p.get('cost_price')}")
            print()
        
        # 发送请求
        response = requests.post(
            f"{BASE_URL}/api/products/import",
            json=test_data,
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 产品导入测试完成")
            print(f"   成功: {result.get('success', 0)}")
            print(f"   失败: {result.get('failed', 0)}")
            print(f"   消息: {result.get('message', '')}")
            
            if result.get('errors'):
                print(f"\n   错误详情:")
                for error in result.get('errors', []):
                    print(f"     - {error}")
                return False
            
            if result.get('success', 0) > 0:
                print(f"\n✅ 导入成功！")
                return True
            else:
                print(f"\n❌ 没有成功导入任何产品")
                return False
        else:
            print(f"\n❌ 产品导入失败")
            print(f"   响应: {response.text}")
            return False
            
    except FileNotFoundError:
        print(f"❌ 找不到模板文件: {template_path}")
        return False
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_imported_products():
    """验证导入的产品"""
    print("\n=== 验证导入的产品 ===")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/products",
            timeout=10
        )
        
        if response.status_code == 200:
            products = response.json()
            print(f"\n产品总数: {len(products)}")
            
            # 查找刚导入的产品
            for product in products[:5]:  # 只显示前5个
                print(f"\n产品: {product.get('name')}")
                variants = product.get('variants', [])
                for variant in variants[:2]:  # 每个产品只显示前2个变体
                    print(f"  - SKU: {variant.get('sku')}")
                    print(f"    规格: {variant.get('option_name')}")
                    print(f"    成本价: {variant.get('cost_price')}")
            
            return True
        else:
            print(f"❌ 获取产品列表失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 验证异常: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("产品导入功能测试（基于模板）")
    print("=" * 60)
    
    # 测试导入
    import_success = test_product_import_with_template()
    
    if import_success:
        # 验证导入结果
        verify_imported_products()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
