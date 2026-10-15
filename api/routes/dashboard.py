"""仪表板API路由"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta

from database.session import get_db
from crud.sales import (
    get_daily_sales_stats,
    get_yesterday_stats,
    get_last_week_stats,
    get_last_month_stats,
    get_variant_sales_stats
)
from crud.operations import (
    get_products_below_warning_level,
    get_variant_by_sku,
    get_sku_recent_sales
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats/today")
def get_today_stats(db: Session = Depends(get_db)) -> Dict:
    """获取今日销售统计"""
    stats = get_daily_sales_stats(db, datetime.now())
    # 转换为API响应格式
    result = {
        'total_amount': float(stats.get('total_amount', 0)),
        'total_orders': stats.get('total_orders', 0),
        'total_items': stats.get('total_items', 0)
    }
    if 'period' in stats:
        period = stats['period']
        result['period'] = {
            'start': period['start'].isoformat() if hasattr(period['start'], 'isoformat') else str(period['start']),
            'end': period['end'].isoformat() if hasattr(period['end'], 'isoformat') else str(period['end'])
        }
    return result


@router.get("/stats/yesterday")
def get_yesterday_statistics(db: Session = Depends(get_db)) -> Dict:
    """获取昨日销售统计"""
    stats = get_yesterday_stats(db)
    # 转换为API响应格式
    result = {
        'total_amount': float(stats.get('total_amount', 0)),
        'total_orders': stats.get('total_orders', 0),
        'total_items': stats.get('total_items', 0)
    }
    if 'period' in stats:
        period = stats['period']
        result['period'] = {
            'start': period['start'].isoformat() if hasattr(period['start'], 'isoformat') else str(period['start']),
            'end': period['end'].isoformat() if hasattr(period['end'], 'isoformat') else str(period['end'])
        }
    return result


@router.get("/stats/week")
def get_week_stats(db: Session = Depends(get_db)) -> Dict:
    """获取最近7天销售统计"""
    stats = get_last_week_stats(db)
    # 转换为API响应格式
    result = {
        'total_amount': float(stats.get('total_amount', 0)),
        'total_orders': stats.get('total_orders', 0),
        'total_items': stats.get('total_items', 0)
    }
    if 'period' in stats:
        period = stats['period']
        result['period'] = {
            'start': period['start'].isoformat() if hasattr(period['start'], 'isoformat') else str(period['start']),
            'end': period['end'].isoformat() if hasattr(period['end'], 'isoformat') else str(period['end'])
        }
    return result


@router.get("/stats/month")
def get_month_stats(db: Session = Depends(get_db)) -> Dict:
    """获取最近30天销售统计"""
    stats = get_last_month_stats(db)
    # 转换为API响应格式
    result = {
        'total_amount': float(stats.get('total_amount', 0)),
        'total_orders': stats.get('total_orders', 0),
        'total_items': stats.get('total_items', 0)
    }
    if 'period' in stats:
        period = stats['period']
        result['period'] = {
            'start': period['start'].isoformat() if hasattr(period['start'], 'isoformat') else str(period['start']),
            'end': period['end'].isoformat() if hasattr(period['end'], 'isoformat') else str(period['end'])
        }
    return result


@router.get("/warnings")
def get_inventory_warnings(
    threshold: float = 1.0,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """获取库存预警列表
    
    Args:
        threshold: 警告阈值(默认1.0表示100%)
    """
    warnings = get_products_below_warning_level(db, threshold)
    
    # 为每个警告项添加销量数据
    for warning in warnings:
        variant = get_variant_by_sku(db, warning['variant_sku'])
        if variant:
            sales_data = get_sku_recent_sales(db, variant.id)
            warning['sales_stats'] = {
                'today': sales_data['today']['total_quantity'],
                'yesterday': sales_data['yesterday']['total_quantity'],
                'week': sales_data['week']['total_quantity'],
                'month': sales_data['month']['total_quantity']
            }
        else:
            warning['sales_stats'] = {
                'today': 0, 'yesterday': 0, 'week': 0, 'month': 0
            }
    
    return warnings


@router.get("/sales-stats/{variant_sku}")
def get_variant_sales_statistics(
    variant_sku: str,
    db: Session = Depends(get_db)
) -> Dict:
    """获取指定SKU的销量统计
    
    Args:
        variant_sku: 变体SKU
        
    Returns:
        {'variant_sku': str, 'today': int, 'yesterday': int, 'week': int, 'month': int}
    """
    try:
        variant = get_variant_by_sku(db, variant_sku)
        if not variant:
            return {
                'variant_sku': variant_sku,
                'today': 0,
                'yesterday': 0,
                'week': 0,
                'month': 0
            }
        
        # 今日销量
        today = datetime.now()
        today_start = datetime(today.year, today.month, today.day)
        today_end = today_start.replace(hour=23, minute=59, second=59)
        today_stats = get_variant_sales_stats(db, variant_sku, today_start, today_end)
        
        # 昨日销量
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day)
        yesterday_end = yesterday_start.replace(hour=23, minute=59, second=59)
        yesterday_stats = get_variant_sales_stats(db, variant_sku, yesterday_start, yesterday_end)
        
        # 最近7天
        week_start = today - timedelta(days=7)
        week_stats = get_variant_sales_stats(db, variant_sku, week_start, today_end)
        
        # 最近30天
        month_start = today - timedelta(days=30)
        month_stats = get_variant_sales_stats(db, variant_sku, month_start, today_end)
        
        return {
            'variant_sku': variant_sku,
            'today': today_stats['total_quantity'],
            'yesterday': yesterday_stats['total_quantity'],
            'week': week_stats['total_quantity'],
            'month': month_stats['total_quantity']
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取销量统计失败: {str(e)}"
        )


@router.get("/all")
def get_all_dashboard_data(
    threshold: float = 1.0,
    db: Session = Depends(get_db)
) -> Dict:
    """批量获取仪表盘所有数据（性能优化）
    
    一次性返回今日、昨日、周、月统计数据和库存警告
    
    Args:
        threshold: 库存警告阈值(默认1.0表示100%)
        
    Returns:
        {
            'stats': {
                'today': {...},
                'yesterday': {...},
                'week': {...},
                'month': {...}
            },
            'warnings': [...]
        }
    """
    try:
        # 获取各时间段统计
        today_stats = get_daily_sales_stats(db, datetime.now())
        yesterday_stats = get_yesterday_stats(db)
        week_stats = get_last_week_stats(db)
        month_stats = get_last_month_stats(db)
        
        # 转换为统一格式
        def format_stats(stats):
            result = {
                'total_amount': float(stats.get('total_amount', 0)),
                'total_orders': stats.get('total_orders', 0),
                'total_items': stats.get('total_items', 0)
            }
            if 'period' in stats:
                period = stats['period']
                result['period'] = {
                    'start': period['start'].isoformat() if hasattr(period['start'], 'isoformat') else str(period['start']),
                    'end': period['end'].isoformat() if hasattr(period['end'], 'isoformat') else str(period['end'])
                }
            return result
        
        # 获取库存警告
        warnings = get_products_below_warning_level(db, threshold)
        
        # 为每个警告项添加销量数据
        for warning in warnings:
            variant = get_variant_by_sku(db, warning['variant_sku'])
            if variant:
                sales_data = get_sku_recent_sales(db, variant.id)
                warning['sales_stats'] = {
                    'today': sales_data['today']['total_quantity'],
                    'yesterday': sales_data['yesterday']['total_quantity'],
                    'week': sales_data['week']['total_quantity'],
                    'month': sales_data['month']['total_quantity']
                }
            else:
                warning['sales_stats'] = {
                    'today': 0, 'yesterday': 0, 'week': 0, 'month': 0
                }
        
        return {
            'stats': {
                'today': format_stats(today_stats),
                'yesterday': format_stats(yesterday_stats),
                'week': format_stats(week_stats),
                'month': format_stats(month_stats)
            },
            'warnings': warnings
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取仪表盘数据失败: {str(e)}"
        )


@router.post("/sales-stats/batch")
def get_batch_variant_sales_statistics(
    variant_skus: List[str] = Body(...),
    db: Session = Depends(get_db)
) -> Dict[str, Dict]:
    """批量获取多个SKU的销量统计（高性能优化版）
    
    Args:
        variant_skus: SKU列表
        
    Returns:
        {'sku1': {'today': 0, 'yesterday': 0, ...}, 'sku2': {...}}
    """
    try:
        from sqlalchemy import func, case
        from database.models import OrderItem, SaleOrder
        import time
        
        start_time = time.time()
        
        # 计算时间范围
        today = datetime.now()
        today_start = datetime(today.year, today.month, today.day)
        
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime(yesterday.year, yesterday.month, yesterday.day)
        
        week_start = today - timedelta(days=7)
        month_start = today - timedelta(days=30)
        year_start = datetime(today.year, 1, 1)
        
        print(f"⏱️ 批量查询 {len(variant_skus)} 个SKU的销量统计...")
        
        # 🚀 直接从order_items和sale_orders表查询（实际数据源）
        query_start = time.time()
        query = db.query(
            OrderItem.variant_sku,
            func.sum(case(
                (SaleOrder.order_date >= today_start, OrderItem.quantity),
                else_=0
            )).label('today'),
            func.sum(case(
                ((SaleOrder.order_date >= yesterday_start) &
                 (SaleOrder.order_date < today_start), OrderItem.quantity),
                else_=0
            )).label('yesterday'),
            func.sum(case(
                (SaleOrder.order_date >= week_start, OrderItem.quantity),
                else_=0
            )).label('week'),
            func.sum(case(
                (SaleOrder.order_date >= month_start, OrderItem.quantity),
                else_=0
            )).label('month'),
            func.sum(case(
                (SaleOrder.order_date >= year_start, OrderItem.quantity),
                else_=0
            )).label('year')
        ).join(
            SaleOrder, OrderItem.order_id == SaleOrder.id
        ).filter(
            OrderItem.variant_sku.in_(variant_skus)
        ).group_by(
            OrderItem.variant_sku
        )
        
        # 执行查询并转换为字典（SKU -> stats）
        sku_to_stats = {}
        for row in query.all():
            sku_to_stats[row.variant_sku] = {
                'today': int(row.today or 0),
                'yesterday': int(row.yesterday or 0),
                'week': int(row.week or 0),
                'month': int(row.month or 0),
                'year': int(row.year or 0)
            }
        
        print(f"✅ 查询完成，找到 {len(sku_to_stats)} 个SKU有销量数据 "
              f"(耗时 {time.time() - query_start:.2f}s)")
        
        # 为所有请求的SKU生成结果（包括没有销量的）
        result = {}
        for sku in variant_skus:
            result[sku] = sku_to_stats.get(sku, {
                'today': 0, 'yesterday': 0, 'week': 0, 'month': 0, 'year': 0
            })
        
        print(f"🎉 批量查询完成！总耗时 {time.time() - start_time:.2f}s")
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"批量获取销量统计失败: {str(e)}"
        )
