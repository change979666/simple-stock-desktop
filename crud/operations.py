import json
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import re

from database.models import (
    Category, Product, ProductVariant,
    StockLog, ActionLog
)

# 导入发货操作（向后兼容）
from crud.shipment_operations import get_all_shipments

# 导入数据变更跟踪器
from utils.data_change_tracker import mark_data_changed


def natural_sort_key(text: str) -> list:
    """自然排序键函数：将字符串中的数字部分转为整数
    
    示例:
        'SKU10' -> ['SKU', 10, '']
        'SKU2' -> ['SKU', 2, '']
        'BD55-104' -> ['BD', 55, '-', 104, '']
    
    这样排序结果就是：SKU2, SKU10, SKU100（而不是SKU10, SKU100, SKU2）
    """
    if not text:
        return ['']
    
    # 将文本分割为数字和非数字部分
    parts = re.split(r'(\d+)', str(text))
    
    # 将数字部分转为整数，其他保持字符串
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part)
    
    return result


def create_product(db: Session, parent_sku: str) -> Product:
    """创建新的父产品，如果已存在则直接返回
    
    Args:
        db: 数据库会话
        parent_sku: 父产品SKU
        
    Returns:
        Product: 产品对象
        
    Raises:
        ValueError: 当输入参数无效时
        RuntimeError: 当数据库操作失败时
    """
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError
    
    if not parent_sku or not parent_sku.strip():
        raise ValueError("产品SKU不能为空")
    
    try:
        # 先检查是否已存在
        existing_product = get_product_by_sku(db, parent_sku)
        if existing_product:
            return existing_product
            
        # 不存在则创建新的
        product = Product(
            parent_sku=parent_sku,
            name=parent_sku,  # 使用parent_sku作为产品名称
            category_id=1,    # 使用默认分类ID
            stock_warning_level=None  # 不再使用产品级别预警，使用全局设置
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # 标记数据已变更
        mark_data_changed(f"create_product: {parent_sku}")
        
        return product
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"产品SKU已存在或违反数据库约束: {parent_sku}")
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"数据库操作失败: {str(e)}")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"创建产品时发生未知错误: {str(e)}")


def create_product_variant(
    db: Session, product_id: int, sku: str,
    option_name: str, cost_price: float
) -> ProductVariant:
    """创建新的产品变体，如果已存在则返回已有的变体
    
    Args:
        db: 数据库会话
        product_id: 父产品ID
        sku: 产品变体SKU
        option_name: 选项名称
        cost_price: 成本价格
        
    Returns:
        ProductVariant: 产品变体对象
        
    Raises:
        ValueError: 当输入参数无效时
        RuntimeError: 当数据库操作失败时
    """
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError
    
    if not sku or not sku.strip():
        raise ValueError("产品SKU不能为空")
    if cost_price < 0:
        raise ValueError("成本价格不能为负数")
    
    try:
        # 先检查是否已存在
        existing_variant = get_variant_by_sku(db, sku)
        if existing_variant:
            # 如果需要更新成本价，则更新它
            if existing_variant.cost_price != cost_price:
                existing_variant.cost_price = cost_price
                db.commit()
                db.refresh(existing_variant)
            return existing_variant
        
        # 不存在则创建新的
        variant = ProductVariant(
            product_id=product_id,
            sku=sku,
            option_name=option_name,
            cost_price=cost_price
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        
        # 标记数据已变更
        mark_data_changed(f"create_variant: {sku}")
        
        return variant
    except IntegrityError:
        db.rollback()
        raise ValueError(f"产品变体SKU已存在: {sku}")
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"数据库操作失败: {str(e)}")
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"创建产品变体时发生未知错误: {str(e)}")


def get_product(db: Session, product_id: int) -> Optional[Product]:
    """通过ID获取产品"""
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_sku(db: Session, parent_sku: str) -> Optional[Product]:
    """通过父SKU获取产品"""
    return db.query(Product).filter(Product.parent_sku == parent_sku).first()


def get_variant(db: Session, variant_id: int) -> Optional[ProductVariant]:
    """通过ID获取产品变体"""
    return db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()


def get_variant_by_sku(db: Session, sku: str) -> Optional[ProductVariant]:
    """通过SKU获取产品变体(大小写不敏感)"""
    from sqlalchemy import func
    return db.query(ProductVariant).filter(
        func.lower(ProductVariant.sku) == sku.lower()
    ).first()


