"""清空产品和变体表"""
from database.session import SessionLocal
from database.models import ProductVariant, Product

db = SessionLocal()

try:
    # 删除所有变体
    deleted_variants = db.query(ProductVariant).delete()
    print(f'已删除 {deleted_variants} 个SKU变体')
    
    # 删除所有产品
    deleted_products = db.query(Product).delete()
    print(f'已删除 {deleted_products} 个产品')
    
    db.commit()
    print('\n数据库已清空，可以重新导入了！')
    
except Exception as e:
    db.rollback()
    print(f'错误: {e}')
finally:
    db.close()
