"""
清空数据库并生成测试数据
包含：20条产品、库存记录、销售记录、发货记录
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import random
from database.session import SessionLocal, engine, Base
from database.models import (
    Category, Product, ProductVariant, StockLog,
    InventoryShipment, ShipmentItem, ActionLog
)
from database.models.sale_order import SaleOrder, OrderItem
from database.inventory import ShipmentStatus
from sqlalchemy import text


def init_database():
    """初始化数据库表结构"""
    print("=" * 60)
    print("初始化数据库表结构...")
    print("=" * 60)
    Base.metadata.create_all(bind=engine)
    print("  ✓ 数据库表结构创建完成\n")


def clear_all_data(session):
    """清空所有业务数据"""
    print("=" * 60)
    print("清空数据库...")
    print("=" * 60)
    
    # 删除所有表的数据
    tables = [
        'action_logs',
        'inventory_transit_logs',
        'shipment_items',
        'inventory_shipments',
        'order_items',
        'sale_orders',
        'sale_records',
        'stock_logs',
        'product_variants',
        'products',
        'categories'
    ]
    
    for table in tables:
        try:
            session.execute(text(f'DELETE FROM {table}'))
            count = session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
            print(f"  ✓ {table}: {count} 条记录")
        except Exception as e:
            print(f"  ✗ {table}: {str(e)}")
    
    session.commit()
    print("\n数据清理完成!\n")


def create_categories(session):
    """创建产品分类"""
    print("创建产品分类...")
    categories_data = [
        {'name': '服装配饰'},
        {'name': '家居用品'},
        {'name': '电子配件'},
        {'name': '文具用品'}
    ]
    
    categories = []
    for data in categories_data:
        category = Category(**data)
        session.add(category)
        categories.append(category)
    
    session.commit()
    print(f"  ✓ 创建了 {len(categories)} 个分类")
    return categories


def create_products_and_variants(session, categories):
    """创建20个产品和SKU变体"""
    print("\n创建产品和SKU...")
    
    # 产品模板
    product_templates = [
        # 服装配饰 (分类0)
        {'name': '羊绒围巾', 'parent_sku': 'SC', 'category_idx': 0, 
         'options': ['黑色', '驼色', '灰色', '米白'],
         'base_price': 89.00},
        {'name': '棉质帽子', 'parent_sku': 'HAT', 'category_idx': 0,
         'options': ['黑色', '深蓝', '卡其', '浅灰'],
         'base_price': 45.00},
        {'name': '真丝丝巾', 'parent_sku': 'SILK', 'category_idx': 0,
         'options': ['红色', '蓝色', '绿色', '紫色'],
         'base_price': 128.00},
        {'name': '针织手套', 'parent_sku': 'GLV', 'category_idx': 0,
         'options': ['黑色', '灰色', '米色'],
         'base_price': 35.00},
        {'name': '羊毛披肩', 'parent_sku': 'SHW', 'category_idx': 0,
         'options': ['驼色', '灰色', '酒红'],
         'base_price': 168.00},
        
        # 家居用品 (分类1)
        {'name': '陶瓷马克杯', 'parent_sku': 'MUG', 'category_idx': 1,
         'options': ['300ml', '400ml', '500ml'],
         'base_price': 25.00},
        {'name': '纯棉毛巾', 'parent_sku': 'TWL', 'category_idx': 1,
         'options': ['蓝色', '粉色', '白色', '灰色'],
         'base_price': 18.00},
        {'name': '保温杯', 'parent_sku': 'THM', 'category_idx': 1,
         'options': ['350ml', '500ml', '750ml'],
         'base_price': 68.00},
        {'name': '床上四件套', 'parent_sku': 'BED', 'category_idx': 1,
         'options': ['浅蓝', '淡粉', '米白', '深灰'],
         'base_price': 298.00},
        {'name': '浴巾', 'parent_sku': 'BTW', 'category_idx': 1,
         'options': ['白色', '蓝色', '灰色'],
         'base_price': 45.00},
        
        # 电子配件 (分类2)
        {'name': 'Type-C数据线', 'parent_sku': 'USBC', 'category_idx': 2,
         'options': ['1米', '1.5米', '2米'],
         'base_price': 15.00},
        {'name': '无线充电器', 'parent_sku': 'WCHG', 'category_idx': 2,
         'options': ['10W', '15W', '20W'],
         'base_price': 58.00},
        {'name': '蓝牙耳机', 'parent_sku': 'BTE', 'category_idx': 2,
         'options': ['黑色', '白色', '粉色'],
         'base_price': 128.00},
        {'name': '手机支架', 'parent_sku': 'PHS', 'category_idx': 2,
         'options': ['桌面款', '车载款', '床头款'],
         'base_price': 28.00},
        {'name': '移动电源', 'parent_sku': 'PWB', 'category_idx': 2,
         'options': ['10000mAh', '20000mAh', '30000mAh'],
         'base_price': 88.00},
        
        # 文具用品 (分类3)
        {'name': 'A5笔记本', 'parent_sku': 'NB', 'category_idx': 3,
         'options': ['横线', '方格', '空白'],
         'base_price': 12.00},
        {'name': '中性笔', 'parent_sku': 'PEN', 'category_idx': 3,
         'options': ['黑色', '蓝色', '红色', '彩色'],
         'base_price': 3.00},
        {'name': '便利贴', 'parent_sku': 'STK', 'category_idx': 3,
         'options': ['黄色', '粉色', '蓝色', '绿色'],
         'base_price': 8.00},
        {'name': '文件夹', 'parent_sku': 'FLD', 'category_idx': 3,
         'options': ['A4', 'A5', 'B5'],
         'base_price': 6.00},
        {'name': '荧光笔', 'parent_sku': 'HLT', 'category_idx': 3,
         'options': ['黄色', '绿色', '粉色', '橙色'],
         'base_price': 5.00},
    ]
    
    all_variants = []
    
    for template in product_templates:
        # 创建父产品
        product = Product(
            name=template['name'],
            parent_sku=template['parent_sku'],
            category_id=categories[template['category_idx']].id,
            description=f"{template['name']}，多种规格可选",
            created_at=datetime.now()
        )
        session.add(product)
        session.flush()
        
        # 创建SKU变体
        for idx, option in enumerate(template['options'], 1):
            sku = f"{template['parent_sku']}-{idx:02d}"
            cost_price = template['base_price'] * random.uniform(0.4, 0.6)
            
            variant = ProductVariant(
                product_id=product.id,
                sku=sku,
                option_name=option,
                cost_price=round(cost_price, 2)
            )
            session.add(variant)
            all_variants.append(variant)
    
    session.commit()
    print(f"  ✓ 创建了 {len(product_templates)} 个产品")
    print(f"  ✓ 创建了 {len(all_variants)} 个SKU变体")
    return all_variants


def create_stock_logs(session, variants):
    """创建库存记录"""
    print("\n创建库存记录...")
    
    operators = ['张三', '李四', '王五', '赵六']
    stock_logs = []
    
    for variant in variants:
        # 每个SKU创建2-5条入库记录
        num_logs = random.randint(2, 5)
        for i in range(num_logs):
            days_ago = random.randint(1, 60)
            created_at = datetime.now() - timedelta(days=days_ago)
            
            # 随机入库数量
            quantity = random.choice([50, 100, 150, 200, 250, 300])
            
            log = StockLog(
                variant_id=variant.id,
                change_quantity=quantity,
                notes=f"采购入库-批次{random.randint(1000, 9999)}",
                operator_info=f"{random.choice(operators)} (192.168.1.{random.randint(10, 200)})",
                created_at=created_at
            )
            session.add(log)
            stock_logs.append(log)
        
        # 添加一些出库记录（销售出库）
        num_out = random.randint(1, 3)
        for i in range(num_out):
            days_ago = random.randint(1, 30)
            created_at = datetime.now() - timedelta(days=days_ago)
            
            quantity = -random.choice([10, 20, 30, 40, 50])
            
            log = StockLog(
                variant_id=variant.id,
                change_quantity=quantity,
                notes=f"销售出库",
                operator_info=f"{random.choice(operators)} (192.168.1.{random.randint(10, 200)})",
                created_at=created_at
            )
            session.add(log)
            stock_logs.append(log)
    
    session.commit()
    print(f"  ✓ 创建了 {len(stock_logs)} 条库存记录")
    return stock_logs


def create_sales(session, variants):
    """创建销售订单数据（使用SaleOrder模型）"""
    print("\n创建销售订单...")
    
    customers = ['客户A', '客户B', '客户C', '客户D', '客户E', '客户F', 
                 '张先生', '李女士', '王总', '赵经理', '陈老板', '刘总']
    
    orders = []
    
    # 创建100个订单
    for i in range(100):
        days_ago = random.randint(1, 60)
        order_date = datetime.now() - timedelta(days=days_ago)
        
        # 创建唯一的订单号（使用循环计数器避免重复）
        order_number = f"ORD{order_date.strftime('%Y%m%d')}{i:04d}"
        
        # 创建订单
        order = SaleOrder(
            order_number=order_number,
            customer_name=random.choice(customers),
            order_date=order_date,
            total_amount=0  # 先设为0，后面计算
        )
        session.add(order)
        session.flush()  # 获取订单ID
        
        # 为每个订单添加1-5个商品
        num_items = random.randint(1, 5)
        selected_variants = random.sample(variants, min(num_items, len(variants)))
        
        total_amount = 0
        for variant in selected_variants:
            quantity = random.randint(1, 10)
            
            # 计算单价（成本价的1.5-2.5倍）
            item_price = variant.cost_price * random.uniform(1.5, 2.5) * quantity
            total_amount += item_price
            
            order_item = OrderItem(
                order_id=order.id,
                parent_sku=variant.product.parent_sku,
                variant_sku=variant.sku,
                quantity=quantity,
                item_price=round(item_price, 2)
            )
            session.add(order_item)
        
        # 更新订单总金额
        order.total_amount = round(total_amount, 2)
        orders.append(order)
    
    session.commit()
    print(f"  ✓ 创建了 {len(orders)} 个订单")
    
    # 统计订单明细数量
    total_items = session.query(OrderItem).count()
    print(f"  ✓ 创建了 {total_items} 条订单明细")
    
    return orders


def create_shipments(session, variants):
    """创建发货记录"""
    print("\n创建发货记录...")
    
    operators = ['张三', '李四', '王五', '赵六']
    shipments = []
    
    # 创建20条发货单
    for i in range(20):
        days_ago = random.randint(1, 60)
        created_at = datetime.now() - timedelta(days=days_ago)
        
        # 随机选择状态
        status_choices = list(ShipmentStatus)
        status = random.choice(status_choices)
        
        # 预计到达日期
        estimated_arrival = created_at + timedelta(days=random.randint(7, 30))
        
        # 如果已到达或已上架，设置实际到达日期
        arrival_date = None
        if status in [ShipmentStatus.ARRIVED, ShipmentStatus.SHELVED]:
            arrival_date = created_at + timedelta(days=random.randint(7, 20))
        
        shipment = InventoryShipment(
            batch_number=f"SHIP{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}",
            status=status,
            estimated_arrival=estimated_arrival,
            arrival_date=arrival_date,
            operator=random.choice(operators),
            created_at=created_at,
            updated_at=created_at,
            notes=f"第{i+1}批次发货"
        )
        session.add(shipment)
        session.flush()
        
        # 为每个发货单添加2-5个SKU
        num_items = random.randint(2, 5)
        selected_variants = random.sample(variants, min(num_items, len(variants)))
        
        for variant in selected_variants:
            quantity = random.choice([100, 200, 300, 500])
            
            item = ShipmentItem(
                shipment_id=shipment.id,
                variant_id=variant.id,
                quantity=quantity,
                tracking_number=f"TRK{random.randint(1000000000, 9999999999)}"
            )
            session.add(item)
        
        shipments.append(shipment)
    
    session.commit()
    print(f"  ✓ 创建了 {len(shipments)} 条发货记录")
    return shipments


def create_action_logs(session):
    """创建操作日志"""
    print("\n创建操作日志...")
    
    operators = ['张三', '李四', '王五', '赵六']
    actions = [
        '创建产品：{}',
        '编辑产品：{}',
        '删除产品：{}',
        '导入产品：成功导入{}个SKU',
        '导入库存：成功导入{}条记录',
        '导入销售：成功导入{}条记录',
        '数据库备份：备份成功',
        '系统设置：修改库存预警阈值',
    ]
    
    logs = []
    
    for i in range(30):
        days_ago = random.randint(1, 60)
        created_at = datetime.now() - timedelta(days=days_ago)
        
        action_template = random.choice(actions)
        if '{}' in action_template:
            action = action_template.format(random.randint(1, 20))
        else:
            action = action_template
        
        log = ActionLog(
            action=action,
            operator_info=f"{random.choice(operators)} (192.168.1.{random.randint(10, 200)})",
            created_at=created_at
        )
        session.add(log)
        logs.append(log)
    
    session.commit()
    print(f"  ✓ 创建了 {len(logs)} 条操作日志")
    return logs


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据库重置和测试数据生成工具")
    print("=" * 60 + "\n")
    
    # 初始化数据库
    init_database()
    
    session = SessionLocal()
    
    try:
        # 1. 清空数据
        clear_all_data(session)
        
        # 2. 创建分类
        categories = create_categories(session)
        
        # 3. 创建产品和变体
        variants = create_products_and_variants(session, categories)
        
        # 4. 创建库存记录
        create_stock_logs(session, variants)
        
        # 5. 创建销售记录
        create_sales(session, variants)
        
        # 6. 创建发货记录
        create_shipments(session, variants)
        
        # 7. 创建操作日志
        create_action_logs(session)
        
        print("\n" + "=" * 60)
        print("✓ 测试数据生成完成!")
        print("=" * 60)
        print("\n数据统计:")
        print(f"  - 产品分类: {len(categories)} 个")
        print(f"  - 产品: 20 个")
        print(f"  - SKU变体: {len(variants)} 个")
        print(f"  - 库存记录: {session.query(StockLog).count()} 条")
        print(f"  - 销售订单: {session.query(SaleOrder).count()} 个")
        print(f"  - 订单明细: {session.query(OrderItem).count()} 条")
        print(f"  - 发货单: {session.query(InventoryShipment).count()} 条")
        print(f"  - 操作日志: {session.query(ActionLog).count()} 条")
        print("\n可以启动程序查看测试数据了！\n")
        
    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
