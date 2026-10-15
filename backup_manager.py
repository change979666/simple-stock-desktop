"""
数据库备份管理工具 - 统一管理界面
支持备份、恢复、删除操作
"""
from utils.auto_backup import AutoBackup
from pathlib import Path


def show_menu():
    """显示主菜单"""
    print("\n" + "="*70)
    print("               数据库备份管理工具")
    print("="*70)
    print("\n请选择操作：")
    print("  1. 📦 立即备份数据库")
    print("  2. 🔄 恢复数据库备份")
    print("  3. 📋 查看所有备份")
    print("  4. 🗑️  删除备份文件")
    print("  0. 🚪 退出程序")
    print("\n" + "="*70)


def do_backup():
    """执行备份操作"""
    print("\n" + "="*70)
    print("📦 开始备份数据库")
    print("="*70)
    
    backup = AutoBackup()
    
    print("\n🔄 正在备份数据库...")
    if backup.create_backup():
        print("\n✅ 备份成功！")
        
        # 显示最新的备份
        backups = backup.get_backup_list()
        if backups:
            latest = backups[0]
            print(f"\n📁 备份文件信息:")
            print(f"   文件名: {latest['name']}")
            print(f"   时间: {latest['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   大小: {latest['size'] / 1024 / 1024:.2f} MB")
            print(f"\n💾 备份位置: backups\\{latest['name']}")
    else:
        print("\n❌ 备份失败！")
        print("\n请检查：")
        print("  1. database.db 文件是否存在")
        print("  2. backups 目录是否可写")
        print("  3. 磁盘空间是否充足")


def list_backups():
    """列出所有备份"""
    backup = AutoBackup()
    backups = backup.get_backup_list()
    
    if not backups:
        print("\n❌ 没有找到任何备份文件！")
        return []
    
    print("\n" + "="*70)
    print("📦 可用的数据库备份文件")
    print("="*70)
    
    for i, info in enumerate(backups, 1):
        time_str = info['time'].strftime('%Y-%m-%d %H:%M:%S')
        size_mb = info['size'] / 1024 / 1024
        print(f"\n{i}. {info['name']}")
        print(f"   时间: {time_str}")
        print(f"   大小: {size_mb:.2f} MB")
    
    print("\n" + "="*70)
    return backups


def do_restore():
    """执行恢复操作"""
    print("\n" + "="*70)
    print("🔄 恢复数据库备份")
    print("="*70)
    
    # 先列出所有备份，让用户看到有哪些可选
    backups = list_backups()
    if not backups:
        return
    
    print("\n⚠️  警告：")
    print("  - 恢复操作将覆盖当前数据库")
    print("  - 请确保服务端已停止")
    print("  - 系统会自动备份当前数据库")
    
    confirm = input("\n是否继续恢复？(yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\n✅ 已取消恢复操作")
        return
    
    # 选择要恢复的备份
    while True:
        try:
            choice = input(f"\n请输入要恢复的备份编号 (1-{len(backups)})，或输入 0 取消: ").strip()
            
            if choice == '0':
                print("\n已取消恢复操作")
                return
            
            index = int(choice) - 1
            if 0 <= index < len(backups):
                break
            else:
                print(f"❌ 请输入 1 到 {len(backups)} 之间的数字！")
        except ValueError:
            print("❌ 请输入有效的数字！")
    
    selected_backup = backups[index]
    
    # 确认恢复
    print(f"\n📋 您选择恢复的备份:")
    print(f"   文件名: {selected_backup['name']}")
    print(f"   时间: {selected_backup['time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   大小: {selected_backup['size'] / 1024 / 1024:.2f} MB")
    
    final_confirm = input("\n⚠️  最后确认：确定要恢复此备份吗？(yes/no): ").strip().lower()
    
    if final_confirm not in ['yes', 'y']:
        print("\n已取消恢复操作")
        return
    
    # 执行恢复
    print("\n🔄 正在恢复备份...")
    backup_manager = AutoBackup()
    
    if backup_manager.restore_backup(selected_backup['path']):
        print("\n✅ 恢复成功！")
        print("\n💡 提示：")
        print("  - 请重启服务端以使用恢复的数据库")
        print("  - 启动前请确认数据是否正确")
    else:
        print("\n❌ 恢复失败！")
        print("请查看错误信息或联系技术支持")


