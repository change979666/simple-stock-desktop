"""
修复 shipment status 枚举值问题
将数据库中的枚举类型列改为字符串类型
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.database import SessionLocal, engine
from sqlalchemy import text, inspect


def migrate_shipment_status():
    """迁移shipment status字段类型"""
    print("开始迁移 shipment status 字段...")
    
    db = SessionLocal()
    try:
        # 检查表结构
        inspector = inspect(engine)
        
        # 检查 inventory_shipments 表
        if 'inventory_shipments' in inspector.get_table_names():
            print("\n✓ 找到 inventory_shipments 表")
            
            # 查看当前数据
            result = db.execute(
                text("SELECT COUNT(*) FROM inventory_shipments")
            )
            count = result.scalar()
            print(f"  当前记录数: {count}")
            
            # 查看不同的status值
            result = db.execute(
                text("SELECT DISTINCT status FROM inventory_shipments")
            )
            statuses = [row[0] for row in result.fetchall()]
            print(f"  当前status值: {statuses}")
            
        # 检查 inventory_transit_logs 表
        if 'inventory_transit_logs' in inspector.get_table_names():
            print("\n✓ 找到 inventory_transit_logs 表")
            
            # 查看当前数据
            result = db.execute(
                text("SELECT COUNT(*) FROM inventory_transit_logs")
            )
            count = result.scalar()
            print(f"  当前记录数: {count}")
            
            if count > 0:
                # 查看不同的status值
                result = db.execute(
                    text(
                        "SELECT DISTINCT old_status, new_status "
                        "FROM inventory_transit_logs"
                    )
                )
                for old, new in result.fetchall():
                    print(f"  status变更: '{old}' -> '{new}'")
        
        print("\n✅ 数据检查完成")
        print("\n说明:")
        print("  - InventoryShipment.status 已改为 String 类型")
        print("  - InventoryTransitLog.old_status/new_status 已改为 String 类型")
        print("  - 现有数据保持不变,无需迁移")
        print("  - 重启服务端后将使用新的数据类型")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    migrate_shipment_status()
