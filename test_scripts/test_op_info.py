"""Test operator info"""
from utils.operator import get_operator_info
from config.settings import get_setting

print("=" * 60)
print("Operator Info Test")
print("=" * 60)

print("\n[1] Nickname from config:")
nickname = get_setting('user_info', 'nickname')
print(f"  nickname: {repr(nickname)}")

print("\n[2] get_operator_info() result:")
info = get_operator_info()
print(f"  name: {repr(info['name'])}")
print(f"  ip: {repr(info['ip'])}")
print(f"  display: {repr(info['display'])}")

print("\n[3] Diagnosis:")
if info['name'] == 'Not set':
    print("  FAIL: nickname read failed")
elif info['name'] == nickname:
    print(f"  OK: nickname correct: {nickname}")
else:
    print(f"  WARNING: mismatch - config={nickname}, actual={info['name']}")

print("\n" + "=" * 60)
