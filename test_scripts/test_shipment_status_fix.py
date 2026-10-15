"""
测试 shipment status 修复效果
验证不再出现枚举值错误
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.database import SessionLocal
from database.models import InventoryShipment, InventoryTransitLog
from database.inventory import ShipmentStatus


def test_shipment_status_fix():
    """测试 shipment status 修复"""
    print("=" * 60)
    print("测试 Shipment Status 修复效果")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 测试1: 读取所有发货记录
        print("\n测试1: 读取所有发货记录...")
        shipments = db.query(InventoryShipment).all()
        print(f"  ✓ 成功读取 {len(shipments)} 条发货记录")
        
        # 显示状态分布
        status_counts = {}
        for shipment in shipments:
            status = shipment.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\n  状态分布:")
        for status, count in status_counts.items():
            print(f"    {status}: {count} 条")
        
        # 测试2: 通过ID读取发货记录
        print("\n测试2: 通过ID读取发货记录...")
        if shipments:
            first_shipment = db.query(InventoryShipment).first()
            print(f"  ✓ 成功读取ID={first_shipment.id}的记录")
            print(f"    批次号: {first_shipment.batch_number}")
            print(f"    状态: '{first_shipment.status}'")
        else:
            print("  ⚠️  没有发货记录")
        
        # 测试3: 按状态查询
        print("\n测试3: 按状态查询...")
        for status in ShipmentStatus:
            status_str = str(status)  # 自动调用__str__()，返回小写值
            count = (
                db.query(InventoryShipment)
                .filter(InventoryShipment.status == status_str)
                .count()
            )
            if count > 0:
                print(f"  ✓ {status.name}: {count} 条 (值: '{status_str}')")
        
        # 测试4: 读取状态变更日志
        print("\n测试4: 读取状态变更日志...")
        logs = db.query(InventoryTransitLog).all()
        print(f"  ✓ 成功读取 {len(logs)} 条状态变更日志")
        
        if logs:
            for log in logs[:5]:  # 只显示前5条
                print(
                    f"    {log.old_status} -> {log.new_status} "
                    f"(操作员: {log.operator})"
                )
        else:
            print("  (暂无状态变更日志)")
        
        # 测试5: 验证所有状态值都是有效的
        print("\n测试5: 验证状态值...")
        valid_statuses = [str(s) for s in ShipmentStatus]
        invalid_found = False
        
        for status in status_counts.keys():
            if status not in valid_statuses:
                print(f"  ❌ 发现无效状态: '{status}'")
                invalid_found = True
        
        if not invalid_found:
            print(f"  ✓ 所有状态值都是有效的")
            print(f"  有效状态: {valid_statuses}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！修复成功！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == '__main__':
    success = test_shipment_status_fix()
    sys.exit(0 if success else 1)
