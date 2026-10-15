"""检查数据库中的SKU"""
from database.session import SessionLocal
from database.models import ProductVariant, Product

db = SessionLocal()

try:
    # 查询所有变体
    variants = db.query(ProductVariant).all()
    print(f'数据库中现有的SKU数量: {len(variants)}')
    
    if variants:
        print('\n现有SKU列表:')
        for v in variants:
            print(f'  - SKU: {v.sku}, 规格: {v.option_name}, 成本: {v.cost_price}')
    else:
        print('数据库中没有任何SKU！')
    
    # 查询所有产品
    products = db.query(Product).all()
    print(f'\n数据库中现有的产品数量: {len(products)}')
    if products:
        print('\n现有产品列表:')
        for p in products:
            print(f'  - 父SKU: {p.parent_sku}, ID: {p.id}')
            
finally:
    db.close()
