from typing import List, Optional, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from database.models import (
    InventoryShipment, ShipmentItem, ProductVariant
)
from database.inventory import ShipmentStatus

# 导入数据变更跟踪器
from utils.data_change_tracker import mark_data_changed


def get_shipments_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sku: Optional[str] = None
) -> Tuple[List[InventoryShipment], int]:
    """
    分页获取发货记录
    
    Args:
        db: 数据库会话
        page: 页码（从1开始）
        page_size: 每页数量
        status: 状态过滤
        start_date: 开始日期
        end_date: 结束日期
        sku: SKU搜索（模糊匹配）
    
    Returns:
        (发货记录列表, 总数量)
    """
    query = db.query(InventoryShipment).options(
        joinedload(InventoryShipment.shipment_items)
        .joinedload(ShipmentItem.variant)
    )
    
    # 状态过滤
    if status:
        query = query.filter(InventoryShipment.status == status)
    
    # 日期范围过滤
    if start_date:
        query = query.filter(InventoryShipment.created_at >= start_date)
    if end_date:
        query = query.filter(InventoryShipment.created_at <= end_date)
    
    # SKU过滤（关联shipment_items和variants）
    if sku:
        query = query.join(InventoryShipment.shipment_items)\
                     .join(ShipmentItem.variant)\
                     .filter(ProductVariant.sku.ilike(f'%{sku}%'))\
                     .distinct()
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    offset = (page - 1) * page_size
    shipments = query.order_by(InventoryShipment.created_at.desc())\
                     .offset(offset)\
                     .limit(page_size)\
                     .all()
    
    return shipments, total


def get_all_shipments(db: Session) -> List[InventoryShipment]:
    """获取所有发货记录，按时间降序排序"""
    return (
        db.query(InventoryShipment)
        .options(
            joinedload(InventoryShipment.shipment_items)
            .joinedload(ShipmentItem.variant)
        )
        .order_by(InventoryShipment.created_at.desc())
        .all()
    )


def get_shipment(db: Session, shipment_id: int) -> Optional[InventoryShipment]:
    """通过ID获取单个发货记录"""
    return db.query(InventoryShipment).get(shipment_id)


def get_shipments_by_status(
    db: Session,
    status: ShipmentStatus
) -> List[InventoryShipment]:
    """获取特定状态的所有发货记录"""
    return (
        db.query(InventoryShipment)
        .filter(InventoryShipment.status == status)
        .options(
            joinedload(InventoryShipment.shipment_items)
            .joinedload(ShipmentItem.variant)
        )
        .order_by(InventoryShipment.created_at.desc())
        .all()
    )


def update_shipment_status(
    db: Session,
    shipment_id: int,
    new_status: ShipmentStatus,
    arrival_date: Optional[datetime] = None
) -> Optional[InventoryShipment]:
    """更新发货记录状态"""
    from sqlalchemy import text
    
    # 使用原始SQL更新,避免枚举类型问题
    status_value = new_status.value if hasattr(new_status, 'value') else str(new_status)
    
    db.execute(
        text('UPDATE inventory_shipments SET status = :status WHERE id = :id'),
        {'status': status_value, 'id': shipment_id}
    )
    
    if arrival_date:
        db.execute(
            text('UPDATE inventory_shipments SET arrival_date = :date WHERE id = :id'),
            {'date': arrival_date, 'id': shipment_id}
        )
    
    db.commit()
    
    # 重新查询并返回
    shipment = get_shipment(db, shipment_id)
    
    # 标记数据已变更
    if shipment:
        mark_data_changed(f"update_shipment_status: {shipment.batch_number}")
    
    return shipment


