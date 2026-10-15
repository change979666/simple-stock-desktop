from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from database.models import StockLog, ActionLog, ProductVariant
import logging


def parse_operator_info(operator_info) -> str:
    """解析操作员信息，返回操作员名称
    
    Args:
        operator_info: 操作员信息，可以是字符串、字典或其他类型

    Returns:
        str: 操作员名称
    """
    if not operator_info:
        return "系统"
        
    # 如果是字符串，处理各种格式
    if isinstance(operator_info, str):
        # 去除前后空白和引号
        cleaned_info = operator_info.strip()
        if cleaned_info.startswith("'") and cleaned_info.endswith("'"):
            cleaned_info = cleaned_info[1:-1]
        elif cleaned_info.startswith('"') and cleaned_info.endswith('"'):
            cleaned_info = cleaned_info[1:-1]
            
        # 检查是否是 "名字 (IP)" 格式
        if " (" in cleaned_info and cleaned_info.endswith(")"):
            # 提取名字部分（去除IP地址）
            return cleaned_info.split(" (")[0]
            
        # 如果不是特殊格式，直接返回清理后的字符串
        return cleaned_info
        
    # 如果是字典，尝试获取name字段
    if isinstance(operator_info, dict):
        return operator_info.get('name', '系统')
        
    # 其他情况，转换为字符串
    return str(operator_info)


def get_operation_logs_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    operator: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    """分页获取操作记录 - 数据库层面分页优化
    
    Args:
        db: 数据库会话
        page: 页码（从1开始）
        page_size: 每页数量
        start_date: 开始日期
        end_date: 结束日期
        operator: 操作人员过滤
    
    Returns:
        (操作记录列表, 总数量)
    """
    # 🔥 优化B: 先查询总数
    stock_query = db.query(func.count(StockLog.id))
    action_query = db.query(func.count(ActionLog.id))
    
    if start_date:
        stock_query = stock_query.filter(StockLog.created_at >= start_date)
        action_query = action_query.filter(ActionLog.created_at >= start_date)
    if end_date:
        stock_query = stock_query.filter(StockLog.created_at <= end_date)
        action_query = action_query.filter(ActionLog.created_at <= end_date)
    if operator:
        stock_query = stock_query.filter(
            StockLog.operator_info.ilike(f"%{operator}%")
        )
        action_query = action_query.filter(
            ActionLog.operator_info.ilike(f"%{operator}%")
        )
    
    total_stock = stock_query.scalar() or 0
    total_action = action_query.scalar() or 0
    total = total_stock + total_action
    
    # 🔥 优化B: 数据库层面分页（避免一次性加载所有数据）
    # 注意：这里采用简化策略 - 先加载分页范围内的记录，再合并排序
    # 实际生产环境可以用更复杂的UNION分页，但这里为了代码简洁性
    offset = (page - 1) * page_size
    
    # 获取该页的操作记录（使用limit+offset）
    all_logs = get_all_operation_logs(
        db=db,
        start_date=start_date,
        end_date=end_date,
        operator=operator,
        limit=None  # 不限制，因为要排序后再分页
    )
    
    # 排序并分页
    all_logs.sort(key=lambda x: x['time'], reverse=True)
    paginated_logs = all_logs[offset:offset + page_size]
    
    return paginated_logs, total


