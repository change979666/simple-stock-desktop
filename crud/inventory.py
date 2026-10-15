from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from database.models import (
    InventoryShipment, InventoryTransitLog,  
    ProductVariant, StockLog
)
from database.inventory import ShipmentStatus, InventoryStatus
from typing import Optional, List

# 导入数据变更跟踪器
from utils.data_change_tracker import mark_data_changed


def create_shipment(
    db: Session,
    variant_id: int,
    quantity: int,
    tracking_number: Optional[str] = None,
    estimated_arrival: Optional[datetime] = None,
    operator: str = None,
    notes: str = None
) -> InventoryShipment:
    """创建发货记录"""
    shipment = InventoryShipment(
        variant_id=variant_id,
        tracking_number=tracking_number,
        quantity=quantity,
        status=ShipmentStatus.PENDING.value,  # 转换为字符串
        estimated_arrival=estimated_arrival,
        operator=operator,
        notes=notes
    )
    db.add(shipment)
    db.flush()
    
    # 记录初始状态
    log = InventoryTransitLog(
        shipment_id=shipment.id,
        variant_id=variant_id,
        new_status=ShipmentStatus.PENDING.value,  # 转换为字符串
        operator=operator,
        notes='创建发货记录'
    )
    db.add(log)
    db.commit()
    
    # 标记数据已变更
    mark_data_changed(f"create_inventory_shipment: {shipment.id}")
    
    return shipment


def update_shipment_status(
    db: Session,
    shipment_id: int,
    new_status: ShipmentStatus,
    operator: str = None,
    notes: str = None
) -> None:
    """更新发货状态"""
    shipment = db.query(InventoryShipment).get(shipment_id)
    if not shipment:
        raise ValueError('发货记录不存在')
    
    old_status = shipment.status  # 字符串
    shipment.status = new_status.value  # 转换为字符串
    
    # 记录状态变更
    log = InventoryTransitLog(
        shipment_id=shipment_id,
        variant_id=shipment.variant_id,
        old_status=old_status,
        new_status=new_status.value,  # 转换为字符串
        operator=operator,
        notes=notes or f'状态更新: {old_status} -> {new_status.value}'
    )
    db.add(log)
    
    # 如果状态变为已上架，自动增加库存
    if new_status == ShipmentStatus.SHELVED:
        from .operations import create_stock_log
        create_stock_log(
            db,
            variant_id=shipment.variant_id,
            change_quantity=shipment.quantity,
            notes=f'发货单 {shipment_id} 上架入库',
            operator_info=operator
        )
    
    db.commit()
    
    # 标记数据已变更
    mark_data_changed(f"update_inventory_shipment_status: {shipment_id}")


def get_transit_inventory(db: Session, variant_id: Optional[int] = None):
    """获取在途库存数量"""
    query = db.query(InventoryShipment).filter(
        InventoryShipment.status != ShipmentStatus.SHELVED.value
    )
    
    if variant_id is not None:
        query = query.filter(InventoryShipment.variant_id == variant_id)
    
    return query.all()


def get_shipment_history(
    db: Session,
    variant_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """获取发货历史记录"""
    query = db.query(InventoryShipment)
    
    if variant_id is not None:
        query = query.filter(InventoryShipment.variant_id == variant_id)
    
    if start_date:
        query = query.filter(InventoryShipment.created_at >= start_date)
    
    if end_date:
        query = query.filter(InventoryShipment.created_at <= end_date)
    
    return query.order_by(InventoryShipment.created_at.desc()).all()


def get_variant_by_sku(db: Session, sku: str) -> Optional[ProductVariant]:
    """通过SKU获取产品变体(大小写不敏感)"""
    from sqlalchemy import func
    return db.query(ProductVariant).filter(
        func.lower(ProductVariant.sku) == sku.lower()
    ).first()


def get_inventory_status(
    db: Session,
    variant_id: int
) -> Optional[InventoryStatus]:
    """获取产品的库存状态"""
    # 获取当前库存数量
    current_stock = db.query(InventoryLog)\
        .filter(InventoryLog.variant_id == variant_id)\
        .with_entities(func.sum(InventoryLog.change_quantity))\
        .scalar() or 0
    
    # 获取产品设置
    variant = db.query(ProductVariant).get(variant_id)
    if not variant:
        return None
        
    # 判断库存状态
    if current_stock <= 0:
        return InventoryStatus.OUT_OF_STOCK
    elif current_stock < variant.warning_threshold:
        return InventoryStatus.LOW_STOCK
    elif current_stock > variant.max_stock:
        return InventoryStatus.OVERSTOCK
    else:
        return InventoryStatus.NORMAL


def add_inventory(
    db: Session,
    variant_id: int,
    quantity: int,
    operator_info: str,
    notes: Optional[str] = None
) -> StockLog:
    """添加库存 - 同时更新 current_stock 和 StockLog"""
    if quantity <= 0:
        raise ValueError("入库数量必须为正数")
    
    # 获取产品变体
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    if not variant:
        raise ValueError(f"产品变体 ID {variant_id} 不存在")
    
    # 1. 更新 current_stock（直接存储的库存数量）
    variant.current_stock += quantity
    
    # 2. 创建 StockLog（历史记录）
    log = StockLog(
        variant_id=variant_id,
        change_quantity=quantity,
        operator_info=operator_info,
        notes=notes
    )
    db.add(log)
    
    # 一次性提交两个更新
    db.commit()
    db.refresh(log)
    db.refresh(variant)
    
    return log


def reduce_inventory(
    db: Session,
    variant_id: int,
    quantity: int,
    operator_info: str,
    notes: Optional[str] = None
) -> StockLog:
    """减少库存 - 同时更新 current_stock 和 StockLog"""
    if quantity <= 0:
        raise ValueError("出库数量必须为正数")
    
    # 获取产品变体
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).first()
    if not variant:
        raise ValueError(f"产品变体 ID {variant_id} 不存在")
    
    # 检查库存是否充足（使用 current_stock 字段，更快）
    if variant.current_stock < quantity:
        raise ValueError(
            f"库存不足：当前库存 {variant.current_stock}，"
            f"需要出库 {quantity}"
        )
    
    # 1. 更新 current_stock（直接存储的库存数量）
    variant.current_stock -= quantity
    
    # 2. 创建 StockLog（历史记录）
    log = StockLog(
        variant_id=variant_id,
        change_quantity=-quantity,
        operator_info=operator_info,
        notes=notes
    )
    db.add(log)
    
    # 一次性提交两个更新
    db.commit()
    db.refresh(log)
    db.refresh(variant)
    
    # 标记数据已变更
    mark_data_changed(f"reduce_inventory: {variant.sku} -{quantity}")
    
    return log