def get_all_products(db: Session) -> List[Product]:
    """获取所有产品及其关联数据（库存直接从 current_stock 读取）"""
    # 主查询：获取产品和变体信息
    products = (
        db.query(Product)
        .options(
            joinedload(Product.variants)
        )
        .all()
    )
    
    # 🔧 使用自然排序（正确处理SKU中的数字）
    products = sorted(
        products,
        key=lambda p: natural_sort_key(p.parent_sku)
    )
    
    # current_stock 字段已经包含库存数量，无需额外计算
    
    return products


def get_products_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    category_id: Optional[int] = None
) -> tuple[List[Product], int]:
    """分页获取产品列表
    
    Args:
        db: 数据库会话
        page: 页码（从1开始）
        page_size: 每页数量
        search: 搜索关键词（匹配产品名称或SKU）
        category_id: 分类ID筛选
    
    Returns:
        (products, total): 产品列表和总数
    """
    # 构建基础查询
    query = db.query(Product).options(
        joinedload(Product.variants)
    )
    
    # 应用搜索过滤
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Product.parent_sku.ilike(search_pattern)) |
            (Product.name.ilike(search_pattern))
        )
    
    # 应用分类过滤
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    
    # 获取总数（在分页前）
    total = query.count()
    
    # 先获取数据（不在数据库层排序）
    products = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # 🔧 在Python层进行自然排序（正确处理数字）
    products = sorted(
        products,
        key=lambda p: natural_sort_key(p.parent_sku)
    )
    
    return products, total


def update_product(
    db: Session, product_id: int,
    stock_warning_level: Optional[int] = None
) -> Optional[Product]:
    """更新产品信息"""
    product = get_product(db, product_id)
    if product:
        if stock_warning_level:
            product.stock_warning_level = stock_warning_level
        db.commit()
        db.refresh(product)
        
        # 标记数据已变更
        mark_data_changed(f"update_product: {product.parent_sku}")
    return product


def update_variant_cost_price(
    db: Session, variant_id: int,
    new_cost_price: float
) -> Optional[ProductVariant]:
    """更新产品变体的成本价"""
    try:
        variant = get_variant(db, variant_id)
        if variant:
            variant.cost_price = new_cost_price
            db.commit()
            db.refresh(variant)
            
            # 记录修改日志
            create_action_log(
                db,
                operator_info={'display': '系统'},
                action=f'更新SKU {variant.sku} 的成本价为 {new_cost_price}'  
                # 这里参数名不用改，因为函数定义里会处理
            )
            
            # 标记数据已变更
            mark_data_changed(f"update_cost_price: {variant.sku}")
            
        return variant
    except Exception as e:
        db.rollback()
        raise Exception(f'更新成本价失败: {str(e)}')


def delete_product(db: Session, product_id: int) -> bool:
    """删除产品及其所有变体，包括相关的库存记录"""
    try:
        product = get_product(db, product_id)
        if not product:
            return False
            
        # 先删除与变体相关的记录
        for variant in product.variants:
            # 删除库存记录
            db.query(StockLog).filter(
                StockLog.variant_id == variant.id
            ).delete(synchronize_session=False)
            
            # 删除销售记录（如果有的话）
            from database.models.sale_order import OrderItem
            db.query(OrderItem).filter(
                OrderItem.variant_sku == variant.sku
            ).delete(synchronize_session=False)
            
            # 删除变体
            db.delete(variant)
        
        # 最后删除产品本身
        parent_sku = product.parent_sku
        db.delete(product)
        db.commit()
        
        # 标记数据已变更
        mark_data_changed(f"delete_product: {parent_sku}")
        
        return True
        
    except Exception as e:
        db.rollback()
        raise Exception(f'删除产品失败: {str(e)}')


