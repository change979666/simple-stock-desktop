from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import ResourceClosedError

from database.models import SaleOrder, OrderItem, ProductVariant
from crud.operations import create_stock_log

# 导入数据变更跟踪器
from utils.data_change_tracker import mark_data_changed


def create_sale_order(
    db: Session,
    order_number: str,
    customer_name: str,
    order_date: datetime,
    items: List[dict],
    operator_info: str,
    total_amount: float = None
) -> SaleOrder:
    """创建销售订单
    
    Args:
        db: 数据库会话
        order_number: 订单号
        customer_name: 客户名称
        order_date: 订单日期
        items: 订单项列表，每项包含：
            - parent_sku: 原始SKU
            - variant_sku: 处理后的SKU
            - quantity: 数量
            - item_price: 单价（可选）
            - variant_id: 产品变体ID
        operator_info: 操作者信息
        total_amount: 订单总价（可选）
            - 如果指定，使用此值（支持优惠券等折扣）
            - 如果不指定，从产品单价自动计算
    """
    # 如果没有指定总价，从产品单价计算
    if total_amount is None:
        total_amount = sum(
            item.get('item_price', 0) * item['quantity']
            for item in items
        )
    
    # 创建订单（使用指定的或计算的总价）
    order = SaleOrder(
        order_number=order_number,
        customer_name=customer_name,
        order_date=order_date,
        total_amount=total_amount
    )
    
    # 创建订单项
    for item in items:
        order_item = OrderItem(
            parent_sku=item['parent_sku'],
            variant_sku=item['variant_sku'],
            quantity=item['quantity'],
            item_price=item.get('item_price')
        )
        order.items.append(order_item)
        
        # 创建出库记录
        create_stock_log(
            db,
            item['variant_id'],
            -item['quantity'],
            f'销售出库 (订单号: {order_number})',
            operator_info
        )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # 标记数据已变更
    mark_data_changed(f"create_sale_order: {order_number}")
    
    return order


def get_sales_stats(
    db: Session,
    start_date: datetime,
    end_date: datetime
) -> Dict:
    """获取指定时间段的销售统计
    
    Args:
        db: 数据库会话
        start_date: 开始时间
        end_date: 结束时间
        
    Returns:
        Dict: 包含销售总额、订单数等统计数据的字典
    """
    orders = db.query(SaleOrder).filter(
        SaleOrder.order_date >= start_date,
        SaleOrder.order_date <= end_date
    ).all()
    
    total_amount = sum(order.total_amount for order in orders)
    total_orders = len(orders)
    total_items = sum(len(order.items) for order in orders)
    
    return {
        'period': {
            'start': start_date,
            'end': end_date,
        },
        'total_amount': total_amount,
        'total_orders': total_orders,
        'total_items': total_items,
        'orders': orders
    }


def get_daily_sales_stats(db: Session, target_date: datetime) -> Dict:
    """获取指定日期的销售统计
    
    Args:
        db: 数据库会话
        target_date: 目标日期
        
    Returns:
        Dict: 包含销售总额、订单数等统计数据的字典
    """
    # 获取当天的开始和结束时间
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = datetime(
        target_date.year, target_date.month, target_date.day,
        23, 59, 59
    )
    
    return get_sales_stats(db, start, end)


def get_variant_sales_stats(
    db: Session,
    variant_sku: str,
    start_date: datetime,
    end_date: datetime
) -> Dict:
    """获取指定SKU在指定时间段内的销售统计
    
    Args:
        db: 数据库会话
        variant_sku: 产品规格SKU
        start_date: 开始时间
        end_date: 结束时间
        
    Returns:
        Dict: 包含该SKU的销量统计数据的字典
    """
    # 查询该时间段内包含指定SKU的订单
    orders_with_sku = db.query(SaleOrder).join(OrderItem).filter(
        SaleOrder.order_date >= start_date,
        SaleOrder.order_date <= end_date,
        OrderItem.variant_sku == variant_sku
    ).all()
    
    # 统计该SKU的销量和销售额
    total_quantity = 0
    total_amount = 0
    total_orders = len(orders_with_sku)
    
    for order in orders_with_sku:
        # 只计算该SKU的订单项
        for item in order.items:
            if item.variant_sku == variant_sku:
                total_quantity += item.quantity
                # item_price 可能为 None，需要处理
                if item.item_price is not None:
                    total_amount += item.quantity * item.item_price
    
    return {
        'period': {
            'start': start_date,
            'end': end_date,
        },
        'variant_sku': variant_sku,
        'total_quantity': total_quantity,
        'total_amount': total_amount,
        'total_orders': total_orders,
        'orders': orders_with_sku
    }


