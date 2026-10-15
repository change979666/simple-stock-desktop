"""
统一测试运行脚本
提供便捷的测试执行接口
"""
import sys
import subprocess
from pathlib import Path


def run_tests(test_path=None, verbose=False, coverage=False):
    """运行测试
    
    Args:
        test_path: 测试路径，None 表示运行所有测试
        verbose: 是否显示详细输出
        coverage: 是否生成覆盖率报告
    """
    cmd = ["pytest"]
    
    # 测试路径
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")
    
    # 详细输出
    if verbose:
        cmd.append("-v")
    
    # 覆盖率
    if coverage:
        cmd.extend([
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term"
        ])
    
    # 显示打印输出
    cmd.append("-s")
    
    print("=" * 60)
    print("运行测试命令:", " ".join(cmd))
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("错误: pytest 未安装")
        print("请运行: pip install pytest pytest-cov")
        return 1


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="运行项目测试")
    parser.add_argument(
        "path",
        nargs="?",
        help="测试路径（文件或目录），默认运行所有测试"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="只运行 API 测试"
    )
    parser.add_argument(
        "--crud",
        action="store_true",
        help="只运行 CRUD 测试"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="只运行集成测试"
    )
    
    args = parser.parse_args()
    
    # 确定测试路径
    test_path = args.path
    if args.api:
        test_path = "tests/test_api/"
    elif args.crud:
        test_path = "tests/test_crud/"
    elif args.integration:
        test_path = "tests/test_integration/"
    
    # 运行测试
    exit_code = run_tests(
        test_path=test_path,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
