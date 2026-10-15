"""
清空旧的操作日志数据
让所有新产生的日志都显示正确的操作员信息
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.session import SessionLocal
from database.models import ActionLog, StockLog


def clear_old_logs():
    """清空旧的操作日志"""
    
    session = SessionLocal()
    
    try:
        # 统计当前日志数量
        action_log_count = session.query(ActionLog).count()
        stock_log_count = session.query(StockLog).count()
        
        print("=" * 60)
        print("清空操作日志工具")
        print("=" * 60)
        print()
        print("📊 当前数据库统计:")
        print(f"   - 操作日志(ActionLog): {action_log_count} 条")
        print(f"   - 库存日志(StockLog): {stock_log_count} 条")
        print()
        
        if action_log_count == 0 and stock_log_count == 0:
            print("⚠️  数据库中没有日志记录，无需清空")
            return
        
        # 确认操作
        print("⚠️  警告：即将执行以下操作:")
        print("   1. 清空所有操作日志(ActionLog)")
        print("   2. 清空所有库存日志(StockLog)")
        print()
        print("   注意：此操作不可恢复！")
        print("   建议：在执行前先备份数据库文件 database.db")
        print()
        
        confirm = input("确认继续执行? (输入 yes 继续): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ 操作已取消")
            return
        
        print()
        print("🔄 开始清空日志...")
        
        # 清空操作日志
        deleted_action_logs = session.query(ActionLog).delete()
        print(f"   ✅ 已删除 {deleted_action_logs} 条操作日志")
        
        # 清空库存日志
        deleted_stock_logs = session.query(StockLog).delete()
        print(f"   ✅ 已删除 {deleted_stock_logs} 条库存日志")
        
        # 提交事务
        session.commit()
        
        print()
        print("✅ 日志清空成功!")
        print()
        print("💡 提示:")
        print("   - 所有旧的操作记录已清除")
        print("   - 从现在开始，所有新操作都会记录正确的操作员信息")
        print("   - 库存数量不受影响（基于库存日志的累计值会变为0）")
        print()
        print("⚠️  重要：")
        print("   - 如果需要保留库存数量，请不要清空库存日志(StockLog)")
        print("   - 建议只清空操作日志(ActionLog)")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()


def clear_action_logs_only():
    """只清空操作日志，保留库存日志"""
    
    session = SessionLocal()
    
    try:
        # 统计当前日志数量
        action_log_count = session.query(ActionLog).count()
        
        print("=" * 60)
        print("清空操作日志工具（仅清空操作日志，保留库存记录）")
        print("=" * 60)
        print()
        print("📊 当前数据库统计:")
        print(f"   - 操作日志(ActionLog): {action_log_count} 条")
        print()
        
        if action_log_count == 0:
            print("⚠️  数据库中没有操作日志记录，无需清空")
            return
        
        # 确认操作
        print("⚠️  即将执行以下操作:")
        print("   1. 清空所有操作日志(ActionLog)")
        print("   2. 保留库存日志(StockLog) - 库存数量不受影响")
        print()
        
        confirm = input("确认继续执行? (输入 yes 继续): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ 操作已取消")
            return
        
        print()
        print("🔄 开始清空操作日志...")
        
        # 清空操作日志
        deleted_action_logs = session.query(ActionLog).delete()
        print(f"   ✅ 已删除 {deleted_action_logs} 条操作日志")
        
        # 提交事务
        session.commit()
        
        print()
        print("✅ 操作日志清空成功!")
        print()
        print("💡 提示:")
        print("   - 所有旧的操作记录已清除")
        print("   - 库存日志已保留，库存数量不受影响")
        print("   - 从现在开始，所有新操作都会记录正确的操作员信息")
        
    except Exception as e:
        session.rollback()
        print(f"❌ 操作失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()


def verify_clearing():
    """验证日志是否已清空"""
    
    session = SessionLocal()
    
    try:
        action_log_count = session.query(ActionLog).count()
        stock_log_count = session.query(StockLog).count()
        
        print()
        print("🔍 验证结果:")
        print(f"   - 操作日志(ActionLog): {action_log_count} 条")
        print(f"   - 库存日志(StockLog): {stock_log_count} 条")
        
        if action_log_count == 0:
            print("   ✅ 操作日志已成功清空!")
        else:
            print(f"   ⚠️  仍有 {action_log_count} 条操作日志")
        
    except Exception as e:
        print(f"❌ 验证失败: {str(e)}")
    
    finally:
        session.close()


if __name__ == '__main__':
    print()
    print("请选择操作:")
    print("1. 只清空操作日志 (推荐 - 保留库存数量)")
    print("2. 清空所有日志 (操作日志 + 库存日志，会导致库存归零)")
    print()
    
    choice = input("请输入选项 (1 或 2): ").strip()
    
    if choice == '1':
        clear_action_logs_only()
        verify_clearing()
    elif choice == '2':
        clear_old_logs()
        verify_clearing()
    else:
        print("❌ 无效的选项")
    
    print()
    print("=" * 60)
    print("操作完成")
    print("=" * 60)