def create_stock_log(
    db: Session, variant_id: int,
    change_quantity: int, notes: str,
    operator_info: dict,
    allow_negative: bool = True  # v2.1.1: 默认允许负库存（超卖）
) -> StockLog:
    """创建库存变更日志 - 同时更新 current_stock 和 StockLog
    
    Args:
        allow_negative: 是否允许负库存，默认True（允许超卖）
    """
    try:
        # 获取产品变体
        variant = get_variant(db, variant_id)
        if not variant:
            raise ValueError(f"产品变体 ID {variant_id} 不存在")
        
        # 获取当前库存（使用 current_stock 字段，更快）
        current_stock = variant.current_stock
        
        # 如果是出库操作，检查库存是否足够
        if change_quantity < 0 and current_stock + change_quantity < 0:
            if not allow_negative:
                raise ValueError(
                    f'库存不足，当前库存: {current_stock}, '
                    f'需要出库: {abs(change_quantity)}'
                )
            # 允许负库存时，在备注中添加超卖标记
            oversell_info = (
                f' [超卖: 库存{current_stock}, '
                f'出库{abs(change_quantity)}]'
            )
            notes = f'{notes}{oversell_info}'
        
        # 1. 更新 current_stock（直接存储的库存数量）
        variant.current_stock += change_quantity
        
        # 2. 创建 StockLog（历史记录）
        stock_log = StockLog(
            variant_id=variant_id,
            change_quantity=change_quantity,
            notes=notes,
            operator_info=operator_info.get('display', str(operator_info))
        )
        
        # 创建操作日志
        operation_type = "入库" if change_quantity > 0 else "出库"
        action_message = (
            f"{operation_type}: SKU {variant.sku}, "
            f"数量 {abs(change_quantity)}, "
            f"备注: {notes if notes else '无'}"
        )
        
        action_log = create_action_log(
            db,
            operator_info,
            action_message
        )
        
        db.add(stock_log)
        db.flush()  # 刷新到数据库但不提交，让外层控制事务
        
        # 标记数据已变更（库存变更是高频操作）
        mark_data_changed(f"stock_change: {variant.sku} {change_quantity:+d}")
        
        return stock_log
        
    except Exception as e:
        raise Exception(f'库存修改失败: {str(e)}')


def get_product_stock_level(db: Session, variant_id: int) -> int:
    """获取产品变体的当前库存（直接从 current_stock 字段读取）"""
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    
    if not variant:
        return 0
    
    return variant.current_stock


def create_action_log(
    db: Session,
    operator_info,  # Union[dict, str]
    action: str
) -> ActionLog:
    """创建操作日志, 增强对 operator_info 的解析
    
    优先级：
    1. 如果有 display 字段，直接使用
    2. 如果有 nickname/operator_name，显示为 "昵称 (IP)"
    3. 如果昵称为空但有 IP，只显示 IP
    4. 如果都没有，显示"未知操作员"
    """
    operator_display = "未知操作员"
    
    try:
        # 尝试解析JSON字符串
        if isinstance(operator_info, str):
            try:
                # 替换单引号为双引号以符合JSON格式
                if "'" in operator_info:
                    operator_info = operator_info.replace("'", '"')
                info_dict = json.loads(operator_info)
                if isinstance(info_dict, dict):
                    operator_info = info_dict
            except (json.JSONDecodeError, TypeError):
                # 如果解析失败，直接使用字符串
                if operator_info and operator_info.strip():
                    operator_display = operator_info

        if isinstance(operator_info, dict):
            # 1. 优先使用 display 字段
            if 'display' in operator_info and operator_info.get('display'):
                operator_display = operator_info['display']
            else:
                # 2. 尝试从 nickname 或 operator_name 构建
                name = (
                    operator_info.get('nickname', '') or
                    operator_info.get('operator_name', '')
                ).strip()
                ip = operator_info.get('ip_address', '').strip()
                
                # 3. 如果有昵称，显示 "昵称 (IP)" 或 "昵称"
                if name:
                    operator_display = f"{name} ({ip})" if ip else name
                # 4. 如果没有昵称但有 IP，只显示 IP
                elif ip:
                    operator_display = ip
                # 5. 如果都没有，尝试转换整个字典
                else:
                    operator_display = str(operator_info)
        elif isinstance(operator_info, str) and operator_info:
            operator_display = operator_info

    except Exception:
        # 保证即使解析出错, 也能记录日志
        operator_display = str(operator_info) if operator_info else "解析异常"

    action_log = ActionLog(
        operator_info=operator_display,
        action=action
    )
    db.add(action_log)
    db.flush()  # 只刷新，不提交，让外层控制事务
    return action_log


def get_daily_sales_stats(db: Session, date: datetime) -> dict:
    """获取指定日期的销售统计 - 使用SaleOrder表"""
    from database.models.sale_order import SaleOrder
    
    start_of_day = datetime(date.year, date.month, date.day)
    end_of_day = datetime(date.year, date.month, date.day, 23, 59, 59)
    
    # 查询指定日期的订单
    orders = db.query(SaleOrder).filter(
        SaleOrder.order_date >= start_of_day,
        SaleOrder.order_date <= end_of_day
    ).all()
    
    total_sales = sum(
        float(order.total_amount) if order.total_amount else 0
        for order in orders
    )
    total_orders = len(orders)
    
    return {
        'period': {'start': start_of_day, 'end': end_of_day},
        'date': start_of_day.date(),
        'total_sales': total_sales,
        'total_orders': total_orders,
        'orders': orders
    }