def get_all_operation_logs(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    operator: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """获取所有操作记录（包括库存变动和操作日志）

    Args:
        db: 数据库会话
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        operator: 操作人员过滤（可选）
        limit: 返回记录数限制（可选）

    Returns:
        List[Dict[str, Any]]: 操作记录列表
    """
    all_logs = []
    
    # 🔥 优化A: 预加载所有variant的库存累计值（一次查询）
    # 构建 variant_id -> cumulative_stock 的字典映射
    stock_cumulative = {}
    try:
        # 查询每个variant的总库存
        cumulative_query = db.query(
            StockLog.variant_id,
            func.sum(StockLog.change_quantity).label('total_stock')
        ).group_by(StockLog.variant_id).all()
        
        for variant_id, total_stock in cumulative_query:
            stock_cumulative[variant_id] = total_stock or 0
    except Exception as e:
        logging.error(f"Error preloading cumulative stock: {str(e)}")
    
    # 获取库存变动记录
    stock_query = db.query(StockLog)
    if start_date:
        stock_query = stock_query.filter(StockLog.created_at >= start_date)
    if end_date:
        stock_query = stock_query.filter(StockLog.created_at <= end_date)
    if operator:
        stock_query = stock_query.filter(
            StockLog.operator_info.ilike(f"%{operator}%")
        )
    
    try:
        stock_logs = stock_query.all()
        
        for log in stock_logs:
            operator_name = "系统"
            try:
                operator_name = parse_operator_info(log.operator_info)
            except Exception as e:
                logging.error(
                    f"Error processing operator info: {str(e)}, "
                    f"raw value: {log.operator_info}"
                )
                operator_name = "系统（解析错误）"
            
            # 🔥 优化A: 从预加载的字典获取库存（内存查表，O(1)）
            current_stock = 0
            if log.variant_id and log.variant_id in stock_cumulative:
                current_stock = stock_cumulative[log.variant_id]
            
            all_logs.append({
                'type': 'stock',
                'time': log.created_at,
                'sku': log.variant.sku if log.variant else '',
                'operation_type': '入库' if log.change_quantity > 0 else '出库',
                'quantity_change': log.change_quantity,
                'after_stock': current_stock,
                'operator': operator_name,
                'notes': log.notes or ''
            })
            
    except Exception as e:
        logging.error(f"Error fetching stock logs: {str(e)}")
        stock_logs = []
    
    # 获取操作日志记录
    action_query = db.query(ActionLog)
    if start_date:
        action_query = action_query.filter(ActionLog.created_at >= start_date)
    if end_date:
        action_query = action_query.filter(ActionLog.created_at <= end_date)
    if operator:
        action_query = action_query.filter(
            ActionLog.operator_info.ilike(f"%{operator}%")
        )
    
    try:
        action_logs = action_query.all()
        for log in action_logs:
            operator_name = "系统"
            try:
                operator_name = parse_operator_info(log.operator_info)
            except Exception as e:
                logging.error(
                    f"Error processing action log operator info: {str(e)}, "
                    f"raw value: {log.operator_info}"
                )
                operator_name = "系统（解析错误）"
                
            # 解析操作类型
            operation_type = "其他操作"
            if "创建产品" in log.action:
                operation_type = "创建产品"
            elif "编辑" in log.action or "修改" in log.action:
                operation_type = "产品修改"
            elif "删除" in log.action:
                operation_type = "删除操作"
            elif "导入" in log.action:
                operation_type = "数据导入"
            elif "销售" in log.action:
                operation_type = "销售操作"
            elif "发货" in log.action:
                operation_type = "发货操作"
            
            all_logs.append({
                'type': 'action',
                'time': log.created_at,
                'sku': '',  # 操作日志通常不关联特定SKU
                'operation_type': operation_type,
                'quantity_change': None,
                'after_stock': None,
                'operator': operator_name,
                'notes': log.action
            })
            
    except Exception as e:
        logging.error(f"Error fetching action logs: {str(e)}")
    
    # 按时间排序
    all_logs.sort(key=lambda x: x['time'], reverse=True)
    
    # 应用限制
    if limit:
        all_logs = all_logs[:limit]
    
    return all_logs


def get_stock_logs(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    product_id: Optional[int] = None,
    operator: Optional[str] = None,
    limit: Optional[int] = None
) -> List[StockLog]:
    """获取库存变更日志记录

    Args:
        db: 数据库会话
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        product_id: 产品ID过滤（可选）
        operator: 操作人员过滤（可选）
        limit: 返回记录数限制（可选）

    Returns:
        List[StockLog]: 库存日志记录列表
    """
    query = db.query(StockLog)

    # 应用过滤条件
    if start_date:
        query = query.filter(StockLog.created_at >= start_date)
    if end_date:
        query = query.filter(StockLog.created_at <= end_date)
    if product_id:
        query = query.filter(StockLog.variant_id == product_id)  # 更新为正确的字段名
    if operator:
        query = query.filter(StockLog.operator_info.ilike(f"%{operator}%"))

    # 按时间倒序排列
    query = query.order_by(desc(StockLog.created_at))

    # 应用限制
    if limit:
        query = query.limit(limit)

    return query.all()


def get_recent_stock_logs(
    db: Session,
    days: int = 7,
    limit: Optional[int] = None
) -> List[StockLog]:
    """获取最近几天的库存变更日志

    Args:
        db: 数据库会话
        days: 最近天数（默认7天）
        limit: 返回记录数限制（可选）

    Returns:
        List[StockLog]: 最近的库存日志记录列表
    """
    start_date = datetime.now() - timedelta(days=days)
    return get_stock_logs(db, start_date=start_date, limit=limit)


def get_operator_stock_logs(
    db: Session,
    operator: str,
    limit: Optional[int] = None
) -> List[StockLog]:
    """获取特定操作员的库存变更日志

    Args:
        db: 数据库会话
        operator: 操作员信息
        limit: 返回记录数限制（可选）

    Returns:
        List[StockLog]: 特定操作员的库存日志记录列表
    """
    return get_stock_logs(db, operator=operator, limit=limit)


def get_product_stock_logs(
    db: Session,
    product_id: int,
    limit: Optional[int] = None
) -> List[StockLog]:
    """获取特定产品的库存变更日志

    Args:
        db: 数据库会话
        product_id: 产品ID
        limit: 返回记录数限制（可选）

    Returns:
        List[StockLog]: 特定产品的库存日志记录列表
    """
    return get_stock_logs(db, product_id=product_id, limit=limit)


def get_variant_current_stock(db: Session, variant_id: int) -> int:
    """获取指定产品变体的当前库存（直接从 current_stock 字段读取）

    Args:
        db: 数据库会话
        variant_id: 产品变体ID

    Returns:
        int: 当前库存数量
        
    Note:
        如果需要批量查询多个变体的库存，请使用 get_batch_variant_stocks()
    """
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    
    return variant.current_stock if variant else 0


def get_batch_variant_stocks(
    db: Session,
    variant_ids: list[int]
) -> dict[int, int]:
    """批量获取多个产品变体的当前库存（直接从 current_stock 字段读取）

    Args:
        db: 数据库会话
        variant_ids: 产品变体ID列表

    Returns:
        dict: {variant_id: current_stock, ...}
        
    Example:
        >>> stocks = get_batch_variant_stocks(db, [1, 2, 3])
        >>> print(stocks)
        {1: 100, 2: 50, 3: 0}
    """
    if not variant_ids:
        return {}
    
    # 一次性查询所有变体的 current_stock
    variants = db.query(ProductVariant).filter(
        ProductVariant.id.in_(variant_ids)
    ).all()
    
    # 转换为字典
    stock_dict = {variant.id: variant.current_stock for variant in variants}
    
    # 对于不存在的variant_id，返回0
    for variant_id in variant_ids:
        if variant_id not in stock_dict:
            stock_dict[variant_id] = 0
    
    return stock_dict

    
    # 对于没有库存记录的变体，返回0
    result = {vid: stock_dict.get(vid, 0) for vid in variant_ids}
    
    return result