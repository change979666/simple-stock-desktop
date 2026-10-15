"""
库存管理API路由  
提供库存查询、调整和日志查询操作
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from database.session import get_db
from crud.inventory_logs import get_all_operation_logs, get_variant_current_stock
from crud.operations import create_stock_log, get_variant_by_sku, create_action_log


class InventoryAdjust(BaseModel):
    """库存调整请求模型"""
    sku: str
    quantity: int  # 正数为入库,负数为出库
    notes: str
    operator_info: dict


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("")
def get_inventory_list():
    """获取库存列表"""
    return {"message": "库存管理API - 待实现"}


@router.get("/warnings")
def get_inventory_warnings():
    """获取库存预警"""
    return {"message": "库存预警API - 待实现"}


@router.post("/adjust")
def adjust_inventory(
    adjust: InventoryAdjust,
    db: Session = Depends(get_db)
):
    """手动调整库存
    
    Args:
        adjust: 调整信息(sku, quantity, notes, operator_info)
        db: 数据库会话
        
    Returns:
        调整结果
    """
    try:
        # 获取变体
        variant = get_variant_by_sku(db, adjust.sku)
        if not variant:
            raise HTTPException(status_code=404, detail=f"SKU {adjust.sku} 不存在")
        
        # 处理operator_info（可能是dict或str）
        import json
        operator_dict = (
            adjust.operator_info
            if isinstance(adjust.operator_info, dict)
            else json.loads(adjust.operator_info)
        )
        
        # 记录库存日志
        log = create_stock_log(
            db,
            variant.id,
            adjust.quantity,
            adjust.notes,
            operator_dict
        )
        
        # 记录操作日志
        action_text = f"库存调整: SKU {adjust.sku}, 数量 {adjust.quantity:+d}"
        create_action_log(db, operator_dict, action_text)
        
        # 提交事务
        db.commit()
        
        # 计算调整后的库存
        new_stock = get_variant_current_stock(db, variant.id)
        
        return {
            "message": "库存调整成功",
            "sku": adjust.sku,
            "variant_id": variant.id,
            "quantity_change": adjust.quantity,
            "new_stock": new_stock,
            "log_id": log.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"库存调整失败: {str(e)}")


@router.get("/logs")
def get_operation_logs(
    start_date: Optional[str] = Query(None, description="开始日期 (ISO格式)"),
    end_date: Optional[str] = Query(None, description="结束日期 (ISO格式)"),
    db: Session = Depends(get_db)
):
    """获取库存操作日志
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        db: 数据库会话
        
    Returns:
        操作日志列表
    """
    try:
        # 转换日期参数
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        # 获取日志
        logs = get_all_operation_logs(db, start_date=start, end_date=end)
        
        # 转换为可序列化的格式
        result = []
        for log in logs:
            result.append({
                'id': log.get('id'),
                'time': log['time'].isoformat() if log.get('time') else None,
                'sku': log.get('sku'),
                'quantity_change': log.get('quantity_change'),
                'notes': log.get('notes'),
                'operator': log.get('operator')
            })
        
        return {"logs": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取操作日志失败: {str(e)}")
