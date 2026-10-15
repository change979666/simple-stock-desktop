"""完整检查预警值数据流程"""
from database.session import SessionLocal
from database.models import Product
from config.settings import load_settings
from crud.operations import get_products_below_warning_level

print("=" * 60)
print("1. 配置文件检查")
print("=" * 60)
settings = load_settings()
global_warning = settings.get('default_warning_level', 96)
print(f"配置文件 default_warning_level: {global_warning}")
print()

print("=" * 60)
print("2. 数据库产品预警值检查")
print("=" * 60)
db = SessionLocal()
products = db.query(Product).limit(10).all()
print(f"检查前10个产品的 stock_warning_level 字段:")
for p in products:
    print(f"  {p.parent_sku}: stock_warning_level = {p.stock_warning_level}")
print()

print("=" * 60)
print("3. get_products_below_warning_level 函数测试")
print("=" * 60)
warnings = get_products_below_warning_level(db, threshold_ratio=1.0)
print(f"预警产品数量: {len(warnings)}")
if warnings:
    print("前5个预警产品的预警值:")
    for w in warnings[:5]:
        print(f"  {w['parent_sku']}-{w['variant_sku']}: "
              f"库存={w['current_stock']}, "
              f"预警值={w['warning_level']}")
print()

print("=" * 60)
print("4. 模拟API返回数据")
print("=" * 60)
# 模拟 api/routes/products.py 的返回格式
product = db.query(Product).first()
if product:
    product_dict = {
        'id': product.id,
        'parent_sku': product.parent_sku,
        'stock_warning_level': product.stock_warning_level,
    }
    print(f"API返回的产品数据:")
    print(f"  parent_sku: {product_dict['parent_sku']}")
    print(f"  stock_warning_level: {product_dict['stock_warning_level']}")
    
    # 模拟客户端的逻辑
    used_warning = product_dict['stock_warning_level'] or global_warning
    print(f"\n客户端使用的预警值: {used_warning}")
    print(f"  (产品={product_dict['stock_warning_level']}, 全局={global_warning})")

db.close()

print()
print("=" * 60)
print("5. 结论")
print("=" * 60)
print("如果所有产品的 stock_warning_level = None")
print("那么应该使用全局配置值:", global_warning)
print("如果显示的不是这个值，说明客户端代码有问题")
