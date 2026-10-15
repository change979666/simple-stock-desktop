# -*- coding: utf-8 -*-
"""完整操作者信息流程测试（隔离版 · 最终审计修订）

原 test_complete_flow.py 在 Git 首次提交（2ed99f3）时即已损坏：
脚本式（v1）与函数式（v2）两个版本被错误拼接，多处语句粘连（如
`print("=" * 80)import sys`），py_compile 无法通过；Git 历史中的
同名文件同样损坏，无完好源文件可直接恢复。

经审计，原脚本意图为：
  v1（脚本式）: get_operator_info → create_action_log →
                parse_operator_info → get_all_operation_logs
                （操作者信息与操作日志数据链路）
  v2（函数式）: SettingsView 昵称加载 → 修改 → 保存 → 验证 → 恢复
                （UI 昵称同步链路）

隔离设计（本轮审计后修订，含测试隔离审计结论）：
1. 本文件在模块导入阶段不做任何全局修改：不 chdir、不修改 sys.path、
   不 import 任何仓库模块。全部业务断言迁至 `_complete_flow_child.py`，
   由本文件以独立 Python 子进程执行（cwd=临时目录）。
   —— 避免与同进程其他测试共享 CWD / 模块缓存 / 配置路径常量。
2. 关键背景：config/settings.CONFIG_FILE 与 database/session.DB_PATH 均为
   模块级常量，import 时基于当前工作目录解析并永久缓存；若在主进程
   import，即使事后恢复 CWD，缓存路径仍指向临时目录，会污染同进程内
   后续 import 相同模块的其它测试。因此所有仓库模块导入都只发生在
   独立子进程中，进程退出即释放，主进程缓存不受影响。
3. 生命周期由 tempfile.TemporaryDirectory 管理：临时 erp_settings.json、
   database.db、__pycache__ 等随上下文退出自动清理，不留残留。
4. 生产数据隔离：任何用例不触碰仓库根的真实 config.ini / erp_settings.json /
   database.db；子进程 cwd 恒为临时目录（子进程内防御性校验）。
5. 依赖标注：数据库链路依赖 SQLAlchemy，GUI 链路依赖 PyQt6，缺失时
   跳过并如实标注（探测 import 本身无副作用，不初始化仓库模块）。
6. v2 原调用的 `_save_nickname_to_config` 已不存在于当前实现（settings_view
   已改用 load_settings/save_settings 扁平配置 API），GUI 断言按现行 API。
"""
import os
import subprocess
import sys
import tempfile
import unittest

# 子进程执行体：定位用绝对路径（父进程不修改 sys.path）
_CHILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_complete_flow_child.py")

# 依赖可用性探测（仅探测包能否导入，不导入任何仓库模块，无路径/缓存副作用）
try:
    import sqlalchemy  # noqa: F401
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

try:
    import PyQt6  # noqa: F401
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


def _run_child(mode, tmp):
    """在临时目录中以子进程执行对应检查；失败时附带子进程输出便于诊断"""
    proc = subprocess.run(
        [sys.executable, _CHILD, mode, tmp],
        cwd=tmp,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"子进程检查 [{mode}] 失败 (exit {proc.returncode})\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )


class TestOperatorInfo(unittest.TestCase):
    """v1/v2 共有核心：get_operator_info 结构 / display 格式 / 默认昵称回退"""

    def test_operator_info_isolated(self):
        with tempfile.TemporaryDirectory(prefix="simple_stock_test_") as tmp:
            _run_child("operator_info", tmp)


class TestParseOperatorInfo(unittest.TestCase):
    """v1 第 3 步：parse_operator_info 解析逻辑（子进程内 import，避免
    crud.inventory_logs → database.session 的模块级 DB 路径初始化副作用）"""

    @unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy 未安装，无法导入 crud.inventory_logs")
    def test_parse_operator_info_variants(self):
        with tempfile.TemporaryDirectory(prefix="simple_stock_test_") as tmp:
            _run_child("parse", tmp)


@unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy 未安装，无法运行数据库链路测试")
class TestDatabaseFlow(unittest.TestCase):
    """v1 第 2/4 步：操作日志写入与查询（临时数据库，子进程隔离）"""

    def test_action_log_write_and_query(self):
        with tempfile.TemporaryDirectory(prefix="simple_stock_test_") as tmp:
            _run_child("db_flow", tmp)


@unittest.skipUnless(HAS_PYQT6, "PyQt6 未安装，GUI 昵称同步链路未运行")
class TestGuiNicknameFlow(unittest.TestCase):
    """v2：SettingsView 昵称修改 → 保存 → 验证 → 恢复（PyQt6 可用时子进程执行）"""

    def test_nickname_sync(self):
        with tempfile.TemporaryDirectory(prefix="simple_stock_test_") as tmp:
            _run_child("gui_flow", tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