def get_yesterday_stats(db: Session) -> Dict:
    """获取昨天的销售统计"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    start = datetime(yesterday.year, yesterday.month, yesterday.day)
    end = datetime(
        yesterday.year, yesterday.month, yesterday.day,
        23, 59, 59
    )
    
    return get_sales_stats(db, start, end)


def get_last_week_stats(db: Session) -> Dict:
    """获取最近7天的销售统计"""
    end = datetime.now()
    start = end - timedelta(days=6)  # 改为6天，使日期范围为7个自然日（包含今天）
    start = datetime(start.year, start.month, start.day)
    
    return get_sales_stats(db, start, end)


def get_last_month_stats(db: Session) -> Dict:
    """获取最近30天的销售统计"""
    end = datetime.now()
    start = end - timedelta(days=29)  # 改为29天，使日期范围为30个自然日（包含今天）
    start = datetime(start.year, start.month, start.day)
    
    return get_sales_stats(db, start, end)


def get_sales_orders(db: Session, **filters) -> List[SaleOrder]:
    """获取销售订单列表（优化：使用joinedload预加载订单项，避免N+1查询）
    
    Args:
        filters: 筛选条件
            - status: 订单状态
            - start_date: 开始日期
            - end_date: 结束日期
            - customer_name: 客户名称
    """
    from sqlalchemy.orm import joinedload
    
    query = db.query(SaleOrder).options(joinedload(SaleOrder.items))
    
    if 'status' in filters:
        query = query.filter(SaleOrder.status == filters['status'])
    
    if 'start_date' in filters:
        query = query.filter(SaleOrder.order_date >= filters['start_date'])
    
    if 'end_date' in filters:
        query = query.filter(SaleOrder.order_date <= filters['end_date'])
    
    if 'customer_name' in filters:
        query = query.filter(
            SaleOrder.customer_name.like(f"%{filters['customer_name']}%")
        )
    
    return query.order_by(SaleOrder.order_date.desc()).all()


def get_sales_orders_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> tuple[List[SaleOrder], int]:
    """分页获取销售订单列表
    
    Args:
        db: 数据库会话
        page: 页码（从1开始）
        page_size: 每页数量
        search: 搜索关键词（匹配订单号或客户名）
        status: 订单状态筛选
        start_date: 开始日期
        end_date: 结束日期
    
    Returns:
        (orders, total): 订单列表和总数
    """
    from sqlalchemy.orm import joinedload
    
    # 构建基础查询
    query = db.query(SaleOrder).options(joinedload(SaleOrder.items))
    
    # 应用搜索过滤
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (SaleOrder.order_number.ilike(search_pattern)) |
            (SaleOrder.customer_name.ilike(search_pattern))
        )
    
    # 应用状态过滤
    if status:
        query = query.filter(SaleOrder.status == status)
    
    # 应用日期范围过滤
    if start_date:
        query = query.filter(SaleOrder.order_date >= start_date)
    if end_date:
        query = query.filter(SaleOrder.order_date <= end_date)
    
    # 获取总数（在分页前）
    total = query.count()
    
    # 应用分页和排序
    orders = (
        query
        .order_by(SaleOrder.order_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return orders, total


def search_sales_orders(db: Session, search_text: str) -> List[SaleOrder]:
    """搜索销售订单（按订单号或客户名，不限时间范围）
    优化：使用joinedload预加载订单项
    
    Args:
        db: 数据库会话
        search_text: 搜索文本（匹配订单号或客户名）
    
    Returns:
        匹配的订单列表，按日期降序排列
    """
    from sqlalchemy.orm import joinedload
    
    search_pattern = f"%{search_text}%"
    
    query = db.query(SaleOrder).options(
        joinedload(SaleOrder.items)
    ).filter(
        (SaleOrder.order_number.like(search_pattern)) |
        (SaleOrder.customer_name.like(search_pattern))
    )
    
    return query.order_by(SaleOrder.order_date.desc()).all()


def get_sale_order_by_id(db: Session, order_id: int) -> Optional[SaleOrder]:
    """根据ID获取销售订单"""
    return db.query(SaleOrder).filter(SaleOrder.id == order_id).first()


def update_sale_order_status(db: Session, order_id: int, status: str):
    """更新订单状态"""
    order = db.query(SaleOrder).filter(SaleOrder.id == order_id).first()
    if order:
        order.status = status
        db.commit()
        
        # 标记数据已变更
        mark_data_changed(f"update_order_status: {order.order_number}")


def delete_sale_order(db: Session, order_id: int, operator_info: dict = None):
    """
    删除销售订单并恢复库存
    
    Args:
        db: 数据库会话
        order_id: 订单ID
        operator_info: 操作者信息 {'name': '操作员名称'}
    """
    from crud.operations import create_stock_log, create_action_log
    from database.models import ProductVariant
    
    # 获取订单信息
    order = db.query(SaleOrder).filter(SaleOrder.id == order_id).first()
    if not order:
        return
    
    order_number = order.order_number
    customer_name = order.customer_name
    
    # 获取订单项，准备恢复库存
    order_items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()
    
    # 记录删除订单的操作日志
    action_desc = (
        f"删除订单 {order_number} (客户: {customer_name}, "
        f"共 {len(order_items)} 个SKU)"
    )
    create_action_log(
        db=db,
        operator_info=operator_info or {},
        action=action_desc
    )
    
    # 恢复每个订单项的库存
    for item in order_items:
        # 查找对应的产品变体
        variant = db.query(ProductVariant).filter(
            ProductVariant.sku == item.variant_sku
        ).first()
        
        if variant:
            # 记录库存变化日志
            stock_log_desc = (
                f"删除订单 {order_number} - 恢复库存 "
                f"{item.variant_sku} 数量 +{item.quantity}"
            )
            create_stock_log(
                db=db,
                variant_id=variant.id,
                change_quantity=item.quantity,  # 正数表示入库
                notes=stock_log_desc,
                operator_info=operator_info or {},
                allow_negative=True
            )
    
    # 删除订单项
    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()
    
    # 删除订单
    db.delete(order)
    
    # 提交事务
    db.commit()
    
    # 标记数据已变更
    mark_data_changed(f"delete_sale_order: {order_number}")


def import_sales_orders(db, orders_data, operator_info):
    """批量导入销售订单"""
    from crud.operations import create_action_log
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    
    success_count = 0
    failed_count = 0
    skipped_count = 0  # 新增：跳过的订单数（重复）
    errors = []
    skipped_orders = []  # 新增：跳过的订单列表
    
    logger.info(f"开始批量导入销售订单，共 {len(orders_data)} 个订单")
    
    for idx, order_data in enumerate(orders_data, 1):
        order_number = order_data.get('order_number', f'unknown_{idx}')
        
        # 预验证（在事务外进行）
        if not order_number or order_number.startswith('unknown_'):
            error_msg = '订单号不能为空'
            logger.warning(
                f"[{idx}/{len(orders_data)}] "
                f"订单验证失败: {error_msg}"
            )
            errors.append({
                'order': order_data,
                'error': error_msg
            })
            failed_count += 1
            continue
        
        # 检查订单号是否重复 - 智能比对
        existing = db.query(SaleOrder).filter(
            SaleOrder.order_number == order_number
        ).first()
        
        # 如果订单已存在，比对内容是否一致
        if existing:
            # 检查是否强制覆盖
            force_overwrite = order_data.get('force_overwrite', False)
            
            if not force_overwrite:
                # 获取现有订单的所有订单项
                existing_items = db.query(OrderItem).filter(
                    OrderItem.order_id == existing.id
                ).all()
                
                # 构建现有订单项的字典 {sku: quantity}
                existing_items_dict = {
                    item.variant_sku: item.quantity
                    for item in existing_items
                }
                
                # 构建新导入订单项的字典 {sku: quantity}
                new_items = order_data.get('items', [])
                new_items_dict = {
                    item.get('variant_sku', ''): item.get('quantity', 0)
                    for item in new_items
                }
                
                # 比对订单项是否完全一致
                items_identical = (
                    len(existing_items_dict) == len(new_items_dict) and
                    all(
                        existing_items_dict.get(sku) == qty
                        for sku, qty in new_items_dict.items()
                    )
                )
                
                # 比对订单总金额
                new_total_amount = order_data.get('total_amount', 0)
                if new_total_amount is None:
                    new_total_amount = 0
                amount_identical = (
                    abs(existing.total_amount - new_total_amount) < 0.01
                )
                
                # 如果订单完全一致，静默跳过
                if items_identical and amount_identical:
                    logger.info(
                        f"[{idx}/{len(orders_data)}] "
                        f"订单 {order_number} 已存在且内容完全一致，跳过"
                    )
                    skipped_orders.append({
                        'order_number': order_number,
                        'reason': '订单内容完全一致'
                    })
                    skipped_count += 1
                    continue
                
                # 如果订单内容不一致，需要询问用户
                logger.warning(
                    f"[{idx}/{len(orders_data)}] "
                    f"订单 {order_number} 已存在但内容不一致"
                )
                
                # 返回标记，需要在GUI层询问用户
                # 这里先收集所有冲突的订单，稍后统一处理
                errors.append({
                    'order': order_data,
                    'error': 'DUPLICATE_CONFLICT',
                    'order_number': order_number,
                    'existing_items': existing_items_dict,
                    'new_items': new_items_dict,
                    'existing_amount': existing.total_amount,
                    'new_amount': new_total_amount
                })
                failed_count += 1
                continue
            
            # force_overwrite=True，执行覆盖更新
            logger.info(
                f"[{idx}/{len(orders_data)}] "
                f"订单 {order_number} 强制覆盖更新"
            )
            
            try:
                # 获取旧订单的所有订单项
                old_items = db.query(OrderItem).filter(
                    OrderItem.order_id == existing.id
                ).all()
                
                # 恢复旧订单项的库存
                from crud.operations import (
                    get_variant_by_sku,
                    create_stock_log
                )
                
                for old_item in old_items:
                    if old_item.variant_sku and old_item.quantity > 0:
                        variant = get_variant_by_sku(db, old_item.variant_sku)
                        if variant:
                            # 恢复库存（加回去）
                            notes = (
                                f'订单覆盖更新-恢复库存 '
                                f'(订单号: {order_number})'
                            )
                            create_stock_log(
                                db,
                                variant_id=variant.id,
                                change_quantity=old_item.quantity,  # 正数
                                notes=notes,
                                operator_info=operator_info
                            )
                            logger.debug(
                                f"恢复库存: SKU {old_item.variant_sku} "
                                f"+{old_item.quantity}"
                            )
                
                # 删除旧订单项
                db.query(OrderItem).filter(
                    OrderItem.order_id == existing.id
                ).delete()
                
                # 删除旧订单
                db.delete(existing)
                db.flush()
                
                logger.info(
                    f"订单 {order_number} 的旧数据已删除，库存已恢复"
                )
                
            except Exception as e:
                error_msg = f'覆盖更新旧订单失败: {str(e)}'
                logger.error(
                    f"[{idx}/{len(orders_data)}] {error_msg}",
                    exc_info=True
                )
                errors.append({'order': order_data, 'error': error_msg})
                failed_count += 1
                continue
        
        items = order_data.get('items', [])
        if not items:
            error_msg = '订单项不能为空'
            logger.warning(
                f"[{idx}/{len(orders_data)}] "
                f"订单 {order_number} 验证失败: {error_msg}"
            )
            errors.append({
                'order': order_data,
                'error': error_msg
            })
            failed_count += 1
            continue
        
        # ⚠️ 使用嵌套事务(Savepoint)确保每个订单是独立的原子操作
        # with 语句会自动在成功时 commit，异常时 rollback
        try:
            with db.begin_nested():
                logger.debug(
                    f"[{idx}/{len(orders_data)}] "
                    f"开始处理订单: {order_number}"
                )
                
                # 直接使用Excel中的订单总价，不做自动计算
                # 如果Excel没有total_amount列或值为空，设为0
                total_amount = order_data.get('total_amount')
                if total_amount is None:
                    total_amount = 0  # 没有提供总价，默认为0
                
                # 解析订单日期
                order_date = order_data.get('order_date')
                if isinstance(order_date, str):
                    try:
                        order_date = datetime.fromisoformat(order_date)
                    except Exception:
                        order_date = datetime.now()
                elif not order_date:
                    order_date = datetime.now()
                
                # 创建销售订单
                order = SaleOrder(
                    order_number=order_number,
                    customer_name=order_data.get('customer_name', ''),
                    order_date=order_date,
                    total_amount=total_amount
                )
                db.add(order)
                db.flush()  # 获取order.id
                
                logger.debug(
                    f"[{idx}/{len(orders_data)}] "
                    f"订单 {order_number} 已创建 (ID: {order.id})，"
                    f"开始处理 {len(items)} 个订单项"
                )
                
                # 创建订单项并扣减库存
                from crud.operations import (
                    get_variant_by_sku,
                    create_stock_log
                )
                
                for item_idx, item_data in enumerate(items, 1):
                    # 创建订单项
                    # 保留原始价格，如果是None就是None，不转成0
                    item_price = item_data.get('item_price')
                    variant_sku = item_data.get('variant_sku', '')
                    
                    item = OrderItem(
                        order_id=order.id,
                        parent_sku=item_data.get('parent_sku', ''),
                        variant_sku=variant_sku,
                        quantity=item_data.get('quantity', 0),
                        item_price=(
                            item_price if item_price is not None else 0
                        )
                    )
                    db.add(item)
                    
                    # 扣减库存
                    quantity = item_data.get('quantity', 0)
                    if variant_sku and quantity > 0:
                        variant = get_variant_by_sku(db, variant_sku)
                        if variant:
                            notes = f'销售出库 (订单号: {order_number})'
                            create_stock_log(
                                db,
                                variant_id=variant.id,
                                change_quantity=-quantity,
                                notes=notes,
                                operator_info=operator_info
                            )
                            logger.debug(
                                f"[{idx}/{len(orders_data)}] "
                                f"订单项 {item_idx}/{len(items)}: "
                                f"SKU {variant_sku} 库存扣减 {quantity}"
                            )
                        else:
                            logger.warning(
                                f"[{idx}/{len(orders_data)}] "
                                f"订单项 {item_idx}/{len(items)}: "
                                f"SKU {variant_sku} 未找到对应的产品变体"
                            )
                
                success_count += 1
                logger.info(
                    f"[{idx}/{len(orders_data)}] "
                    f"订单 {order_number} 导入成功"
                )
                # with 语句会在此自动 commit 嵌套事务
            
        except ResourceClosedError as e:
            # 嵌套事务已被意外关闭或父事务处于错误状态
            error_msg = f'事务已关闭: {str(e)}'
            logger.error(
                f"[{idx}/{len(orders_data)}] "
                f"订单 {order_number} 导入失败 (ResourceClosedError): {e}",
                exc_info=True
            )
            errors.append({'order': order_data, 'error': error_msg})
            failed_count += 1
            # 回滚顶层会话以重置状态
            try:
                db.rollback()
                logger.info("已执行顶层 session rollback 以重置会话状态")
            except Exception as rollback_err:
                logger.error(
                    f"顶层 rollback 失败: {rollback_err}",
                    exc_info=True
                )
            continue
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"[{idx}/{len(orders_data)}] "
                f"订单 {order_number} 导入失败: {error_msg}",
                exc_info=True
            )
            errors.append({'order': order_data, 'error': error_msg})
            failed_count += 1
            # with 语句会自动 rollback，无需手动调用
            continue
    
    # 提交整个批次
    logger.info(
        f"所有订单处理完毕，准备提交批次事务。"
        f"成功: {success_count}, 跳过: {skipped_count}, 失败: {failed_count}"
    )
    
    try:
        # 先记录操作日志(在同一事务中)
        action_desc = (
            f'批量导入销售订单: '
            f'成功{success_count}, '
            f'跳过{skipped_count}, '
            f'失败{failed_count}'
        )
        create_action_log(db, operator_info, action_desc)
        
        # 标记数据已变更(批量导入也需要触发轻量级询问机制)
        if success_count > 0:
            mark_data_changed(f"import_sales_orders: {success_count} orders")
        
        # 最后提交事务
        db.commit()
        logger.info(f"批量导入完成并已记录操作日志: {action_desc}")
    except Exception as e:
        logger.error(
            f"提交批次事务失败: {str(e)}",
            exc_info=True
        )
        db.rollback()
        return {
            'success': 0,
            'failed': len(orders_data),
            'skipped': 0,
            'errors': [{'error': f'批次提交失败: {str(e)}'}],
            'skipped_orders': []
        }
    
    return {
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'errors': errors,
        'skipped_orders': skipped_orders
    }


def get_sku_sales_stats(
    db: Session,
    start_date: datetime,
    end_date: datetime
) -> List[Dict]:
    """获取SKU销量统计
    
    Args:
        db: 数据库会话
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        SKU销量统计列表，包含：
        - sku: SKU
        - product_name: 产品名称
        - options: 选项（如：颜色-尺码）
        - quantity: 销售数量
        - amount: 销售金额
        - order_count: 订单数
    """
    from database.models import Product
    
    # 查询指定时间范围内的订单项
    # 按SKU分组统计数量和金额
    query = db.query(
        OrderItem.variant_sku.label('sku'),
        func.sum(OrderItem.quantity).label('quantity'),
        func.sum(OrderItem.quantity * OrderItem.item_price).label('amount'),
        func.count(func.distinct(OrderItem.order_id)).label('order_count')
    ).join(
        SaleOrder, OrderItem.order_id == SaleOrder.id
    ).filter(
        SaleOrder.order_date >= start_date,
        SaleOrder.order_date <= end_date
    ).group_by(
        OrderItem.variant_sku
    )
    
    results = query.all()
    
    # 获取SKU对应的产品信息
    stats = []
    for row in results:
        sku = row.sku
        
        # 查找产品变体信息
        variant = db.query(ProductVariant).filter(
            func.lower(ProductVariant.sku) == sku.lower()
        ).first()
        
        if variant:
            # 获取产品信息
            product = db.query(Product).filter(
                Product.id == variant.product_id
            ).first()
            
            product_name = product.name if product else ''
            
            # 使用 option_name 字段（格式如：Black, White-S 等）
            options = variant.option_name if variant.option_name else ''
        else:
            product_name = ''
            options = ''
        
        stats.append({
            'sku': sku,
            'product_name': product_name,
            'options': options,
            'quantity': int(row.quantity or 0),
            'amount': float(row.amount or 0),
            'order_count': int(row.order_count or 0)
        })
    
    # 按销量降序排序
    stats.sort(key=lambda x: x['quantity'], reverse=True)
    
    return stats
