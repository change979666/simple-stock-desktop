"""
销售管理API路由
提供销售订单的CRUD操作
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date

from database.session import get_db
from crud.sales import (
    create_sale_order,
    get_sale_order_by_id,
    update_sale_order_status,
    delete_sale_order
)
from crud.operations import create_action_log

router = APIRouter(prefix="/sales", tags=["sales"])


# ============ 请求/响应模型 ============

class OrderItemCreate(BaseModel):
    """订单项创建模型 - 匹配GUI格式"""
    variant_id: Optional[int] = None  # 可选，如果有SKU会自动查找
    sku: Optional[str] = None  # GUI可能发送SKU
    quantity: int
    unit_price: float


class SaleOrderCreate(BaseModel):
    """销售订单创建模型 - 匹配GUI格式"""
    order_number: Optional[str] = None  # GUI可能发送订单号
    order_date: Optional[str] = None  # GUI可能发送日期
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[OrderItemCreate]
    total_amount: Optional[float] = None  # 如果没有会自动计算
    notes: Optional[str] = None
    operator_info: Optional[dict] = None  # GUI发送dict格式


class SaleOrderUpdate(BaseModel):
    """销售订单更新模型"""
    status: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    notes: Optional[str] = None


# ============ API端点 ============

@router.get("/orders")
def get_orders_list(
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取销售订单列表（支持分页）
    
    参数:
    - page: 页码（从1开始）
    - page_size: 每页数量（默认50）
    - search: 搜索关键词（匹配订单号或客户名）
    - status: 订单状态筛选
    - start_date: 开始日期(ISO格式字符串)
    - end_date: 结束日期(ISO格式字符串)
    
    返回:
    {
        "items": [...],
        "total": 总数,
        "page": 当前页,
        "page_size": 每页数量,
        "total_pages": 总页数
    }
    """
    from crud.sales import get_sales_orders_paginated
    import math
    
    # 转换日期参数
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    # 使用分页查询
    orders, total = get_sales_orders_paginated(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        start_date=start_dt,
        end_date=end_dt
    )
    
    # 计算总页数
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    # 转换为字典格式
    items = []
    for order in orders:
        order_dict = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'order_date': (order.order_date.isoformat()
                          if order.order_date else None),
            'total_amount': float(order.total_amount),
            'items': []
        }
        
        for item in order.items:
            item_dict = {
                'id': item.id,
                'order_id': item.order_id,
                'parent_sku': item.parent_sku,
                'variant_sku': item.variant_sku,
                'quantity': item.quantity,
                'item_price': float(item.item_price) if item.item_price else 0
            }
            order_dict['items'].append(item_dict)
        
        items.append(order_dict)
    
    # 返回分页响应
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    }


@router.post("/orders")
def create_order(
    order: SaleOrderCreate,
    db: Session = Depends(get_db)
):
    """创建销售订单 - 支持SKU和variant_id"""
    try:
        from crud.operations import get_variant_by_sku
        
        # 处理订单项，支持SKU查找variant_id
        items_data = []
        for item in order.items:
            variant_id = item.variant_id
            
            # 如果没有variant_id但有SKU，通过SKU查找
            if not variant_id and item.sku:
                variant = get_variant_by_sku(db, item.sku)
                if not variant:
                    raise HTTPException(
                        status_code=404,
                        detail=f"SKU {item.sku} 不存在"
                    )
                variant_id = variant.id
            
            if not variant_id:
                raise HTTPException(
                    status_code=400,
                    detail="订单项必须提供variant_id或sku"
                )
            
            items_data.append({
                'variant_id': variant_id,
                'quantity': item.quantity,
                'unit_price': item.unit_price
            })
        
        # 如果没有提供total_amount，自动计算
        total_amount = order.total_amount
        if total_amount is None:
            total_amount = sum(
                item['quantity'] * item['unit_price']
                for item in items_data
            )
        
        # 处理operator_info
        import json
        operator_dict = (
            order.operator_info
            if isinstance(order.operator_info, dict)
            else json.loads(order.operator_info)
            if order.operator_info
            else {"operator": "系统"}
        )
        
        # 创建订单
        new_order = create_sale_order(
            db=db,
            order_number=order.order_number or datetime.now().strftime('SO%Y%m%d%H%M%S%f')[:18],
            customer_name=order.customer_name,
            order_date=datetime.now(),
            items=items_data,
            operator_info=operator_dict,
            total_amount=total_amount
        )
        
        # 记录操作日志
        create_action_log(
            db=db,
            operator_info=operator_dict,
            action=f'创建销售订单: {new_order.order_number}, 金额: {total_amount}'
        )
        
        # create_sale_order_v2已经commit，这里不需要
        
        return {
            "message": "订单创建成功",
            "order_id": new_order.id,
            "order_number": new_order.order_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/search")
def search_orders(
    search: str = Query(..., description="搜索文本（订单号或客户名）"),
    db: Session = Depends(get_db)
):
    """搜索销售订单（按订单号或客户名）
    
    Args:
        search: 搜索文本（匹配订单号或客户名）
    
    Returns:
        匹配的订单列表，按日期降序排列
    """
    from crud.sales import search_sales_orders
    
    orders = search_sales_orders(db, search)
    
    # 转换为字典格式
    result = []
    for order in orders:
        order_dict = {
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'order_date': (
                order.order_date.isoformat() if order.order_date else None
            ),
            'total_amount': float(order.total_amount),
            'items': []
        }
        
        for item in order.items:
            item_dict = {
                'id': item.id,
                'order_id': item.order_id,
                'parent_sku': item.parent_sku,
                'variant_sku': item.variant_sku,
                'quantity': item.quantity,
                'item_price': (
                    float(item.item_price) if item.item_price else 0.0
                )
            }
            order_dict['items'].append(item_dict)
        
        result.append(order_dict)
    
    return result


@router.get("/orders/{order_id}")
def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db)
):
    """获取订单详情"""
    order = get_sale_order_by_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    return {
        'id': order.id,
        'order_number': order.order_number,
        'customer_name': order.customer_name,
        'order_date': order.order_date.isoformat() if order.order_date else None,
        'total_amount': float(order.total_amount),
        'items': [
            {
                'id': item.id,
                'order_id': item.order_id,
                'parent_sku': item.parent_sku,
                'variant_sku': item.variant_sku,
                'quantity': item.quantity,
                'item_price': float(item.item_price) if item.item_price else 0.0
            }
            for item in order.items
        ]
    }


