"""检查产品的预警值设置"""
from database.session import SessionLocal
from database.models import Product, ProductVariant
from sqlalchemy import inspect

db = SessionLocal()

# 检查ProductVariant表结构
inspector = inspect(db.bind)
columns = [col['name'] for col in inspector.get_columns('product_variants')]
print("ProductVariant表字段:")
print(columns)
print()

# 检查Product表结构
columns = [col['name'] for col in inspector.get_columns('products')]
print("Product表字段:")
print(columns)
print()

# 检查几个产品的预警值
variants = db.query(ProductVariant).join(Product).limit(10).all()
print("产品预警值:")
for v in variants:
    parent = v.product
    print(f"{parent.parent_sku}-{v.sku}:")
    
    # 检查variant是否有warning_threshold
    if hasattr(v, 'warning_threshold'):
        print(f"  variant.warning_threshold = {v.warning_threshold}")
    
    # 检查product是否有warning_threshold  
    if hasattr(parent, 'warning_threshold'):
        print(f"  product.warning_threshold = {parent.warning_threshold}")
    
    # 检查其他可能的字段
    if hasattr(v, 'stock_warning_level'):
        print(f"  variant.stock_warning_level = {v.stock_warning_level}")
    if hasattr(parent, 'stock_warning_level'):
        print(f"  product.stock_warning_level = {parent.stock_warning_level}")
    print()

db.close()
