"""
数据分析CRUD操作
提供库存趋势、销量排行、颜色分布等统计数据
"""
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database.models import ProductVariant, SaleOrder, OrderItem, Product


def get_stock_trend_data(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """
    获取库存趋势数据（最近N天）
    
    显示累计销量曲线（从0开始累加），更容易看出销售趋势
    
    Args:
        db: 数据库会话
        days: 天数，默认30天
    
    Returns:
        [{'date': '2025-11-01', 'total_stock': 15234}, ...]
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)
    
    # 获取当前总库存
    current_total = db.query(func.sum(ProductVariant.current_stock)).scalar() or 0
    
    # 查询每天的销售量
    daily_sales = db.query(
        func.date(SaleOrder.order_date).label('date'),
        func.sum(OrderItem.quantity).label('sold')
    ).join(
        OrderItem, OrderItem.order_id == SaleOrder.id
    ).filter(
        func.date(SaleOrder.order_date) >= start_date,
        func.date(SaleOrder.order_date) <= end_date
    ).group_by(
        func.date(SaleOrder.order_date)
    ).order_by('date').all()
    
    # 创建销量映射（func.date()返回字符串，需要转换为date对象）
    sales_map = {}
    for row in daily_sales:
        if isinstance(row.date, str):
            date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
        else:
            date_obj = row.date
        sales_map[date_obj] = int(row.sold)
    
    # 计算每天的库存（当前库存 - 从该天到今天的累计销量）
    result = []
    
    # 计算总销量（用于反推历史库存）
    total_sales_in_period = sum(sales_map.values())
    
    # 从开始日期往后推
    current_date = start_date
    cumulative_sales = 0
    
    while current_date <= end_date:
        # 该天的库存 = 当前库存 + (总销量 - 该天之前的累计销量)
        # 也就是：开始时库存最高，每天减去当天销量
        stock_on_date = int(current_total) + (total_sales_in_period - cumulative_sales)
        
        result.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'total_stock': stock_on_date
        })
        
        # 累加销量
        date_sales = sales_map.get(current_date, 0)
        cumulative_sales += date_sales
        
        current_date += timedelta(days=1)
    
    return result


def get_top_selling_products(db: Session, limit: int = 10, start_date=None, end_date=None, days: int = None) -> List[Dict[str, Any]]:
    """
    获取TOP N热销产品
    
    Args:
        db: 数据库会话
        limit: 返回数量，默认10
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        days: 最近N天（当start_date和end_date为None时使用）
    
    Returns:
        [{'product_code': 'P001', 'product_name': '产品A', 'total_sold': 1234}, ...]
    """
    # 通过OrderItem关联SaleOrder来筛选日期范围
    query = db.query(
        OrderItem.parent_sku.label('product_code'),
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(
        SaleOrder, SaleOrder.id == OrderItem.order_id
    )
    
    # 添加日期范围筛选
    if start_date and end_date:
        query = query.filter(
            func.date(SaleOrder.order_date) >= start_date,
            func.date(SaleOrder.order_date) <= end_date
        )
    elif days:
        # 如果没有指定日期范围，使用days参数
        end_date_calc = datetime.now().date()
        start_date_calc = end_date_calc - timedelta(days=days - 1)
        query = query.filter(
            func.date(SaleOrder.order_date) >= start_date_calc,
            func.date(SaleOrder.order_date) <= end_date_calc
        )
    
    query = query.group_by(
        OrderItem.parent_sku
    ).order_by(
        desc('total_sold')
    ).limit(limit)
    
    # 🔥 优化: 添加Product LEFT JOIN以一次获取产品名称，避免N+1查询
    subquery = query.subquery()
    result_query = db.query(
        subquery.c.product_code,
        func.coalesce(Product.name, subquery.c.product_code).label('product_name'),
        subquery.c.total_sold
    ).outerjoin(
        Product,
        Product.parent_sku == subquery.c.product_code
    )
    
    result = []
    for row in result_query.all():
        result.append({
            'product_code': row.product_code,
            'product_name': row.product_name,
            'total_sold': int(row.total_sold)
        })
    
    return result


def get_color_distribution(db: Session) -> List[Dict[str, Any]]:
    """
    获取SKU颜色销量分布
    
    Args:
        db: 数据库会话
    
    Returns:
        [{'color': '黑色', 'count': 1234, 'percentage': 35.5}, ...]
    """
    # 通过OrderItem关联ProductVariant获取颜色信息
    query = db.query(
        ProductVariant.color,
        func.sum(OrderItem.quantity).label('count')
    ).join(
        OrderItem, OrderItem.variant_sku == ProductVariant.sku
    ).filter(
        ProductVariant.color.isnot(None),
        ProductVariant.color != ''
    ).group_by(
        ProductVariant.color
    ).order_by(
        desc('count')
    )
    
    results = query.all()
    
    # 计算总数和百分比
    total_count = sum(row.count for row in results)
    
    distribution = []
    for row in results:
        percentage = (row.count / total_count * 100) if total_count > 0 else 0
        distribution.append({
            'color': row.color,
            'count': int(row.count),
            'percentage': round(percentage, 1)
        })
    
    return distribution


def get_sales_trend_data(db: Session, days: int = 30, start_date=None, end_date=None) -> List[Dict[str, Any]]:
    """
    获取销量趋势数据（最近N天或指定日期范围）
    
    Args:
        db: 数据库会话
        days: 天数，默认30天（当start_date和end_date为None时使用）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
    
    Returns:
        [{'date': '2025-11-01', 'total_sales': 234}, ...]
    """
    if start_date is None or end_date is None:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
    
    # 查询每天的销售数量（通过OrderItem关联SaleOrder）
    query = db.query(
        func.date(SaleOrder.order_date).label('date'),
        func.sum(OrderItem.quantity).label('total_sales')
    ).join(
        OrderItem, OrderItem.order_id == SaleOrder.id
    ).filter(
        func.date(SaleOrder.order_date) >= start_date,
        func.date(SaleOrder.order_date) <= end_date
    ).group_by(
        func.date(SaleOrder.order_date)
    ).order_by('date')
    
    # 创建日期映射（func.date()返回字符串，需要转换为date对象）
    sales_map = {}
    for row in query.all():
        if isinstance(row.date, str):
            date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
        else:
            date_obj = row.date
        sales_map[date_obj] = int(row.total_sales)
    
    # 填充所有日期（包括无销售的日期）
    result = []
    current_date = start_date
    
    while current_date <= end_date:
        result.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'total_sales': sales_map.get(current_date, 0)
        })
        current_date += timedelta(days=1)
    
    return result


def get_daily_order_count(db: Session, days: int = 30, start_date=None, end_date=None) -> List[Dict[str, Any]]:
    """
    获取每日订单量统计
    
    Args:
        db: 数据库会话
        days: 天数，默认30天
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
    
    Returns:
        [{'date': '2025-11-01', 'order_count': 15}, ...]
    """
    if start_date is None or end_date is None:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
    
    # 查询每天的订单数量
    query = db.query(
        func.date(SaleOrder.order_date).label('date'),
        func.count(SaleOrder.id).label('order_count')
    ).filter(
        func.date(SaleOrder.order_date) >= start_date,
        func.date(SaleOrder.order_date) <= end_date
    ).group_by(
        func.date(SaleOrder.order_date)
    ).order_by('date')
    
    # 创建日期映射
    order_map = {}
    for row in query.all():
        if isinstance(row.date, str):
            date_obj = datetime.strptime(row.date, '%Y-%m-%d').date()
        else:
            date_obj = row.date
        order_map[date_obj] = int(row.order_count)
    
    # 填充所有日期（包括无订单的日期）
    result = []
    current_date = start_date
    
    while current_date <= end_date:
        result.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'order_count': order_map.get(current_date, 0)
        })
        current_date += timedelta(days=1)
    
    return result


def get_multi_item_order_stats(db: Session, days: int = 30, start_date=None, end_date=None) -> List[Dict[str, Any]]:
    """
    获取多件订单统计（按订单中的商品件数分组）
    
    Args:
        db: 数据库会话
        days: 天数，默认30天
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
    
    Returns:
        [
            {'item_count': 1, 'order_count': 50, 'label': '1件'},
            {'item_count': 2, 'order_count': 30, 'label': '2件'},
            ...
        ]
    """
    if start_date is None or end_date is None:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)
    
    # 子查询：计算每个订单的总件数
    subquery = db.query(
        SaleOrder.id.label('order_id'),
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(
        OrderItem, OrderItem.order_id == SaleOrder.id
    ).filter(
        func.date(SaleOrder.order_date) >= start_date,
        func.date(SaleOrder.order_date) <= end_date
    ).group_by(
        SaleOrder.id
    ).subquery()
    
    # 主查询：按件数分组统计订单数量
    query = db.query(
        subquery.c.total_quantity.label('item_count'),
        func.count(subquery.c.order_id).label('order_count')
    ).group_by(
        subquery.c.total_quantity
    ).order_by('item_count')
    
    result = []
    for row in query.all():
        item_count = int(row.item_count)
        result.append({
            'item_count': item_count,
            'order_count': int(row.order_count),
            'label': f'{item_count}件'
        })
    
    return result