def get_shipments(db: Session, **filters) -> List[InventoryShipment]:
    """获取发货记录列表
    
    Args:
        filters: 筛选条件
            - status: 发货状态
            - start_date: 开始日期
            - end_date: 结束日期
            - destination: 目的地
    """
    query = db.query(InventoryShipment)
    
    if 'status' in filters:
        query = query.filter(InventoryShipment.status == filters['status'])
    
    if 'start_date' in filters:
        query = query.filter(
            InventoryShipment.created_at >= filters['start_date']
        )
    
    if 'end_date' in filters:
        query = query.filter(
            InventoryShipment.created_at <= filters['end_date']
        )
    
    if 'destination' in filters:
        query = query.filter(
            InventoryShipment.destination.like(f"%{filters['destination']}%")
        )
    
    return query.order_by(InventoryShipment.created_at.desc()).all()


def get_shipment_by_id(
    db: Session,
    shipment_id: int
) -> Optional[InventoryShipment]:
    """根据ID获取发货记录"""
    return db.query(InventoryShipment).filter(
        InventoryShipment.id == shipment_id
    ).first()


def create_shipment(
    db: Session,
    shipment_number: str,
    destination: str,
    items: List[dict],
    notes: str = None,
    operator_info: str = None
) -> InventoryShipment:
    """创建发货记录
    
    Args:
        db: 数据库会话
        shipment_number: 发货单号(存入batch_number字段)
        destination: 目的地(存入notes字段)
        items: 发货项列表，每项包含：
            - variant_id: 产品变体ID
            - quantity: 数量
        notes: 备注
        operator_info: 操作者信息
    """
    # 创建发货记录 - 注意：数据库模型只有batch_number字段
    combined_notes = f"{destination} | {notes}" if notes else destination
    shipment = InventoryShipment(
        batch_number=shipment_number,  # 使用batch_number字段
        status=ShipmentStatus.PENDING.value,  # 转换为字符串
        notes=combined_notes,  # destination合并到notes
        operator=str(operator_info) if operator_info else ''
    )
    db.add(shipment)
    db.flush()  # 获取shipment.id
    
    # 创建发货项
    for item_data in items:
        item = ShipmentItem(
            shipment_id=shipment.id,
            variant_id=item_data['variant_id'],
            quantity=item_data['quantity']
        )
        db.add(item)
    
    db.commit()
    db.refresh(shipment)
    
    # 标记数据已变更
    mark_data_changed(f"create_shipment: {shipment_number}")
    
    return shipment


def delete_shipment(db: Session, shipment_id: int):
    """删除发货记录"""
    shipment = db.query(InventoryShipment).filter(
        InventoryShipment.id == shipment_id
    ).first()
    
    if shipment:
        batch_number = shipment.batch_number
        # 先删除发货项
        db.query(ShipmentItem).filter(
            ShipmentItem.shipment_id == shipment_id
        ).delete()
        # 再删除发货记录
        db.delete(shipment)
        db.commit()
        
        # 标记数据已变更
        mark_data_changed(f"delete_shipment: {batch_number}")


