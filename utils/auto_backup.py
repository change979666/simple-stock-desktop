"""
服务端自动备份工具
定期备份数据库，保留最近N个备份文件
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutoBackup:
    """自动备份管理器"""
    
    def __init__(self, db_path: str = 'database.db', backup_dir: str = 'backups', max_backups: int = 30):
        """
        初始化自动备份
        
        Args:
            db_path: 数据库文件路径
            backup_dir: 备份目录
            max_backups: 保留的最大备份数量（默认30个，大约一个月）
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups
        
        # 确保备份目录存在
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"自动备份已初始化: db={db_path}, backup_dir={backup_dir}, max_backups={max_backups}")
    
    def create_backup(self) -> bool:
        """
        创建数据库备份
        
        Returns:
            bool: 备份是否成功
        """
        try:
            # 检查数据库文件是否存在
            if not self.db_path.exists():
                logger.error(f"数据库文件不存在: {self.db_path}")
                return False
            
            # 生成备份文件名: database_backup_20251016_143025.db
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"database_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_path)
            
            file_size = backup_path.stat().st_size / 1024 / 1024  # MB
            logger.info(f"✅ 备份成功: {backup_filename} ({file_size:.2f} MB)")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """清理旧备份，只保留最近的N个"""
        try:
            # 获取所有备份文件
            backup_files = sorted(
                self.backup_dir.glob('database_backup_*.db'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            # 删除超出数量的旧备份
            if len(backup_files) > self.max_backups:
                for old_backup in backup_files[self.max_backups:]:
                    old_backup.unlink()
                    logger.info(f"🗑️  删除旧备份: {old_backup.name}")
                    
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
    
    def get_backup_list(self) -> list:
        """
        获取所有备份文件列表
        
        Returns:
            list: 备份文件信息列表 [{name, path, size, time}, ...]
        """
        try:
            backup_files = []
            
            for backup_file in sorted(
                self.backup_dir.glob('database_backup_*.db'),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            ):
                stat = backup_file.stat()
                backup_files.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size': stat.st_size,
                    'time': datetime.fromtimestamp(stat.st_mtime)
                })
            
            return backup_files
            
        except Exception as e:
            logger.error(f"获取备份列表失败: {e}")
            return []
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            backup_file = Path(backup_path)
            
            if not backup_file.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 先备份当前数据库（以防恢复失败）
            emergency_backup = self.db_path.parent / f"database_emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            if self.db_path.exists():
                shutil.copy2(self.db_path, emergency_backup)
                logger.info(f"已创建紧急备份: {emergency_backup.name}")
            
            # 恢复备份
            shutil.copy2(backup_file, self.db_path)
            logger.info(f"✅ 恢复成功: {backup_file.name}")
            
            # 删除紧急备份
            if emergency_backup.exists():
                emergency_backup.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 恢复失败: {e}")
            
            # 尝试恢复紧急备份
            if 'emergency_backup' in locals() and emergency_backup.exists():
                try:
                    shutil.copy2(emergency_backup, self.db_path)
                    logger.info("已从紧急备份恢复")
                except:
                    pass
            
            return False


# 便捷函数
def auto_backup(db_path: str = 'database.db', backup_dir: str = 'backups', max_backups: int = 30) -> bool:
    """
    执行一次自动备份（供定时任务调用）
    
    Args:
        db_path: 数据库文件路径
        backup_dir: 备份目录
        max_backups: 保留的最大备份数量
        
    Returns:
        bool: 备份是否成功
    """
    backup = AutoBackup(db_path, backup_dir, max_backups)
    return backup.create_backup()


if __name__ == '__main__':
    # 测试备份
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    backup = AutoBackup()
    
    # 创建备份
    if backup.create_backup():
        print("\n✅ 备份成功！")
        
        # 查看备份列表
        print("\n📦 备份列表:")
        for i, info in enumerate(backup.get_backup_list(), 1):
            print(f"{i}. {info['name']}")
            print(f"   大小: {info['size'] / 1024 / 1024:.2f} MB")
            print(f"   时间: {info['time'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n❌ 备份失败！")
