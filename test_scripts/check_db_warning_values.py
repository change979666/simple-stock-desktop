"""检查数据库中产品的预警值分布"""
from database.session import SessionLocal
from database.models import Product

db = SessionLocal()

products = db.query(Product).all()

print("=" * 60)
print("数据库产品预警值统计")
print("=" * 60)
print(f"产品总数: {len(products)}")
print()

# 统计各种预警值的数量
warning_values = {}
for p in products:
    val = p.stock_warning_level
    warning_values[val] = warning_values.get(val, 0) + 1

print("预警值分布:")
for val, count in sorted(warning_values.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"  {val}: {count} 个产品")

print()
print("前10个产品的预警值:")
for p in products[:10]:
    print(f"  {p.parent_sku}: stock_warning_level = {p.stock_warning_level}")

db.close()
