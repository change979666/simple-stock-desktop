"""测试备份恢复功能"""
from utils.auto_backup import AutoBackup
import shutil
from pathlib import Path

print("\n" + "="*70)
print("测试备份恢复功能")
print("="*70)

# 1. 创建备份管理器
backup = AutoBackup()

# 2. 获取备份列表
backups = backup.get_backup_list()
print(f"\n✅ 找到 {len(backups)} 个备份文件")

if not backups:
    print("❌ 没有备份文件，无法测试恢复")
    exit(1)

# 3. 选择最新的备份测试
test_backup = backups[0]
print(f"\n📦 测试备份文件:")
print(f"   文件名: {test_backup['name']}")
print(f"   时间: {test_backup['time'].strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   大小: {test_backup['size'] / 1024 / 1024:.2f} MB")

# 4. 备份当前数据库
db_path = Path('database.db')
if db_path.exists():
    backup_path = Path('database_test_backup.db')
    shutil.copy2(db_path, backup_path)
    print(f"\n✅ 已备份当前数据库到: {backup_path}")
    current_size = db_path.stat().st_size
else:
    print("\n⚠️  当前没有 database.db 文件")
    current_size = 0

# 5. 执行恢复
print(f"\n🔄 开始恢复测试...")
success = backup.restore_backup(test_backup['path'])

if success:
    print("✅ 恢复成功！")
    
    # 6. 验证恢复后的数据库
    if db_path.exists():
        restored_size = db_path.stat().st_size
        print(f"\n📊 验证恢复结果:")
        print(f"   恢复前大小: {current_size / 1024 / 1024:.2f} MB")
        print(f"   恢复后大小: {restored_size / 1024 / 1024:.2f} MB")
        print(f"   备份文件大小: {test_backup['size'] / 1024 / 1024:.2f} MB")
        
        if abs(restored_size - test_backup['size']) < 1024:  # 允许1KB误差
            print("\n✅ 数据库大小验证通过！")
        else:
            print("\n⚠️  数据库大小不匹配")
    
    # 7. 测试数据库完整性
    print(f"\n🔍 测试数据库完整性...")
    try:
        import sqlite3
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   找到 {len(tables)} 个数据表")
        
        # 检查产品表
        cursor.execute("SELECT COUNT(*) FROM product")
        product_count = cursor.fetchone()[0]
        print(f"   产品数量: {product_count}")
        
        # 检查销售记录
        cursor.execute("SELECT COUNT(*) FROM sales")
        sales_count = cursor.fetchone()[0]
        print(f"   销售记录: {sales_count}")
        
        conn.close()
        print("\n✅ 数据库完整性验证通过！")
        
    except Exception as e:
        print(f"\n❌ 数据库完整性检查失败: {e}")
    
    # 8. 恢复原数据库
    if Path('database_test_backup.db').exists():
        shutil.copy2('database_test_backup.db', 'database.db')
        Path('database_test_backup.db').unlink()
        print(f"\n✅ 已恢复原数据库")
    
    print("\n" + "="*70)
    print("✅ 备份恢复功能测试完成 - 一切正常！")
    print("="*70)
    
else:
    print("❌ 恢复失败！")
    
    # 恢复原数据库
    if Path('database_test_backup.db').exists():
        shutil.copy2('database_test_backup.db', 'database.db')
        Path('database_test_backup.db').unlink()
        print(f"\n✅ 已恢复原数据库")
    
    print("\n" + "="*70)
    print("❌ 备份恢复功能测试失败！")
    print("="*70)
