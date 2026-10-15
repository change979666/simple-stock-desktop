# -*- coding: utf-8 -*-
"""test_complete_flow 的隔离子进程执行体（不直接参与 pytest 收集）

由 test_complete_flow.py 以独立 Python 子进程方式调用，且父进程保证
cwd=临时目录。这样 config/settings.CONFIG_FILE 与 database/session.DB_PATH
（两者均为模块级常量，import 时基于当前工作目录求值）只在子进程内、
基于临时目录求值；子进程退出后所有模块缓存与临时产物随之释放，
主进程的 CWD 与模块缓存完全不受影响。

用法: python _complete_flow_child.py <mode> <tmp_dir>
mode: operator_info | parse | db_flow | gui_flow
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _write_isolated_config(tmp, operator_name):
    """在临时目录写入隔离的扁平配置 erp_settings.json"""
    import json
    path = os.path.join(tmp, "erp_settings.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"operator_name": operator_name}, f, ensure_ascii=False)


def check_operator_info(tmp):
    """get_operator_info：结构完整性 / display 格式 / 默认昵称回退"""
    _write_isolated_config(tmp, "张三测试")
    from utils.operator import get_operator_info

    info = get_operator_info()
    assert isinstance(info, dict), info
    assert {"name", "ip", "display"} <= set(info)
    assert info["name"] == "张三测试"
    # 不硬编码 IP（本机获取，离线时回退 localhost），只断言拼接格式
    assert info["display"] == f"{info['name']} ({info['ip']})"

    # 配置文件中无 operator_name 键 → 回退 DEFAULT_SETTINGS 默认值
    import json
    with open(os.path.join(tmp, "erp_settings.json"), "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False)
    info2 = get_operator_info()
    assert info2["name"] == "666"  # DEFAULT_SETTINGS['operator_name']
    print("operator_info checks OK")


def check_parse(tmp):
    """parse_operator_info：dict / 展示字符串 / 引号 / 空值（tmp 仅保持统一签名）"""
    from crud.inventory_logs import parse_operator_info

    assert parse_operator_info({"name": "张三"}) == "张三"
    assert parse_operator_info({"name": "李四", "ip": "1.2.3.4"}) == "李四"
    assert parse_operator_info({}) == "系统"
    # "名字 (IP)" 格式 → 提取名字
    assert parse_operator_info("张三 (192.168.1.100)") == "张三"
    # 引号包裹 → 去引号
    assert parse_operator_info("'张三'") == "张三"
    assert parse_operator_info('"张三"') == "张三"
    # 空值 → 系统
    assert parse_operator_info("") == "系统"
    assert parse_operator_info(None) == "系统"
    print("parse checks OK")


def check_db_flow(tmp):
    """操作日志写入与查询（临时数据库；models 实为包，用 ActionLog 的 metadata 建表）"""
    _write_isolated_config(tmp, "张三测试")
    from database.session import engine, SessionLocal
    from database.models import ActionLog

    # database.models 实际是包（database/models/__init__.py），其模型继承自
    # 另一份 declarative Base；从任一模型类取 __table__.metadata 建表，
    # 与生产初始化注册的是同一组模型。
    ActionLog.__table__.metadata.create_all(engine)
    session = SessionLocal()
    try:
        from utils.operator import get_operator_info
        from crud.operations import create_action_log
        from crud.inventory_logs import get_all_operation_logs

        info = get_operator_info()
        log = create_action_log(session, info, "完整流程测试")
        assert log is not None
        assert log.id is not None

        logs = get_all_operation_logs(session, limit=10)
        assert isinstance(logs, list)
        assert len(logs) >= 1
        assert any(item.get("operator") == "张三测试" for item in logs), \
            "最近日志中应包含刚写入的 action log"
        print("db_flow checks OK")
    finally:
        session.close()


def check_gui_flow(tmp):
    """SettingsView 昵称修改 → 保存 → 验证 → 恢复（PyQt6 可用时调用）"""
    from PyQt6.QtWidgets import QApplication
    from gui.settings_view import SettingsView
    from config.settings import load_settings

    _write_isolated_config(tmp, "初始昵称")
    app = QApplication(sys.argv)
    view = SettingsView()
    original = load_settings().get("operator_name", "")

    view.user_nickname.setText("张三测试")
    view.save_settings()
    assert load_settings().get("operator_name") == "张三测试"

    # 恢复原始昵称，避免影响后续用例
    view.user_nickname.setText(original or "未设置昵称")
    view.save_settings()
    print("gui_flow checks OK")


_CHECKS = {
    "operator_info": check_operator_info,
    "parse": check_parse,
    "db_flow": check_db_flow,
    "gui_flow": check_gui_flow,
}


def main():
    mode, tmp = sys.argv[1], sys.argv[2]
    assert os.path.isdir(tmp), f"临时目录不存在: {tmp}"
    # 父进程已保证 cwd=临时目录；此处防御性校验，防止误用
    assert os.path.abspath(os.getcwd()) == os.path.abspath(tmp), \
        f"cwd 不是临时目录: {os.getcwd()}"
    _CHECKS[mode](tmp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
