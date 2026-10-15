"""
发货管理API路由
提供发货记录的CRUD操作
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
import math

from database.session import get_db
from crud.shipment_operations import (
    get_shipments,
    get_shipments_paginated,
    create_shipment,
    get_shipment_by_id,
    update_shipment_status,
    delete_shipment
)
from crud.operations import create_action_log

router = APIRouter(prefix="/shipments", tags=["shipments"])


# ============ 请求/响应模型 ============

class ShipmentItemCreate(BaseModel):
    """发货项创建模型"""
    variant_id: int
    quantity: int


class ShipmentCreate(BaseModel):
    """发货记录创建模型 - 与GUI格式匹配"""
    sku: str  # GUI传递SKU而不是variant_id
    quantity: int
    batch_number: str
    tracking_number: Optional[str] = None
    estimated_arrival: Optional[str] = None  # ISO格式日期字符串
    notes: Optional[str] = None
    operator_info: dict  # GUI传递字典格式的操作者信息


class ShipmentUpdate(BaseModel):
    """发货记录更新模型"""
    status: Optional[str] = None
    destination: Optional[str] = None
    notes: Optional[str] = None


# ============ API端点 ============

@router.get("/paginated")
def get_shipments_paginated_api(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sku: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    分页获取发货记录列表
    
    参数:
    - page: 页码（从1开始）
    - page_size: 每页数量（默认50）
    - status: 发货状态筛选
    - start_date: 创建开始日期
    - end_date: 创建结束日期
    - sku: SKU搜索（模糊匹配）
    
    返回:
    {
        "items": [...],
        "total": 总数量,
        "page": 当前页,
        "page_size": 每页数量,
        "total_pages": 总页数
    }
    """
    try:
        # 转换日期为datetime
        start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        # 调用CRUD层分页查询
        shipments, total = get_shipments_paginated(
            db=db,
            page=page,
            page_size=page_size,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            sku=sku
        )
        
        # 计算总页数
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        
        # 转换为字典格式
        items = []
        for shipment in shipments:
            shipment_dict = {
                'id': shipment.id,
                'batch_number': shipment.batch_number,
                'status': shipment.status.value if hasattr(shipment.status, 'value') else str(shipment.status),
                'estimated_arrival': shipment.estimated_arrival.isoformat() if shipment.estimated_arrival else None,
                'arrival_date': shipment.arrival_date.isoformat() if shipment.arrival_date else None,
                'operator': shipment.operator,
                'created_at': shipment.created_at.isoformat() if shipment.created_at else None,
                'updated_at': shipment.updated_at.isoformat() if shipment.updated_at else None,
                'notes': shipment.notes,
                'shipment_items': []
            }
            
            # 添加发货项
            for item in shipment.shipment_items:
                shipment_dict['shipment_items'].append({
                    'id': item.id,
                    'quantity': item.quantity,
                    'tracking_number': item.tracking_number,
                    'variant': {
                        'id': item.variant.id,
                        'sku': item.variant.sku,
                        'parent_sku': item.variant.product.parent_sku if item.variant.product else None,
                        'current_stock': item.variant.current_stock
                    }
                })
            
            items.append(shipment_dict)
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def get_shipments_list(
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    destination: Optional[str] = None,
    sku: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取发货记录列表（支持服务端过滤）【已弃用，请使用/paginated端点】
    
    参数:
    - status: 发货状态筛选（pending/in_transit/arrived/shelved/cancelled）
    - start_date: 创建开始日期（YYYY-MM-DD）
    - end_date: 创建结束日期（YYYY-MM-DD）
    - destination: 目的地搜索（模糊匹配）
    - sku: SKU搜索（模糊匹配，过滤包含指定SKU的发货记录）
    """
    from sqlalchemy import text
    
    # 使用原始SQL查询避免枚举转换问题
    query = """
        SELECT 
            id, batch_number, status, estimated_arrival, 
            arrival_date, operator, created_at, updated_at, notes
        FROM inventory_shipments
        WHERE 1=1
    """
    params = {}
    
    # 状态过滤
    if status:
        query += " AND status = :status"
        params['status'] = status
    
    # 日期范围过滤
    if start_date:
        query += " AND date(created_at) >= :start_date"
        params['start_date'] = start_date
    if end_date:
        query += " AND date(created_at) <= :end_date"
        params['end_date'] = end_date
    
    # SKU过滤（需要JOIN shipment_items和product_variants）
    if sku:
        query = query.replace(
            "WHERE 1=1",
            """WHERE id IN (
                SELECT DISTINCT si.shipment_id 
                FROM shipment_items si
                JOIN product_variants pv ON si.variant_id = pv.id
                WHERE pv.sku LIKE :sku
            ) AND 1=1"""
        )
        params['sku'] = f'%{sku}%'
    
    query += " ORDER BY created_at DESC"
    
    result = db.execute(text(query), params)
    rows = result.fetchall()
    
    # 手动构建返回数据
    shipments_list = []
    for row in rows:
        shipment_id = row[0]
        
        # 查询发货明细
        items_query = text("""
            SELECT si.id, si.variant_id, si.quantity, si.tracking_number,
                   pv.sku, p.name as product_name
            FROM shipment_items si
            LEFT JOIN product_variants pv ON si.variant_id = pv.id
            LEFT JOIN products p ON pv.product_id = p.id
            WHERE si.shipment_id = :shipment_id
        """)
        items_result = db.execute(items_query, {'shipment_id': shipment_id})
        items_rows = items_result.fetchall()
        
        shipment_items = []
        for item_row in items_rows:
            shipment_items.append({
                'id': item_row[0],
                'variant_id': item_row[1],
                'quantity': item_row[2],
                'tracking_number': item_row[3] or '',
                'sku': item_row[4] or '',
                'product_name': item_row[5] or '',
                'variant': {'sku': item_row[4] or ''}
            })
        
        shipment_dict = {
            'id': row[0],
            'batch_number': row[1] or '',
            'shipment_number': row[1] or '',
            'status': row[2] or 'pending',
            'estimated_arrival': row[3] if row[3] else None,
            'destination': '',
            'notes': row[8] or '',
            'created_at': row[6] if row[6] else None,
            'shipment_items': shipment_items,
            'items': shipment_items
        }
        shipments_list.append(shipment_dict)
    
    return shipments_list
    
    # 转换为字典格式
    result = []
    for shipment in shipments:
        shipment_dict = {
            'id': shipment.id,
            'batch_number': shipment.batch_number,  # 返回batch_number字段名
            'shipment_number': shipment.batch_number,  # 兼容性:同时保留shipment_number
            'destination': getattr(shipment, 'destination', ''),  # 兼容旧数据库
            'estimated_arrival': getattr(shipment, 'estimated_arrival', None),  # 添加预计到货日期
            'status': shipment.status,
            'notes': shipment.notes,
            'created_at': (shipment.created_at.isoformat() 
                          if shipment.created_at else None),
            'shipment_items': [],  # 使用shipment_items字段名
            'items': []  # 兼容性:同时保留items
        }
        
        # 使用shipment_items而不是items
        items = getattr(shipment, 'shipment_items', [])
        for item in items:
            item_dict = {
                'id': item.id,
                'variant_id': item.variant_id,
                'sku': item.variant.sku if item.variant else None,
                'product_name': (item.variant.product.name 
                                if item.variant and item.variant.product 
                                else None),
                'quantity': item.quantity,
                'tracking_number': getattr(item, 'tracking_number', '')  # 添加物流单号
            }
            # 同时添加到两个字段中
            shipment_dict['shipment_items'].append(item_dict)
            shipment_dict['items'].append(item_dict)
        
        # 添加variant对象以兼容GUI代码
    return shipments_list


@router.post("")
def create_new_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db)
):
    """创建发货记录 - 匹配GUI发送的格式"""
    try:
        from crud.operations import get_variant_by_sku
        
        # 通过SKU获取variant_id
        variant = get_variant_by_sku(db, shipment.sku)
        if not variant:
            raise HTTPException(
                status_code=404,
                detail=f"SKU {shipment.sku} 不存在"
            )
        
        # 准备发货项数据
        items_data = [{
            'variant_id': variant.id,
            'quantity': shipment.quantity
        }]
        
        # 创建发货记录
        new_shipment = create_shipment(
            db=db,
            shipment_number=shipment.batch_number,
            destination=shipment.tracking_number or '默认目的地',  # 使用tracking_number作为destination
            items=items_data,
            notes=shipment.notes,
            operator_info=shipment.operator_info
        )
        
        # 记录操作日志
        import json
        operator_dict = (
            json.loads(shipment.operator_info)
            if isinstance(shipment.operator_info, str)
            else shipment.operator_info
        )
        
        create_action_log(
            db=db,
            operator_info=operator_dict,
            action=f'创建发货记录: {new_shipment.batch_number}'
        )
        
        # create_shipment已经commit，这里不需要
        
        return {
            "message": "发货记录创建成功",
            "shipment_id": new_shipment.id,
            "shipment_number": new_shipment.batch_number,
            "batch_number": shipment.batch_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/in-transit")
def get_in_transit_inventory_api(
    sku: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取在途库存数量
    
    Args:
        sku: 可选，指定SKU
        
    Returns:
        字典，key为SKU，value为在途数量
    """
    from crud.shipment_operations import get_in_transit_inventory
    
    result = get_in_transit_inventory(db, sku)
    return result


@router.get("/{shipment_id}")
def get_shipment_detail(
    shipment_id: int,
    db: Session = Depends(get_db)
):
    """获取发货详情"""
    shipment = get_shipment_by_id(db, shipment_id)
    
    if not shipment:
        raise HTTPException(status_code=404, detail="发货记录不存在")
    
    return {
        'id': shipment.id,
        'shipment_number': shipment.batch_number,  # 使用batch_number
        'destination': getattr(shipment, 'destination', ''),  # 兼容旧数据库
        'status': shipment.status,
        'notes': shipment.notes,
        'created_at': (shipment.created_at.isoformat() 
                      if shipment.created_at else None),
        'items': [
            {
                'id': item.id,
                'variant_id': item.variant_id,
                'sku': item.variant.sku if item.variant else None,
                'product_name': (item.variant.product.name 
                                if item.variant and item.variant.product 
                                else None),
                'quantity': item.quantity
            }
            for item in getattr(shipment, 'shipment_items', [])
        ]
    }


@router.put("/{shipment_id}")
def update_shipment(
    shipment_id: int,
    shipment: ShipmentUpdate,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """更新发货记录"""
    db_shipment = get_shipment_by_id(db, shipment_id)
    
    if not db_shipment:
        raise HTTPException(status_code=404, detail="发货记录不存在")
    
    # 更新字段
    if shipment.status is not None:
        update_shipment_status(db, shipment_id, shipment.status)
    
    # destination字段在旧数据库中不存在,跳过
    # if shipment.destination is not None:
    #     db_shipment.destination = shipment.destination
    if shipment.notes is not None:
        db_shipment.notes = shipment.notes
    
    # 记录操作日志
    import urllib.parse
    decoded_operator = urllib.parse.unquote(operator_info)
    operator_dict = {
        'display': decoded_operator,
        'operator': decoded_operator
    }
    
    create_action_log(
        db=db,
        operator_info=operator_dict,
        action=f'更新发货记录: {db_shipment.batch_number}'
    )
    
    db.commit()  # 这里需要commit，因为上面的修改和update_shipment_status
    
    return {"message": "发货记录更新成功"}


@router.delete("/{shipment_id}")
def delete_shipment_record(
    shipment_id: int,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """删除发货记录"""
    shipment = get_shipment_by_id(db, shipment_id)
    
    if not shipment:
        raise HTTPException(status_code=404, detail="发货记录不存在")
    
    shipment_number = shipment.batch_number  # 使用batch_number
    
    # 记录操作日志
    # operator_info是URL编码的字符串,需要转换为字典
    import urllib.parse
    decoded_operator = urllib.parse.unquote(operator_info)
    operator_dict = {
        'display': decoded_operator,
        'operator': decoded_operator
    }
    
    create_action_log(
        db=db,
        operator_info=operator_dict,
        action=f'删除发货记录: {shipment_number}'
    )
    
    delete_shipment(db, shipment_id)
    # delete_shipment已经commit，这里不需要
    
    return {"message": "发货记录删除成功"}


@router.patch("/{shipment_id}/status")
def update_shipment_status_endpoint(
    shipment_id: int,
    status: str,
    operator_info: str,
    db: Session = Depends(get_db)
):
    """更新发货状态
    
    支持的状态转换:
    - PENDING -> IN_TRANSIT (标记为运输中)
    - IN_TRANSIT -> ARRIVED (标记为已到货)
    - ARRIVED -> SHELVED (标记为已上架,会创建入库记录)
    - 任意状态 -> CANCELLED (取消发货)
    """
    from database.inventory import ShipmentStatus
    import json
    
    try:
        shipment = get_shipment_by_id(db, shipment_id)
        if not shipment:
            raise HTTPException(status_code=404, detail="发货记录不存在")
        
        # 解析操作者信息
        try:
            if isinstance(operator_info, str):
                if operator_info.startswith('{'):
                    operator_dict = json.loads(operator_info)
                else:
                    # 简单字符串,转换为dict
                    operator_dict = {"display": operator_info, "operator": operator_info}
            else:
                operator_dict = operator_info
        except json.JSONDecodeError:
            operator_dict = {"display": operator_info, "operator": operator_info}
        
        old_status = shipment.status
        
        # 将字符串状态转换为枚举值
        try:
            # 首先尝试作为枚举名称(CANCELLED)
            if hasattr(ShipmentStatus, status):
                new_status_enum = getattr(ShipmentStatus, status)
            # 否则尝试作为枚举值(cancelled)
            else:
                new_status_enum = ShipmentStatus(status.lower())
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"无效的状态值: {status}. 错误: {str(e)}"
            )
        
        # 上架需要创建入库记录
        if new_status_enum == ShipmentStatus.SHELVED:
            from crud.operations import create_stock_log
            for item in shipment.shipment_items:
                create_stock_log(
                    db,
                    variant_id=item.variant_id,
                    change_quantity=item.quantity,
                    notes=f'发货到货入库 (追踪号: {item.tracking_number or ""})',
                    operator_info=operator_dict
                )
                create_action_log(
                    db,
                    operator_dict,
                    f'发货入库: {item.variant.sku} ({item.quantity} 件)'
                )
        
        # 提交库存日志和操作日志
        if new_status_enum == ShipmentStatus.SHELVED:
            db.commit()
        
        # 使用crud函数更新状态
        from crud.shipment_operations import (
            update_shipment_status as crud_update_status
        )
        crud_update_status(db, shipment_id, new_status_enum)
        
        # 记录操作日志
        create_action_log(
            db,
            operator_dict,
            f'发货状态变更: {shipment.batch_number} ({old_status} -> {status})'
        )
        
        # crud_update_status已经commit，这里不需要
        
        return {
            "message": "状态更新成功",
            "old_status": old_status,
            "new_status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"状态更新失败: {str(e)}")


@router.post("/import")
def import_shipments_endpoint(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """批量导入发货记录"""
    from crud.shipment_operations import import_shipments
    import json
    
    shipments = data.get('shipments', [])
    operator_info = data.get('operator_info', '{}')
    
    operator_dict = json.loads(operator_info) if isinstance(
        operator_info, str) else operator_info
    result = import_shipments(db, shipments, operator_dict)
    return result


@router.put("/items/{item_id}")
def update_shipment_item_endpoint(
    item_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """更新发货项（修改SKU或数量）
    
    Args:
        item_id: 发货项ID
        data: {'variant_id': int, 'quantity': int, 'tracking_number': str}
    """
    from database.models import ShipmentItem
    
    item = db.query(ShipmentItem).filter(
        ShipmentItem.id == item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="发货项不存在")
    
    # 更新字段
    if 'variant_id' in data:
        item.variant_id = data['variant_id']
    if 'quantity' in data:
        item.quantity = data['quantity']
    if 'tracking_number' in data:
        item.tracking_number = data['tracking_number']
    
    db.commit()  # 这里需要commit，因为上面的修改没有在CRUD层
    
    return {"message": "发货项更新成功"}
