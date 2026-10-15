from database.session import SessionLocal
from database.models import InventoryShipment
from database.inventory import ShipmentStatus

db = SessionLocal()

# 修改第一个批次为运输中状态
shipment = db.query(InventoryShipment).filter(
    InventoryShipment.batch_number == 'SHIP2025106839'
).first()

if shipment:
    print(f'批次: {shipment.batch_number}')
    print(f'修改前状态: {shipment.status}')
    shipment.status = ShipmentStatus.IN_TRANSIT
    db.commit()
    print(f'修改后状态: {shipment.status}')
    print('✅ 已修改为运输中状态,请刷新发货管理页面查看按钮!')
else:
    print('❌ 批次不存在')

db.close()
