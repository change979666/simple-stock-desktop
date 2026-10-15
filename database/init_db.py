"""数据库初始化脚本"""

from pathlib import Path
from .session import Base  # 使用session.py的Base,这才是models继承的Base
from .database import engine
# 导入所有models以便Base.metadata知道要创建哪些表
from .models import (
    Product, ProductVariant, Category,
    SaleOrder, OrderItem, SaleRecord,
    InventoryShipment, ShipmentItem, InventoryTransitLog,
    ActionLog, StockLog
)


def init_db():
    """初始化数据库"""
    # 删除旧数据库
    db_path = Path(engine.url.database)
    if db_path.exists():
        db_path.unlink()

    # 创建新表
    Base.metadata.create_all(engine)
    print(f"✓ 数据库表已创建: {len(Base.metadata.tables)} 个表")



if __name__ == '__main__':
    init_db()