def get_yesterday_stats(db: Session) -> dict:
    """获取昨日销售统计"""
    yesterday = datetime.now() - timedelta(days=1)
    return get_daily_sales_stats(db, yesterday)


def get_period_sales_stats(
    db: Session, start_date: datetime, end_date: datetime
) -> dict:
    """获取指定时间范围内的销售统计 - 使用SaleOrder表"""
    from database.models.sale_order import SaleOrder
    
    orders = db.query(SaleOrder).filter(
        SaleOrder.order_date >= start_date,
        SaleOrder.order_date <= end_date
    ).all()
    
    total_sales = sum(
        float(order.total_amount) if order.total_amount else 0
        for order in orders
    )
    total_orders = len(orders)
    
    return {
        'period': {'start': start_date, 'end': end_date},
        'total_sales': total_sales,
        'total_orders': total_orders,
        'orders': orders
    }


def get_last_week_stats(db: Session) -> dict:
    """获取最近7天销售统计"""
    today = datetime.now()
    today = datetime(today.year, today.month, today.day, 23, 59, 59)
    week_ago = today - timedelta(days=7)
    week_ago = datetime(
        week_ago.year, week_ago.month, week_ago.day
    )
    return get_period_sales_stats(db, week_ago, today)


def get_last_month_stats(db: Session) -> dict:
    """获取最近30天销售统计"""
    today = datetime.now()
    today = datetime(today.year, today.month, today.day, 23, 59, 59)
    month_ago = today - timedelta(days=30)
    month_ago = datetime(
        month_ago.year, month_ago.month, month_ago.day
    )
    return get_period_sales_stats(db, month_ago, today)


def get_sku_sales_stats(
    db: Session, variant_id: int,
    start_date: datetime, end_date: datetime
) -> dict:
    """获取指定SKU在给定时间范围内的销售统计 - 使用SaleOrder和OrderItem表"""
    from database.models.sale_order import SaleOrder, OrderItem
    from database.models.product import ProductVariant
    
    # 获取变体的SKU
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        return {
            'period': {'start': start_date, 'end': end_date},
            'total_sales': 0,
            'total_quantity': 0,
            'total_orders': 0,
            'orders': []
        }
    
    # 查询包含指定SKU的订单
    orders_with_items = (
        db.query(SaleOrder)
        .join(OrderItem, SaleOrder.id == OrderItem.order_id)
        .filter(
            SaleOrder.order_date >= start_date,
            SaleOrder.order_date <= end_date,
            OrderItem.variant_sku == variant.sku
        )
        .all()
    )
    
    # 计算统计数据
    total_quantity = 0
    total_sales = 0
    order_items = []
    
    for order in orders_with_items:
        # 获取该订单中匹配的商品项
        for item in order.items:
            if item.variant_sku == variant.sku:
                total_quantity += item.quantity
                total_sales += float(item.item_price) * item.quantity
                order_items.append(item)
    
    return {
        'period': {'start': start_date, 'end': end_date},
        'total_sales': total_sales,
        'total_quantity': total_quantity,
        'total_orders': len(orders_with_items),
        'orders': order_items
    }


def get_sku_recent_sales(
    db: Session, variant_id: int
) -> dict:
    """获取指定SKU的各时间段销售数据"""
    today = datetime.now()
    today = datetime(today.year, today.month, today.day)
    
    # 今日数据
    today_end = today.replace(hour=23, minute=59, second=59)
    today_stats = get_sku_sales_stats(db, variant_id, today, today_end)
    
    # 昨日数据
    yesterday = today - timedelta(days=1)
    yesterday_end = yesterday.replace(hour=23, minute=59, second=59)
    yesterday_stats = get_sku_sales_stats(
        db, variant_id, yesterday, yesterday_end
    )
    
    # 最近7天数据
    week_ago = today - timedelta(days=7)
    week_stats = get_sku_sales_stats(db, variant_id, week_ago, today_end)
    
    # 最近30天数据
    month_ago = today - timedelta(days=30)
    month_stats = get_sku_sales_stats(db, variant_id, month_ago, today_end)
    
    return {
        'today': today_stats,
        'yesterday': yesterday_stats,
        'week': week_stats,
        'month': month_stats
    }


