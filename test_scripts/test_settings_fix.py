"""测试配置保存修复"""
import sys
sys.path.insert(0, '.')

from config.settings import load_settings, save_settings, update_setting

print("=" * 60)
print("测试配置保存修复")
print("=" * 60)

print("\n[1] 加载配置:")
s = load_settings()
print(f"  配置节数: {len(s)}")
print(f"  配置节: {list(s.keys())}")
print(f"  ✓ server: {'server' in s}")
print(f"  ✓ database: {'database' in s}")
print(f"  ✓ user_info: {'user_info' in s}")
print(f"  当前昵称: {s['user_info']['nickname']}")

print("\n[2] 修改昵称:")
update_setting('user_info', 'nickname', '测试昵称')
print("  ✓ 昵称已修改")

print("\n[3] 重新加载配置:")
s2 = load_settings()
print(f"  配置节数: {len(s2)}")
print(f"  配置节: {list(s2.keys())}")
print(f"  ✓ server: {'server' in s2}")
print(f"  ✓ database: {'database' in s2}")
print(f"  ✓ user_info: {'user_info' in s2}")
print(f"  新昵称: {s2['user_info']['nickname']}")

print("\n[4] 检查结果:")
if 'server' in s2 and 'database' in s2:
    print("  ✅ 测试通过！server 和 database 配置节保留")
else:
    print("  ❌ 测试失败！配置节丢失")

print("\n" + "=" * 60)
