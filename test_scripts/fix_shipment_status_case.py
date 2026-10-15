"""
修复运输状态值的大小写格式
将数据库中的小写状态值转换为大写格式
"""
import sqlite3
import sys

def fix_status_case(db_path='database.db'):
    """修复状态值大小写"""
    
    # 状态映射表
    status_mapping = {
        'pending': 'PENDING',
        'in_transit': 'IN_TRANSIT',
        'arrived': 'ARRIVED',
        'shelved': 'SHELVED',
        'cancelled': 'CANCELLED'
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查当前状态值
        print(f"\n{'='*60}")
        print(f"正在修复数据库: {db_path}")
        print(f"{'='*60}\n")
        
        cursor.execute('SELECT DISTINCT status FROM inventory_shipments')
        current_statuses = [row[0] for row in cursor.fetchall()]
        print(f"修复前的状态值: {current_statuses}\n")
        
        # 统计需要修复的记录
        fix_count = 0
        for old_status, new_status in status_mapping.items():
            cursor.execute(
                'SELECT COUNT(*) FROM inventory_shipments WHERE status = ?',
                (old_status,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  {old_status:15} → {new_status:15} ({count} 条记录)")
                fix_count += count
        
        if fix_count == 0:
            print("✅ 所有状态值已是正确格式，无需修复")
            conn.close()
            return
        
        print(f"\n总计需要修复: {fix_count} 条记录")
        
        # 执行修复
        print("\n开始修复...")
        for old_status, new_status in status_mapping.items():
            cursor.execute(
                'UPDATE inventory_shipments SET status = ? WHERE status = ?',
                (new_status, old_status)
            )
        
        conn.commit()
        
        # 验证修复结果
        cursor.execute('SELECT DISTINCT status FROM inventory_shipments')
        new_statuses = [row[0] for row in cursor.fetchall()]
        print(f"\n修复后的状态值: {new_statuses}")
        
        print(f"\n{'='*60}")
        print("✅ 修复完成！")
        print(f"{'='*60}\n")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # 修复开发环境数据库
    print("修复开发环境数据库...")
    fix_status_case('database.db')
    
    # 如果打包环境数据库存在，也修复
    import os
    if os.path.exists('release/database.db'):
        print("\n修复打包环境数据库...")
        fix_status_case('release/database.db')
    
    if os.path.exists('dist_simple/database.db'):
        print("\n修复 dist_simple 数据库...")
        fix_status_case('dist_simple/database.db')
    
    print("\n所有数据库修复完成！🎉")
    print("\n建议:")
    print("1. 重启服务端")
    print("2. 重启客户端")
    print("3. 测试删除运输记录功能")
