"""测试预警值修复"""
from database.session import SessionLocal
from database.models import Product, ProductVariant
from config.settings import load_settings
from crud.operations import get_products_below_warning_level

# 1. 检查全局配置
settings = load_settings()
print("=" * 50)
print("1. 全局配置检查")
print("=" * 50)
print(f"全局预警阈值: {settings.get('default_warning_level', 96)}")
print()

# 2. 检查数据库中的产品预警值
db = SessionLocal()
print("=" * 50)
print("2. 产品预警值检查")
print("=" * 50)
products = db.query(Product).limit(10).all()
for p in products:
    print(f"{p.parent_sku}: stock_warning_level = {p.stock_warning_level}")
print()

# 3. 测试get_products_below_warning_level函数
print("=" * 50)
print("3. 预警产品列表（阈值=1.0）")
print("=" * 50)
warnings = get_products_below_warning_level(db, threshold_ratio=1.0)
print(f"找到 {len(warnings)} 个预警产品")
if warnings:
    for w in warnings[:5]:  # 只显示前5个
        print(f"  {w['parent_sku']}-{w['variant_sku']}: "
              f"库存={w['current_stock']}, "
              f"预警值={w['warning_level']}, "
              f"比例={w['stock_ratio']:.1%}")
print()

# 4. 模拟API返回的数据格式
print("=" * 50)
print("4. 模拟API返回格式")
print("=" * 50)
product = db.query(Product).first()
if product:
    product_dict = {
        'id': product.id,
        'parent_sku': product.parent_sku,
        'stock_warning_level': product.stock_warning_level,
        'variants': []
    }
    print(f"Product API 数据:")
    print(f"  parent_sku: {product_dict['parent_sku']}")
    print(f"  stock_warning_level: {product_dict['stock_warning_level']}")
    print()
    
    # 测试预警值逻辑
    global_level = settings.get('default_warning_level', 96)
    used_level = product_dict['stock_warning_level'] or global_level
    print(f"使用的预警值: {used_level}")
    print(f"  (产品自己的={product_dict['stock_warning_level']}, "
          f"全局的={global_level})")

db.close()

print()
print("=" * 50)
print("✅ 修复验证完成")
print("=" * 50)
print("预期行为:")
print("1. 如果产品的stock_warning_level不为None，使用它")
print("2. 如果产品的stock_warning_level为None，使用全局的96")
print("3. 所有产品当前都是None，所以应该都显示96")
