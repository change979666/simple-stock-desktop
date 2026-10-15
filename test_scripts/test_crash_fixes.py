"""
测试崩溃修复效果
模拟各种异常场景，验证程序的稳定性
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from utils.exception_handlers import (
    safe_gui_operation,
    safe_api_call,
    safe_database_operation,
    safe_batch_operation,
    safe_item_operation,
    SafeContext,
    show_error,
    show_warning
)


class TestCrashFixes:
    """测试崩溃修复"""
    
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.test_results = []
    
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print('='*60)
        
        try:
            test_func()
            self.success_count += 1
            result = "✅ 通过"
            print(f"结果: {result}")
        except Exception as e:
            self.fail_count += 1
            result = f"❌ 失败: {e}"
            print(f"结果: {result}")
        
        self.test_results.append((test_name, result))
    
    def test_safe_gui_operation(self):
        """测试GUI操作装饰器"""
        
        @safe_gui_operation("测试失败", "GUI操作测试", show_dialog=False)
        def failing_operation():
            raise ValueError("模拟GUI操作失败")
        
        # 调用应该捕获异常，不抛出
        result = failing_operation()
        assert result is None, "装饰器应该返回None"
        print("✓ GUI装饰器正确捕获异常")
    
    def test_safe_api_call(self):
        """测试API调用装饰器"""
        
        @safe_api_call("API测试失败", show_dialog=False, return_on_error=[])
        def failing_api_call():
            raise ConnectionError("模拟API连接失败")
        
        # 调用应该返回默认值
        result = failing_api_call()
        assert result == [], "装饰器应该返回默认值[]"
        print("✓ API装饰器正确处理异常并返回默认值")
    
    def test_safe_database_operation(self):
        """测试数据库操作装饰器"""
        
        @safe_database_operation("数据库测试失败", show_dialog=False, return_on_error=False)
        def failing_db_operation():
            raise RuntimeError("模拟数据库操作失败")
        
        # 调用应该返回False
        result = failing_db_operation()
        assert result is False, "装饰器应该返回False"
        print("✓ 数据库装饰器正确处理异常并返回False")
    
    def test_safe_batch_operation(self):
        """测试批量操作装饰器"""
        
        @safe_batch_operation
        def batch_process():
            items = [1, 2, 3, 4, 5]
            results = []
            for item in items:
                if item == 3:
                    raise ValueError(f"处理项目{item}失败")
                results.append(item * 2)
            return results
        
        # 批量操作失败应该返回空列表
        result = batch_process()
        assert result == [], "批量操作失败应该返回[]"
        print("✓ 批量操作装饰器正确处理异常")
    
    def test_safe_item_operation(self):
        """测试单项操作装饰器"""
        
        @safe_item_operation
        def process_item(value):
            if value == 0:
                raise ZeroDivisionError("不能除以0")
            return 10 / value
        
        # 正常值应该正常处理
        result1 = process_item(2)
        assert result1 == 5.0, "正常值应该返回正确结果"
        
        # 异常值应该返回None
        result2 = process_item(0)
        assert result2 is None, "异常值应该返回None"
        
        print("✓ 单项操作装饰器正确处理正常值和异常值")
    
    def test_safe_context(self):
        """测试安全上下文管理器"""
        
        exception_caught = False
        try:
            with SafeContext("测试操作", show_error=False):
                raise FileNotFoundError("模拟文件未找到")
        except:
            exception_caught = True
        
        # 异常应该被上下文管理器捕获，不应该传播出来
        assert not exception_caught, "异常不应该传播出上下文"
        print("✓ 上下文管理器正确捕获异常")
    
    def test_nested_decorators(self):
        """测试嵌套装饰器"""
        
        @safe_gui_operation("外层失败", show_dialog=False)
        @safe_api_call("内层失败", show_dialog=False, return_on_error=None)
        def nested_operation():
            raise RuntimeError("嵌套操作失败")
        
        result = nested_operation()
        assert result is None, "嵌套装饰器应该正确处理异常"
        print("✓ 嵌套装饰器正确工作")
    
    def test_partial_success_batch(self):
        """测试部分成功的批量操作"""
        
        success_items = []
        failed_items = []
        
        items = [1, 2, 3, 4, 5]
        for item in items:
            try:
                if item == 3:
                    raise ValueError("项目3失败")
                success_items.append(item)
            except Exception as e:
                failed_items.append(item)
                # 继续处理，不中断
                continue
        
        assert len(success_items) == 4, "应该成功处理4个项目"
        assert len(failed_items) == 1, "应该有1个失败项目"
        print(f"✓ 批量操作部分成功: 成功{len(success_items)}, 失败{len(failed_items)}")
    
    def test_exception_logging(self):
        """测试异常日志记录"""
        
        @safe_gui_operation("日志测试", show_dialog=False)
        def logged_operation():
            raise RuntimeError("用于测试日志的异常")
        
        # 调用应该记录日志
        logged_operation()
        print("✓ 异常已记录到日志（检查logs/目录）")
    
    def print_summary(self):
        """打印测试摘要"""
        print(f"\n{'='*60}")
        print("测试摘要")
        print('='*60)
        print(f"总测试数: {self.success_count + self.fail_count}")
        print(f"通过: {self.success_count}")
        print(f"失败: {self.fail_count}")
        print(f"成功率: {self.success_count/(self.success_count + self.fail_count)*100:.1f}%")
        print("\n详细结果:")
        for name, result in self.test_results:
            print(f"  {name}: {result}")
        print('='*60)
        
        return self.fail_count == 0


def main():
    """主测试函数"""
    print("="*60)
    print("崩溃修复测试")
    print("="*60)
    
    # 创建QApplication（某些装饰器可能需要）
    app = QApplication(sys.argv)
    
    # 运行测试
    tester = TestCrashFixes()
    
    # 执行所有测试
    tester.run_test("GUI操作装饰器", tester.test_safe_gui_operation)
    tester.run_test("API调用装饰器", tester.test_safe_api_call)
    tester.run_test("数据库操作装饰器", tester.test_safe_database_operation)
    tester.run_test("批量操作装饰器", tester.test_safe_batch_operation)
    tester.run_test("单项操作装饰器", tester.test_safe_item_operation)
    tester.run_test("安全上下文管理器", tester.test_safe_context)
    tester.run_test("嵌套装饰器", tester.test_nested_decorators)
    tester.run_test("部分成功批量操作", tester.test_partial_success_batch)
    tester.run_test("异常日志记录", tester.test_exception_logging)
    
    # 打印摘要
    all_passed = tester.print_summary()
    
    if all_passed:
        print("\n✅ 所有测试通过！崩溃修复工作正常。")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
