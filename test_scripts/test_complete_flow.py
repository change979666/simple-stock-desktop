# -*- coding: utf-8 -*-
"""完整操作者信息流程测试（重建版）

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

本文件按上述意图重建为可重复执行的 unittest 测试：
- 在临时目录（CWD）中运行，隔离 erp_settings.json 与 database.db，
  不触碰真实配置与生产数据库（config/settings 与 database/session 的
  数据路径均基于当前工作目录解析，见 utils/resource_path.get_app_data_path）；
- 数据库链路依赖 SQLAlchemy，不可用时跳过并如实标注；
- GUI 链路依赖 PyQt6，不可用时跳过并如实标注；
- v2 原调用的 `_save_nickname_to_config` 已不存在于当前实现（settings_view
  已改用 load_settings/save_settings 扁平配置 API），GUI 部分按现行 API 断言。
"""
import os
import sys
import tempfile
import unittest

# 仓库根目录加入 sys.path（无论从哪个目录调用，均用绝对路径）
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── 隔离工作目录 ─────────────────────────────────────────────
# 必须在 import 任何仓库模块之前切换 CWD：
# config.settings.CONFIG_FILE = ./erp_settings.json、
# database.session.DB_PATH    = ./database.db 均在模块导入时基于
# 当前工作目录求值（开发环境），切换后自动落到临时目录。
_TMP_DIR = tempfile.mkdtemp(prefix="simple_stock_test_")
os.chdir(_TMP_DIR)

# ── 依赖可用性探测（用于 skipUnless 标注）───────────────────
try:
    import sqlalchemy  # noqa: F401
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

try:
    from PyQt6.QtWidgets import QApplication  # noqa: F401
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


def _write_isolated_config(operator_name):
    """在临时目录写入隔离的扁平配置 erp_settings.json"""
    import json
    path = os.path.join(_TMP_DIR, "erp_settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"operator_name": operator_name}, f, ensure_ascii=False)
    return path


class TestOperatorInfo(unittest.TestCase):
    """v1/v2 共有核心：get_operator_info 读取隔离配置并返回完整结构"""

    def setUp(self):
        _write_isolated_config("张三测试")

    def test_returns_complete_structure(self):
        from utils.operator import get_operator_info
        info = get_operator_info()
        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("ip", info)
        self.assertIn("display", info)
        self.assertEqual(info["name"], "张三测试")

    def test_display_format_is_name_with_ip(self):
        from utils.operator import get_operator_info
        info = get_operator_info()
        # 不硬编码 IP（本机获取，离线时回退 localhost），只断言拼接格式
        self.assertEqual(info["display"], f"{info['name']} ({info['ip']})")

    def test_default_nickname_when_unset(self):
        # 配置文件中无 operator_name 键 → 回退 DEFAULT_SETTINGS 默认值
        import json
        with open(os.path.join(_TMP_DIR, "erp_settings.json"), "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)
        from utils.operator import get_operator_info
        info = get_operator_info()
        self.assertEqual(info["name"], "666")  # DEFAULT_SETTINGS['operator_name']


class TestParseOperatorInfo(unittest.TestCase):
    """v1 第 3 步：parse_operator_info 解析逻辑（纯函数）"""

    @unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy 未安装，无法导入 crud.inventory_logs")
    def test_parse_dict(self):
        from crud.inventory_logs import parse_operator_info
        self.assertEqual(parse_operator_info({"name": "张三"}), "张三")
        self.assertEqual(parse_operator_info({"name": "李四", "ip": "1.2.3.4"}), "李四")
        self.assertEqual(parse_operator_info({}), "系统")

    @unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy 未安装，无法导入 crud.inventory_logs")
    def test_parse_display_string(self):
        from crud.inventory_logs import parse_operator_info
        # "名字 (IP)" 格式 → 提取名字
        self.assertEqual(parse_operator_info("张三 (192.168.1.100)"), "张三")
        # 引号包裹 → 去引号
        self.assertEqual(parse_operator_info("'张三'"), "张三")
        self.assertEqual(parse_operator_info('"张三"'), "张三")
        # 空值 → 系统
        self.assertEqual(parse_operator_info(""), "系统")
        self.assertEqual(parse_operator_info(None), "系统")


@unittest.skipUnless(HAS_SQLALCHEMY, "SQLAlchemy 未安装，无法运行数据库链路测试")
class TestDatabaseFlow(unittest.TestCase):
    """v1 第 2/4 步：写入操作日志并查询（临时数据库，完全隔离）"""

    def setUp(self):
        # CWD 已为临时目录，database.session.DB_PATH 指向临时 database.db。
        # 注意：database.models 实际是包（database/models/__init__.py），其模型
        # 继承自另一份 declarative Base（database/database.py 的 Base 不包含
        # 这些模型）。因此从任一模型类取 __table__.metadata 建表，保证与
        # 生产初始化（database/init_db 等）注册的是同一组模型。
        from database.session import engine, SessionLocal
        from database.models import ActionLog
        ActionLog.__table__.metadata.create_all(engine)
        self.session = SessionLocal()
        _write_isolated_config("张三测试")

    def tearDown(self):
        self.session.close()

    def test_action_log_write_and_query(self):
        from utils.operator import get_operator_info
        from crud.operations import create_action_log
        from crud.inventory_logs import get_all_operation_logs

        info = get_operator_info()
        log = create_action_log(self.session, info, "完整流程测试")
        self.assertIsNotNone(log)
        self.assertIsNotNone(log.id)

        logs = get_all_operation_logs(self.session, limit=10)
        self.assertIsInstance(logs, list)
        self.assertGreaterEqual(len(logs), 1)
        # 至少一条记录的操作者是我们写入的昵称
        self.assertTrue(
            any(log_item.get("operator") == "张三测试" for log_item in logs),
            "最近日志中应包含刚写入的 action log",
        )


@unittest.skipUnless(HAS_PYQT6, "PyQt6 未安装，GUI 昵称同步链路未运行")
class TestGuiNicknameFlow(unittest.TestCase):
    """v2：SettingsView 昵称修改 → 保存 → 验证 → 恢复（隔离配置）"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def test_nickname_sync(self):
        from gui.settings_view import SettingsView
        from config.settings import load_settings

        _write_isolated_config("初始昵称")
        view = SettingsView()
        original = load_settings().get("operator_name", "")

        view.user_nickname.setText("张三测试")
        view.save_settings()

        saved = load_settings().get("operator_name")
        self.assertEqual(saved, "张三测试")

        # 恢复原始昵称，避免影响后续用例
        view.user_nickname.setText(original or "未设置昵称")
        view.save_settings()


if __name__ == "__main__":
    unittest.main(verbosity=2)
