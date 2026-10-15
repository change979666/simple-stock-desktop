"""操作日志相关API路由"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict
from datetime import datetime
import json

from database.session import get_db
from crud.operations import create_action_log

router = APIRouter(tags=["Logs"])


@router.get("/operations/paginated")
def get_operation_logs_paginated_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    operator: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """分页获取操作日志
    
    Args:
        page: 页码（从1开始）
        page_size: 每页数量
        start_date: 开始日期（格式：YYYY-MM-DD HH:MM:SS）
        end_date: 结束日期（格式：YYYY-MM-DD HH:MM:SS）
        operator: 操作人员筛选
    
    Returns:
        {
            'items': [...],
            'total': 总数量,
            'page': 当前页,
            'page_size': 每页数量,
            'total_pages': 总页数
        }
    """
    from crud.inventory_logs import get_operation_logs_paginated
    import math
    
    # 解析日期
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace(' ', 'T'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的开始日期格式: {start_date}"
            )
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace(' ', 'T'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的结束日期格式: {end_date}"
            )
    
    # 获取分页日志
    logs, total = get_operation_logs_paginated(
        db=db,
        page=page,
        page_size=page_size,
        start_date=start,
        end_date=end,
        operator=operator
    )
    
    # 计算总页数
    total_pages = math.ceil(total / page_size) if page_size > 0 else 0
    
    return {
        'items': logs,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    }


@router.get("/operations")
def get_operation_logs_api(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取库存操作日志（非分页，保留兼容性）
    
    Args:
        start_date: 开始日期（格式：YYYY-MM-DD HH:MM:SS）
        end_date: 结束日期（格式：YYYY-MM-DD HH:MM:SS）
        action_type: 操作类型筛选
    """
    from crud.inventory_logs import get_all_operation_logs
    
    # 解析日期
    start = None
    end = None
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace(' ', 'T'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的开始日期格式: {start_date}"
            )
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace(' ', 'T'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的结束日期格式: {end_date}"
            )
    
    # 获取日志
    logs = get_all_operation_logs(db, start_date=start, end_date=end)
    
    # 转换为JSON兼容格式
    result = []
    for log in logs:
        log_dict = {
            'id': log.get('id'),
            'sku': log.get('sku'),
            'product_name': log.get('product_name'),
            'quantity_change': log.get('quantity_change'),
            'after_stock': log.get('after_stock'),
            'operation_type': log.get('operation_type'),
            'notes': log.get('notes'),
            'operator': log.get('operator'),
            'time': log.get('time').isoformat() if log.get('time') else None
        }
        
        # 如果指定了action_type，进行筛选
        if action_type and log_dict['operation_type'] != action_type:
            continue
            
        result.append(log_dict)
    
    return result


@router.get("/actions")
def get_action_logs_api(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """获取操作动作日志
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
    """
    from database.models.log import ActionLog
    
    query = db.query(ActionLog)
    
    # 日期筛选
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace(' ', 'T'))
            query = query.filter(ActionLog.timestamp >= start)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的开始日期格式: {start_date}"
            )
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace(' ', 'T'))
            query = query.filter(ActionLog.timestamp <= end)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的结束日期格式: {end_date}"
            )
    
    logs = query.order_by(ActionLog.timestamp.desc()).all()
    
    # 转换为字典格式
    result = []
    for log in logs:
        result.append({
            'id': log.id,
            'operator_info': log.operator_info,
            'action': log.action,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        })
    
    return result


@router.post("/actions")
def create_action_log_api(
    data: Dict = Body(...),
    db: Session = Depends(get_db)
):
    """创建操作日志
    
    Args:
        data: 包含 action, details, operator_info 的字典
        db: 数据库会话
        
    Returns:
        {'success': True, 'message': '操作日志创建成功'}
    """
    try:
        action = data.get('action')
        details = data.get('details')
        operator_info = data.get('operator_info')
        # create_action_log signature: create_action_log(db, operator_info, action)
        # 调用时传入 operator_info 和 action，details 不属于该函数参数
        create_action_log(db, operator_info, action)
        db.commit()  # create_action_log使用flush不commit，这里需要
        
        return {
            'success': True,
            'message': '操作日志创建成功'
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建操作日志失败: {str(e)}"
        )


@router.get("/operations/count")
def get_operation_logs_count_api(
    cutoff_date: str = Query(..., description="截止日期（ISO格式）"),
    db: Session = Depends(get_db)
):
    """获取指定日期之前的操作日志数量（清空前预览）
    
    Args:
        cutoff_date: 截止日期（ISO格式）
        db: 数据库会话
        
    Returns:
        {'count': int}
    """
    try:
        from database.models import ActionLog
        
        # 解析截止日期
        cutoff = datetime.fromisoformat(cutoff_date)
        
        # 统计将要删除的 ActionLog 数量
        count = db.query(ActionLog).filter(
            ActionLog.created_at < cutoff
        ).count()
        
        return {
            'count': count
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {e}")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询操作日志数量失败: {str(e)}"
        )


@router.delete("/operations/clear")
def clear_old_logs_api(
    cutoff_date: str = Query(...),
    operator_info: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """清空指定日期之前的操作审计日志（不影响库存数据）
    
    ⚠️ 重要说明：
    - 只删除 ActionLog（操作审计日志）
    - 不删除 StockLog（库存变动记录，用于计算当前库存）
    - 不影响任何业务数据（产品、库存、订单等）
    
    Args:
        cutoff_date: 截止日期（ISO格式）
        operator_info: 操作员信息（JSON字符串）
        db: 数据库会话
        
    Returns:
        {'success': True, 'deleted_count': int, 'message': str}
    """
    try:
        from database.models import ActionLog
        
        # 解析截止日期
        cutoff = datetime.fromisoformat(cutoff_date)
        
        # ⚠️ 重要：只删除 ActionLog（操作日志），不删除 StockLog
        # StockLog 是库存变动记录，用于计算当前库存，不能删除！
        
        # 删除旧的操作日志
        deleted_action_logs = db.query(ActionLog).filter(
            ActionLog.created_at < cutoff
        ).delete()
        
        total_deleted = deleted_action_logs
        
        # 记录清空操作
        operator_dict = None
        if operator_info:
            if isinstance(operator_info, str):
                try:
                    operator_dict = json.loads(operator_info)
                except (json.JSONDecodeError, TypeError):
                    # 不是 JSON 字符串，直接使用原始字符串（或包装为 display）
                    operator_dict = operator_info
            else:
                operator_dict = operator_info

        # create_action_log(db, operator_info, action)
        action_message = (
            f'清空{cutoff.strftime("%Y-%m-%d")}之前的操作记录，'
            f'共删除{total_deleted}条'
        )
        create_action_log(db, operator_dict, action_message)
        
        db.commit()  # 这里需要commit，因为上面的删除操作
        
        return {
            'success': True,
            'deleted_count': total_deleted,
            'message': f'成功清空{total_deleted}条记录'
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"无效的日期格式: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"清空操作记录失败: {str(e)}"
        )
