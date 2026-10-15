from sqlalchemy.orm import Session
from .settings import SystemSettings
from typing import Optional


def get_setting(db: Session, key: str, default: Optional[str] = None) -> str:
    """获取系统设置值"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str) -> None:
    """设置或更新系统设置值"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = SystemSettings(key=key, value=value)
        db.add(setting)
    db.commit()