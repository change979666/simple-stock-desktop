"""快速创建测试数据"""
from database.session import SessionLocal
from database.models import Product, ProductVariant
from crud.operations import create_action_log
from datetime import datetime

def create_test_data():
    """创建测试数据"""
    db = SessionLocal()
    
    try:
        print("创建测试数据...")
        
        operator_info = {
            'username': 'admin',
            'display': '管理员'
        }
        
        # 创建测试产品
        products_data = [
            {
                'parent_sku': 'PROD-001',
                'name': '测试产品1',
                'variants': [
                    {'sku': 'SKU-001', 'option': '红色-L', 'price': 99.0},
                    {'sku': 'SKU-002', 'option': '蓝色-L', 'price': 99.0},
                ]
            },
            {
                'parent_sku': 'PROD-002',
                'name': '测试产品2',
                'variants': [
                    {'sku': 'SKU-003', 'option': '黑色-M', 'price': 129.0},
                    {'sku': 'SKU-004', 'option': '白色-M', 'price': 129.0},
                ]
            },
            {
                'parent_sku': 'PROD-003',
                'name': '测试产品3',
                'variants': [
                    {'sku': 'SKU-005', 'option': '绿色-S', 'price': 89.0},
                ]
            }
        ]
        
        for prod_data in products_data:
            product = Product(
                parent_sku=prod_data['parent_sku'],
                name=prod_data['name']
            )
            db.add(product)
            db.flush()
            
            for var_data in prod_data['variants']:
                variant = ProductVariant(
                    product_id=product.id,
                    sku=var_data['sku'],
                    option=var_data['option'],
                    price=var_data['price'],
                    current_stock=0
                )
                db.add(variant)
            
            print(f"✓ 创建产品: {prod_data['name']}")
        
        db.commit()
        
        # 添加初始库存
        from crud.operations import create_stock_log, get_variant_by_sku
        
        initial_stocks = [
            ('SKU-001', 100),
            ('SKU-002', 150),
            ('SKU-003', 80),
            ('SKU-004', 120),
            ('SKU-005', 200),
        ]
        
        for sku, quantity in initial_stocks:
            variant = get_variant_by_sku(db, sku)
            if variant:
                create_stock_log(
                    db,
                    variant_id=variant.id,
                    change_quantity=quantity,
                    notes='初始库存',
                    operator_info=operator_info
                )
                print(f"✓ 添加库存: {sku} = {quantity}")
        
        db.commit()
        
        # 记录操作日志
        create_action_log(
            db,
            operator_info,
            '初始化测试数据: 5个产品, 5个变体, 初始库存'
        )
        
        print("\n✅ 测试数据创建完成!")
        print(f"   产品数: {db.query(Product).count()}")
        print(f"   变体数: {db.query(ProductVariant).count()}")
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    create_test_data()
