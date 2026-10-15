"""检查当前预警值"""
from database.session import SessionLocal
from crud.operations import get_products_below_warning_level
from config.settings import load_settings

db = SessionLocal()
settings = load_settings()

print("=" * 50)
print("当前预警值检查")
print("=" * 50)
print(f"全局预警值配置: {settings.get('default_warning_level', 96)}")
print()

# 获取预警产品
warnings = get_products_below_warning_level(db, 1.0)
print(f"预警产品数量: {len(warnings)}")
print()

if warnings:
    print("前5个产品的预警值:")
    for w in warnings[:5]:
        print(f"  {w['parent_sku']}-{w['variant_sku']}: "
              f"库存={w['current_stock']}, "
              f"预警值={w['warning_level']}")

db.close()
