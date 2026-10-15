import enum


class InventoryStatus(enum.Enum):
    NORMAL = 'normal'  # 正常
    DISCONTINUED = 'discontinued'  # 停产下架
    LOW_STOCK = 'low_stock'  # 库存不足
    OUT_OF_STOCK = 'out_of_stock'  # 无库存
    ON_HOLD = 'on_hold'  # 暂停销售
    REORDERING = 'reordering'  # 补货中
    OVERSTOCK = 'overstock'  # 库存过多

    @classmethod
    def get_display_info(cls, status):
        """获取状态的显示信息"""
        info_map = {
            cls.NORMAL: ('正常', '#198754', '✅'),
            cls.DISCONTINUED: ('停产下架', '#6c757d', '⛔'),
            cls.LOW_STOCK: ('库存不足', '#ffc107', '⚠️'),
            cls.OUT_OF_STOCK: ('无库存', '#dc3545', '❌'),
            cls.ON_HOLD: ('暂停销售', '#0dcaf0', '⏸️'),
            cls.REORDERING: ('补货中', '#0d6efd', '🔄'),
            cls.OVERSTOCK: ('库存过多', '#fd7e14', '📦')
        }
        return info_map.get(status, ('未知', '#6c757d', '❓'))
    
    def __str__(self):
        """字符串表示，用于数据库存储"""
        return self.value


class ShipmentStatus(enum.Enum):
    PENDING = 'pending'  # 待发货
    IN_TRANSIT = 'in_transit'  # 运输中
    ARRIVED = 'arrived'  # 已到达
    SHELVED = 'shelved'  # 已上架
    CANCELLED = 'cancelled'  # 已取消

    @classmethod
    def get_display_info(cls, status):
        """获取状态的显示信息"""
        info_map = {
            cls.PENDING: ('待发货', '#ffc107', '📦'),
            cls.IN_TRANSIT: ('运输中', '#0d6efd', '🚚'),
            cls.ARRIVED: ('已到达', '#198754', '📍'),
            cls.SHELVED: ('已上架', '#6c757d', '✅'),
            cls.CANCELLED: ('已取消', '#dc3545', '❌')
        }
        return info_map.get(status, ('未知', '#6c757d', '❓'))
    
    def __str__(self):
        """字符串表示，用于数据库存储"""
        return self.value

    @classmethod
    def coerce(cls, item):
        """将字符串转换为枚举值，用于 SQLAlchemy 类型转换"""
        if isinstance(item, cls):
            return item
        if isinstance(item, str):
            # 尝试按值查找(小写)
            try:
                return cls(item.lower())
            except ValueError:
                # 尝试按名称查找(大写)
                try:
                    return cls[item.upper()]
                except KeyError:
                    pass
        return cls(str(item))


