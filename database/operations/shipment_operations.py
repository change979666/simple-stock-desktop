from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import (
    InventoryShipment, ShipmentItem,
    ShipmentStatus, InventoryTransitLog
)


def add_shipment(
    db: Session,
    shipment_data: Dict,
    items_data: List[Dict]
) -> InventoryShipment:
    """添加新的出库单及其项目"""
    # 生成批次号
    batch_number = f"SHIP{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 创建出库单
    shipment = InventoryShipment(
        batch_number=batch_number,
        status=ShipmentStatus.PENDING,
        operator=shipment_data['operator'],
        notes=shipment_data.get('notes'),
        estimated_arrival=shipment_data.get('estimated_arrival')
    )
    
    # 添加出库项目
    for item_data in items_data:
        shipment_item = ShipmentItem(
            variant_id=item_data['variant_id'],
            quantity=item_data['quantity'],
            tracking_number=item_data.get('tracking_number')
        )
        shipment.shipment_items.append(shipment_item)
    
    # 保存到数据库
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    
    return shipment


def get_all_shipments(db: Session) -> List[InventoryShipment]:
    """获取所有出库单，包括其项目信息"""
    return (
        db.query(InventoryShipment)
        .options(
            joinedload(InventoryShipment.shipment_items)
            .joinedload(ShipmentItem.variant)
        )
        .order_by(InventoryShipment.created_at.desc())
        .all()
    )


def get_shipment(
    db: Session,
    shipment_id: int
) -> Optional[InventoryShipment]:
    """根据ID获取特定的出库单"""
    return (
        db.query(InventoryShipment)
        .options(
            joinedload(InventoryShipment.shipment_items)
            .joinedload(ShipmentItem.variant)
        )
        .filter(InventoryShipment.id == shipment_id)
        .first()
    )


def update_shipment_status(
    db: Session,
    shipment_id: int,
    status: ShipmentStatus,
    operator: str
) -> Optional[InventoryShipment]:
    """更新出库单状态"""
    shipment = get_shipment(db, shipment_id)
    if shipment:
        # 记录旧状态
        old_status = shipment.status
        
        # 更新状态
        shipment.status = status
        
        # 如果状态改为已到货，记录到货日期
        if status == ShipmentStatus.ARRIVED:
            shipment.arrival_date = datetime.now()
            
        # 添加状态变更记录
        for item in shipment.shipment_items:
            transit_log = InventoryTransitLog(
                shipment_id=shipment_id,
                variant_id=item.variant_id,
                old_status=old_status,
                new_status=status,
                operator=operator
            )
            db.add(transit_log)
            
        db.commit()
        db.refresh(shipment)
    return shipment