def import_shipments(db, shipments_data, operator_info):
    """批量导入发货记录"""
    from crud.operations import create_action_log, get_variant_by_sku
    from datetime import datetime
    
    success_count = 0
    failed_count = 0
    errors = []
    
    for shipment_data in shipments_data:
        try:
            batch_number = shipment_data.get('batch_number')
            if not batch_number:
                batch_number = datetime.now().strftime('SH%Y%m%d%H%M%S%f')[:18]
            
            existing = db.query(InventoryShipment).filter(
                InventoryShipment.batch_number == batch_number
            ).first()
            if existing:
                errors.append({'shipment': shipment_data, 'error': f'批次号已存在: {batch_number}'})
                failed_count += 1
                continue
            
            items = shipment_data.get('items', [])
            if not items:
                errors.append({'shipment': shipment_data, 'error': '发货项不能为空'})
                failed_count += 1
                continue
            
            # 验证所有SKU存在
            for item_data in items:
                sku = item_data.get('variant_sku') or item_data.get('sku')
                if not sku:
                    errors.append({'shipment': shipment_data, 'error': 'SKU不能为空'})
                    failed_count += 1
                    break
                variant = get_variant_by_sku(db, sku)
                if not variant:
                    errors.append({'shipment': shipment_data, 'error': f'SKU不存在: {sku}'})
                    failed_count += 1
                    break
            else:
                # 所有SKU都有效,创建发货记录
                estimated_arrival = shipment_data.get('estimated_arrival')
                if isinstance(estimated_arrival, str):
                    try:
                        estimated_arrival = datetime.fromisoformat(estimated_arrival).date()
                    except:
                        estimated_arrival = None
                
                shipment = InventoryShipment(
                    batch_number=batch_number,
                    status=ShipmentStatus.PENDING.value,  # 转换为字符串
                    estimated_arrival=estimated_arrival,
                    operator=str(operator_info),
                    notes=shipment_data.get('notes', '')
                )
                db.add(shipment)
                db.flush()
                
                for item_data in items:
                    sku = item_data.get('variant_sku') or item_data.get('sku')
                    variant = get_variant_by_sku(db, sku)
                    item = ShipmentItem(
                        shipment_id=shipment.id,
                        variant_id=variant.id,
                        quantity=item_data.get('quantity', 0),
                        tracking_number=item_data.get('tracking_number', '')
                    )
                    db.add(item)
                
                success_count += 1
                
        except Exception as e:
            errors.append({'shipment': shipment_data, 'error': str(e)})
            failed_count += 1
            db.rollback()
            continue
    
    try:
        # 先记录操作日志(在同一事务中)
        action_msg = f'批量导入发货: 成功{success_count}, 失败{failed_count}'
        create_action_log(db, operator_info, action_msg)
        
        # 标记数据已变更(批量导入也需要触发轻量级询问机制)
        if success_count > 0:
            mark_data_changed(f"import_shipments: {success_count} shipments")
        
        # 最后提交事务
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            'success': 0,
            'failed': len(shipments_data),
            'errors': [{'error': str(e)}]
        }
    
    return {'success': success_count, 'failed': failed_count, 'errors': errors}


def get_in_transit_inventory(
    db: Session,
    variant_sku: Optional[str] = None
) -> Dict[str, int]:
    """获取在途库存数量（只统计status='in_transit'运输中的发货单）
    
    Args:
        db: 数据库会话
        variant_sku: 可选，指定SKU。如果为None，返回所有SKU的在途库存
        
    Returns:
        字典，key为SKU，value为在途数量
        例如: {'BD31-Black': 100, 'BD55-Coffee': 50}
    """
    from crud.operations import get_variant_by_sku
    
    query = (
        db.query(
            ProductVariant.sku,
            func.sum(ShipmentItem.quantity).label('in_transit_qty')
        )
        .join(ShipmentItem, ShipmentItem.variant_id == ProductVariant.id)
        .join(
            InventoryShipment,
            InventoryShipment.id == ShipmentItem.shipment_id
        )
        .filter(InventoryShipment.status == 'in_transit')
    )
    
    # 如果指定了SKU，只查询该SKU
    if variant_sku:
        variant = get_variant_by_sku(db, variant_sku)
        if not variant:
            return {}
        query = query.filter(ProductVariant.id == variant.id)
    
    query = query.group_by(ProductVariant.sku)
    
    results = query.all()
    
    # 转换为字典
    in_transit_map = {}
    for sku, qty in results:
        in_transit_map[sku] = int(qty) if qty else 0
    
    return in_transit_map


def get_variant_in_transit_quantity(
    db: Session,
    variant_sku: str
) -> int:
    """获取指定SKU的在途库存数量
    
    Args:
        db: 数据库会话
        variant_sku: 产品变体SKU
        
    Returns:
        在途库存数量
    """
    result = get_in_transit_inventory(db, variant_sku)
    return result.get(variant_sku, 0)
