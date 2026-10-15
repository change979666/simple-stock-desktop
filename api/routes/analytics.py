"""
数据分析API路由
提供图表数据接口：库存趋势、销量排行、颜色分布
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from database.session import get_db
from crud.analytics import (
    get_stock_trend_data,
    get_top_selling_products,
    get_color_distribution,
    get_sales_trend_data,
    get_daily_order_count,
    get_multi_item_order_stats
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stock-trend")
def get_stock_trend(
    days: int = Query(default=30, ge=7, le=365, description="天数范围"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取库存趋势数据
    
    Args:
        days: 查询天数（7-365天）
        db: 数据库会话
    
    Returns:
        {
            'data': [{'date': '2025-11-01', 'total_stock': 15234}, ...],
            'days': 30
        }
    """
    data = get_stock_trend_data(db, days)
    return {
        'data': data,
        'days': days,
        'chart_type': 'line'
    }


@router.get("/sales-trend")
def get_sales_trend(
    days: int = Query(default=30, ge=7, le=365, description="天数范围"),
    start_date: str = Query(default=None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(default=None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取销量趋势数据
    
    Args:
        days: 查询天数（7-365天）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        db: 数据库会话
    
    Returns:
        {
            'data': [{'date': '2025-11-01', 'total_sales': 234}, ...],
            'days': 30
        }
    """
    from datetime import datetime
    start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    data = get_sales_trend_data(db, days, start, end)
    return {
        'data': data,
        'days': days,
        'chart_type': 'line'
    }


@router.get("/top-products")
def get_top_products(
    limit: int = Query(default=10, ge=5, le=50, description="返回数量"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取TOP N热销产品
    
    Args:
        limit: 返回数量（5-50）
        db: 数据库会话
    
    Returns:
        {
            'data': [{'product_code': 'P001', 'product_name': '产品A', 'total_sold': 1234}, ...],
            'limit': 10
        }
    """
    data = get_top_selling_products(db, limit)
    return {
        'data': data,
        'limit': limit,
        'chart_type': 'bar'
    }


@router.get("/color-distribution")
def get_color_dist(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取SKU颜色销量分布
    
    Args:
        db: 数据库会话
    
    Returns:
        {
            'data': [{'color': '黑色', 'count': 1234, 'percentage': 35.5}, ...],
            'total': 3456
        }
    """
    data = get_color_distribution(db)
    total = sum(item['count'] for item in data)
    
    return {
        'data': data,
        'total': total,
        'chart_type': 'pie'
    }


@router.get("/batch")
def get_batch_analytics_data(
    days: int = Query(default=30, ge=7, le=365),
    start_date: str = Query(default=None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(default=None, description="结束日期 YYYY-MM-DD"),
    top_limit: int = Query(default=10, ge=5, le=50),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    批量获取所有分析数据（减少HTTP请求）
    
    Args:
        days: 趋势数据天数
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        top_limit: TOP产品数量
        db: 数据库会话
    
    Returns:
        {
            'stock_trend': {...},
            'sales_trend': {...},
            'top_products': {...},
            'color_distribution': {...}
        }
    """
    from datetime import datetime
    start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    return {
        'stock_trend': {
            'data': get_stock_trend_data(db, days),
            'days': days
        },
        'sales_trend': {
            'data': get_sales_trend_data(db, days, start, end),
            'days': days
        },
        'top_products': {
            'data': get_top_selling_products(db, top_limit, start, end, days),
            'limit': top_limit
        },
        'color_distribution': {
            'data': get_color_distribution(db),
            'total': sum(item['count'] for item in get_color_distribution(db))
        },
        'daily_orders': {
            'data': get_daily_order_count(db, days, start, end),
            'days': days
        },
        'multi_item_orders': {
            'data': get_multi_item_order_stats(db, days, start, end),
            'days': days
        }
    }