def get_products_below_warning_level(db: Session, threshold_ratio: float = 1.0) -> List[dict]:
    """
    获取库存低于警告阈值的产品列表
    
    Args:
        db: 数据库会话
        threshold_ratio: 警告阈值比例，默认为1.0（低于100%警告阈值时显示）
                        例如：0.5表示低于50%警告阈值时显示
    """
    from config.settings import load_settings
    
    results = []
    
    # 从扁平格式配置获取全局预警阈值
    settings = load_settings()
    global_warning_level = settings.get('default_warning_level', 96)
    
    # 使用子查询获取当前库存
    stock_levels = (
        db.query(
            StockLog.variant_id,
            func.sum(StockLog.change_quantity).label('current_stock')
        )
        .group_by(StockLog.variant_id)
        .subquery()
    )
    
    # 查询所有变体和其产品信息
    variants = (
        db.query(ProductVariant, func.coalesce(stock_levels.c.current_stock, 0))
        .outerjoin(stock_levels, ProductVariant.id == stock_levels.c.variant_id)
        .join(Product)
        .all()
    )
    
    for variant, current_stock in variants:
        # 优先使用产品自己的预警阈值，如果没有则使用全局预警阈值
        warning_level = variant.product.stock_warning_level or global_warning_level
        stock_ratio = current_stock / warning_level if warning_level > 0 else 0
        
        # 只包含低于指定阈值比例的产品
        if stock_ratio < threshold_ratio:
            results.append({
                'parent_sku': variant.product.parent_sku,
                'variant_sku': variant.sku,
                'option_name': variant.color or variant.size or '',
                'current_stock': current_stock,
                'warning_level': warning_level,
                'stock_ratio': stock_ratio
            })
    
    # 按库存比例排序，库存最少的在前面
    results.sort(key=lambda x: x['stock_ratio'])
    return results


def delete_product_with_variants(
    db: Session,
    product_id: int,
    operator_info: dict
) -> dict:
    """删除产品及其所有变体,包括清理库存记录
    
    Args:
        db: 数据库会话
        product_id: 产品ID
        operator_info: 操作者信息
        
    Returns:
        dict: 删除结果统计
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise ValueError(f"产品ID {product_id} 不存在")
    
    product_name = product.name
    variants = db.query(ProductVariant).filter(
        ProductVariant.product_id == product_id
    ).all()
    
    # 统计信息
    deleted_variants = 0
    cleared_stock_logs = 0
    
    # 清理每个变体的库存记录
    for variant in variants:
        # 删除该变体的所有库存记录
        stock_logs = db.query(StockLog).filter(
            StockLog.variant_id == variant.id
        ).delete()
        cleared_stock_logs += stock_logs
        deleted_variants += 1
        
        # 记录操作日志
        create_action_log(
            db,
            operator_info,
            f'删除产品变体: {variant.sku}'
        )
    
    # 删除产品(会级联删除所有变体)
    db.delete(product)
    
    # 记录总体操作日志
    create_action_log(
        db,
        operator_info,
        f'删除产品: {product_name}, 清理{deleted_variants}个变体, {cleared_stock_logs}条库存记录'
    )
    
    db.commit()
    
    return {
        'product_name': product_name,
        'deleted_variants': deleted_variants,
        'cleared_stock_logs': cleared_stock_logs
    }


def delete_variant_with_stock(
    db: Session,
    variant_id: int,
    operator_info: dict
) -> dict:
    """删除单个变体,包括清理库存记录
    
    Args:
        db: 数据库会话
        variant_id: 变体ID
        operator_info: 操作者信息
        
    Returns:
        dict: 删除结果统计
    """
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    
    if not variant:
        raise ValueError(f"变体ID {variant_id} 不存在")
    
    variant_sku = variant.sku
    
    # 删除该变体的所有库存记录
    cleared_stock_logs = db.query(StockLog).filter(
        StockLog.variant_id == variant_id
    ).delete()
    
    # 删除变体
    db.delete(variant)
    
    # 记录操作日志
    create_action_log(
        db,
        operator_info,
        f'删除变体: {variant_sku}, 清理{cleared_stock_logs}条库存记录'
    )
    
    db.commit()
    
    return {
        'variant_sku': variant_sku,
        'cleared_stock_logs': cleared_stock_logs
    }
