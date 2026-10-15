"""清空业务数据（库存、发货、销售），保留产品"""
from database.session import SessionLocal
from database.models import StockLog, SaleRecord
from database.models.shipment import ShipmentItem, InventoryShipment

db = SessionLocal()

try:
    print("=" * 60)
    print("开始清空业务数据...")
    print("=" * 60)
    
    # 1. 清空销售记录
    deleted_sales = db.query(SaleRecord).delete()
    print(f'\n✅ 已删除 {deleted_sales} 条销售记录')
    
    # 2. 清空发货明细
    deleted_shipment_items = db.query(ShipmentItem).delete()
    print(f'✅ 已删除 {deleted_shipment_items} 条发货明细')
    
    # 3. 清空发货单
    deleted_shipments = db.query(InventoryShipment).delete()
    print(f'✅ 已删除 {deleted_shipments} 个发货单')
    
    # 4. 清空库存日志
    deleted_stock_logs = db.query(StockLog).delete()
    print(f'✅ 已删除 {deleted_stock_logs} 条库存日志')
    
    db.commit()
    
    print("\n" + "=" * 60)
    print("✅ 业务数据清空完成！")
    print("=" * 60)
    print("\n保留的数据：")
    print("  - 产品信息（Product）")
    print("  - 产品变体/SKU（ProductVariant）")
    print("\n已清空的数据：")
    print("  - 库存日志（StockLog）")
    print("  - 销售记录（SaleRecord）")
    print("  - 发货单（Shipment）")
    print("  - 发货明细（ShipmentItem）")
    print("\n现在可以使用导入模板测试了！")
    print("=" * 60)
    
except Exception as e:
    db.rollback()
    print(f'\n❌ 错误: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