@router.put("/orders/{order_id}")
def update_order(
    order_id: int,
    order: SaleOrderUpdate,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """更新订单信息"""
    db_order = get_sale_order_by_id(db, order_id)
    
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 更新字段
    if order.status is not None:
        update_sale_order_status(db, order_id, order.status)
    
    if order.customer_name is not None:
        db_order.customer_name = order.customer_name
    # 注意：customer_phone, customer_address, notes字段在SaleOrder模型中不存在
    
    # 记录操作日志
    create_action_log(
        db=db,
        action_type='更新订单',
        details=f'订单号: {db_order.order_number}',
        operator_info=operator_info
    )
    
    db.commit()  # 这里需要commit，因为上面的修改没有在CRUD层
    
    return {"message": "订单更新成功"}


@router.delete("/orders/{order_id}")
def delete_order(
    order_id: int,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """删除订单并恢复库存"""
    import json
    
    order = get_sale_order_by_id(db, order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 解析操作者信息
    operator_dict = (json.loads(operator_info) 
                    if isinstance(operator_info, str) 
                    else operator_info)
    
    # delete_sale_order 函数内部会：
    # 1. 记录删除订单的操作日志
    # 2. 恢复每个SKU的库存
    # 3. 记录库存恢复的日志
    # 4. 删除订单数据
    delete_sale_order(db, order_id, operator_dict)
    
    return {"message": "订单删除成功，库存已恢复"}


# ============ 统计API ============

@router.get("/stats/daily")
def get_daily_stats(
    target_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """获取每日销售统计"""
    from crud.sales import get_daily_sales_stats
    
    if target_date is None:
        target_date = datetime.now()
    
    stats = get_daily_sales_stats(db, target_date)
    
    return stats


@router.get("/stats/yesterday")
def get_yesterday_sales_stats(db: Session = Depends(get_db)):
    """获取昨日销售统计"""
    from crud.sales import get_yesterday_stats
    
    return get_yesterday_stats(db)


@router.get("/stats/week")
def get_week_sales_stats(db: Session = Depends(get_db)):
    """获取最近7天销售统计"""
    from crud.sales import get_last_week_stats
    
    return get_last_week_stats(db)


@router.get("/stats/month")
def get_month_sales_stats(db: Session = Depends(get_db)):
    """获取最近30天销售统计"""
    from crud.sales import get_last_month_stats
    
    return get_last_month_stats(db)


@router.post("/import")
def import_sales_orders_endpoint(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """批量导入销售订单"""
    from crud.sales import import_sales_orders
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    orders = data.get('orders', [])
    operator_info = data.get('operator_info', '{}')
    
    operator_dict = json.loads(operator_info) if isinstance(
        operator_info, str) else operator_info
    
    logger.info(
        f"API 接收批量导入请求: {len(orders)} 个订单, "
        f"操作员: {operator_dict.get('name', 'unknown')}"
    )
    
    try:
        result = import_sales_orders(db, orders, operator_dict)
        logger.info(
            f"批量导入完成: 成功 {result['success']}, "
            f"跳过 {result['skipped']}, 失败 {result['failed']}"
        )
        return result
    except Exception as e:
        logger.error(
            f"批量导入订单时发生未捕获异常: {str(e)}",
            exc_info=True
        )
        raise


@router.get("/sku_stats")
def get_sku_sales_stats_endpoint(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db)
):
    """获取SKU销量统计
    
    Args:
        start_date: 开始日期 (ISO格式)
        end_date: 结束日期 (ISO格式)
    """
    from crud.sales import get_sku_sales_stats
    from datetime import datetime
    
    try:
        # URL解码日期字符串（处理 %3A 等编码）
        from urllib.parse import unquote
        start_date_decoded = unquote(start_date)
        end_date_decoded = unquote(end_date)
        
        # 解析日期字符串
        start_dt = datetime.fromisoformat(
            start_date_decoded.replace('Z', '+00:00')
        )
        end_dt = datetime.fromisoformat(
            end_date_decoded.replace('Z', '+00:00')
        )
        
        # 获取统计数据
        stats = get_sku_sales_stats(db, start_dt, end_dt)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"日期格式错误或查询失败: {str(e)}"
        )
