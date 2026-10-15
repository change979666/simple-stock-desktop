from datetime import datetime, timedelta
from sqlalchemy import func
from database.models import ProductVariant, StockLog

def get_inventory_stats(session, period):
    """获取指定周期的库存统计数据"""
    # 确定时间范围
    now = datetime.now()
    if period == '今日':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == '本周':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == '本月':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == '本季度':
        month = (now.month - 1) // 3 * 3 + 1
        start_date = now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # 本年
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 获取基础统计数据
    inventory_query = session.query(Inventory)
    total_value = sum(item.quantity * item.unit_price for item in inventory_query.all())
    total_products = inventory_query.count()
    low_stock_count = inventory_query.filter(Inventory.status == InventoryStatus.LOW_STOCK).count()
    out_of_stock_count = inventory_query.filter(Inventory.status == InventoryStatus.OUT_OF_STOCK).count()
    
    # 获取状态分布
    status_distribution = {}
    for status in InventoryStatus:
        count = inventory_query.filter(Inventory.status == status).count()
        if count > 0:
            status_info = InventoryStatus.get_display_info(status)
            status_distribution[status_info[0]] = count
    
    # 获取详细数据
    detailed_data = []
    inventory_items = inventory_query.all()
    for item in inventory_items:
        # 获取最近一次变动记录
        last_log = session.query(InventoryLog)\
            .filter(InventoryLog.inventory_id == item.id)\
            .order_by(InventoryLog.created_at.desc())\
            .first()
        
        last_change = last_log.created_at.strftime('%Y-%m-%d %H:%M') if last_log else '无记录'
        
        detailed_data.append({
            'code': item.code,
            'name': item.name,
            'quantity': item.quantity,
            'status': item.status,
            'last_change': last_change,
            'value': item.quantity * item.unit_price
        })
    
    return {
        'total_value': total_value,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'status_distribution': status_distribution,
        'detailed_data': detailed_data
    }

def get_inventory_history(session, period):
    """获取指定周期的库存历史数据"""
    # 确定时间范围（与上面相同的逻辑）
    now = datetime.now()
    if period == '今日':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        group_by = func.date_trunc('hour', InventoryLog.created_at)
    elif period == '本周':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        group_by = func.date_trunc('day', InventoryLog.created_at)
    elif period == '本月':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = func.date_trunc('day', InventoryLog.created_at)
    elif period == '本季度':
        month = (now.month - 1) // 3 * 3 + 1
        start_date = now.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = func.date_trunc('week', InventoryLog.created_at)
    else:  # 本年
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        group_by = func.date_trunc('month', InventoryLog.created_at)
    
    # 计算每个时间点的库存总值
    history_data = session.query(
        group_by.label('date'),
        func.sum(InventoryLog.quantity * Inventory.unit_price).label('total_value')
    ).join(Inventory)\
     .filter(InventoryLog.created_at >= start_date)\
     .group_by(group_by)\
     .order_by(group_by)\
     .all()
    
    return {
        'date': [item.date for item in history_data],
        'total_value': [float(item.total_value or 0) for item in history_data]
    }