def do_view():
    """查看所有备份"""
    backups = list_backups()
    
    if backups:
        total_size = sum(b['size'] for b in backups) / 1024 / 1024
        print(f"\n📊 统计信息:")
        print(f"   备份文件总数: {len(backups)} 个")
        print(f"   占用空间: {total_size:.2f} MB")
        print(f"   最新备份: {backups[0]['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   最旧备份: {backups[-1]['time'].strftime('%Y-%m-%d %H:%M:%S')}")


def do_delete():
    """删除备份文件"""
    print("\n" + "="*70)
    print("🗑️  删除备份文件")
    print("="*70)
    
    # 列出所有备份
    backups = list_backups()
    if not backups:
        return
    
    print("\n⚠️  注意：删除操作不可恢复！")
    
    # 选择删除方式
    print("\n请选择删除方式：")
    print("  1. 删除单个备份")
    print("  2. 批量删除旧备份（保留最新N个）")
    print("  0. 取消删除")
    
    delete_mode = input("\n请选择 (0-2): ").strip()
    
    if delete_mode == '0':
        print("\n已取消删除操作")
        return
    
    elif delete_mode == '1':
        # 删除单个备份
        while True:
            try:
                choice = input(f"\n请输入要删除的备份编号 (1-{len(backups)})，或输入 0 取消: ").strip()
                
                if choice == '0':
                    print("\n已取消删除操作")
                    return
                
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    break
                else:
                    print(f"❌ 请输入 1 到 {len(backups)} 之间的数字！")
            except ValueError:
                print("❌ 请输入有效的数字！")
        
        selected_backup = backups[index]
        
        # 确认删除
        print(f"\n📋 您选择删除的备份:")
        print(f"   文件名: {selected_backup['name']}")
        print(f"   时间: {selected_backup['time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        confirm = input("\n⚠️  确定要删除此备份吗？(yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y']:
            try:
                Path(selected_backup['path']).unlink()
                print(f"\n✅ 已删除备份: {selected_backup['name']}")
            except Exception as e:
                print(f"\n❌ 删除失败: {e}")
        else:
            print("\n已取消删除操作")
    
    elif delete_mode == '2':
        # 批量删除
        try:
            keep_count = int(input("\n请输入要保留的最新备份数量 (建议至少保留7个): ").strip())
            
            if keep_count <= 0:
                print("❌ 保留数量必须大于0")
                return
            
            if keep_count >= len(backups):
                print(f"\n💡 当前只有 {len(backups)} 个备份，无需删除")
                return
            
            to_delete = backups[keep_count:]
            
            print(f"\n📋 将删除 {len(to_delete)} 个旧备份:")
            for i, backup in enumerate(to_delete[:5], 1):  # 只显示前5个
                print(f"   {i}. {backup['name']} ({backup['time'].strftime('%Y-%m-%d')})")
            if len(to_delete) > 5:
                print(f"   ... 还有 {len(to_delete) - 5} 个")
            
            confirm = input(f"\n⚠️  确定要删除这 {len(to_delete)} 个备份吗？(yes/no): ").strip().lower()
            
            if confirm in ['yes', 'y']:
                deleted_count = 0
                for backup in to_delete:
                    try:
                        Path(backup['path']).unlink()
                        deleted_count += 1
                    except Exception as e:
                        print(f"❌ 删除 {backup['name']} 失败: {e}")
                
                print(f"\n✅ 成功删除 {deleted_count} 个备份文件")
                print(f"💾 保留了最新的 {keep_count} 个备份")
            else:
                print("\n已取消删除操作")
                
        except ValueError:
            print("❌ 请输入有效的数字！")
    
    else:
        print("❌ 无效的选择！")


def main():
    """主程序"""
    print("\n" + "="*70)
    print("               欢迎使用数据库备份管理工具")
    print("="*70)
    print("\n💡 功能说明:")
    print("  - 备份：立即创建数据库备份")
    print("  - 恢复：从备份文件恢复数据库")
    print("  - 查看：查看所有备份文件信息")
    print("  - 删除：清理不需要的备份文件")
    
    while True:
        show_menu()
        
        choice = input("\n请输入选项 (0-4): ").strip()
        
        if choice == '1':
            do_backup()
        elif choice == '2':
            do_restore()
        elif choice == '3':
            do_view()
        elif choice == '4':
            do_delete()
        elif choice == '0':
            print("\n" + "="*70)
            print("感谢使用！再见！")
            print("="*70)
            break
        else:
            print("\n❌ 无效的选择，请输入 0-4 之间的数字")
        
        # 等待用户按键继续
        if choice in ['1', '2', '3', '4']:
            input("\n按回车键继续...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序已中断，再见！")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        input("\n按回车键退出...")
