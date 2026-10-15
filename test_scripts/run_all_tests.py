"""
运行所有功能测试的主入口
按顺序执行产品、库存、销售、发货的测试
"""
import sys
import subprocess
from datetime import datetime

def run_test_script(script_name, description):
    """运行单个测试脚本"""
    print("\n" + "=" * 80)
    print(f"开始执行: {description}")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ['python', script_name],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # 打印输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        success = result.returncode == 0
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} - {description}")
        
        return success
    except Exception as e:
        print(f"❌ 执行测试脚本失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试流程"""
    print("=" * 80)
    print("ERP系统全功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 定义测试脚本列表
    tests = [
        ('test_product_operations.py', '产品管理功能测试'),
        ('test_inventory_operations.py', '库存管理功能测试'),
        ('test_sales_operations.py', '销售管理功能测试'),
        ('test_shipment_operations.py', '发货管理功能测试'),
    ]
    
    results = {}
    
    # 运行所有测试
    for script, description in tests:
        results[description] = run_test_script(script, description)
    
    # 生成总结报告
    print("\n" + "=" * 80)
    print("全功能测试总结报告")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "-" * 80)
    print(f"总体通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 恭喜！所有测试都通过了！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试模块失败，请检查错误信息")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
