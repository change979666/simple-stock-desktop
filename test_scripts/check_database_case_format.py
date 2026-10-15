"""
全面检查数据库字段的大小写格式问题
检查范围：
1. ShipmentStatus - 发货状态
2. InventoryStatus - 库存状态
3. API请求/响应的status字段
4. 数据库中实际存储的值
"""
import sys
from pathlib import Path
from typing import Dict, List, Set
import re

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.database import SessionLocal
from database.models import InventoryShipment
from database.inventory import ShipmentStatus, InventoryStatus
from sqlalchemy import text


class CaseFormatChecker:
    """大小写格式检查器"""
    
    def __init__(self):
        self.issues = []
        self.db = SessionLocal()
        
    def check_all(self):
        """执行所有检查"""
        print("=" * 80)
        print("数据库大小写格式全面检查")
        print("=" * 80)
        
        # 1. 检查枚举定义
        self.check_enum_definitions()
        
        # 2. 检查数据库实际值
        self.check_database_values()
        
        # 3. 检查代码中的状态使用
        self.check_code_usage()
        
        # 4. 检查API路由
        self.check_api_routes()
        
        # 5. 生成报告
        self.generate_report()
        
    def check_enum_definitions(self):
        """检查枚举类定义"""
        print("\n" + "=" * 80)
        print("1. 检查枚举类定义")
        print("=" * 80)
        
        # ShipmentStatus
        print("\n📦 ShipmentStatus 枚举:")
        for status in ShipmentStatus:
            name = status.name
            value = status.value
            str_value = str(status)
            
            print(f"  {name:15} = '{value:15}' (str: '{str_value}')")
            
            # 检查名称和值的格式
            if name != name.upper():
                self.issues.append(
                    f"ShipmentStatus.{name} 名称不是全大写"
                )
            if value != value.lower():
                self.issues.append(
                    f"ShipmentStatus.{name} 值不是全小写: '{value}'"
                )
            if '_' in name and name != name.replace('_', '_').upper():
                self.issues.append(
                    f"ShipmentStatus.{name} 下划线格式不正确"
                )
        
        # InventoryStatus
        print("\n📊 InventoryStatus 枚举:")
        for status in InventoryStatus:
            name = status.name
            value = status.value
            str_value = str(status)
            
            print(f"  {name:15} = '{value:15}' (str: '{str_value}')")
            
            # 检查格式
            if name != name.upper():
                self.issues.append(
                    f"InventoryStatus.{name} 名称不是全大写"
                )
            if value != value.lower():
                self.issues.append(
                    f"InventoryStatus.{name} 值不是全小写: '{value}'"
                )
    
    def check_database_values(self):
        """检查数据库中实际存储的值"""
        print("\n" + "=" * 80)
        print("2. 检查数据库实际值")
        print("=" * 80)
        
        # 检查 inventory_shipments 表
        print("\n📦 inventory_shipments.status:")
        try:
            result = self.db.execute(
                text("SELECT DISTINCT status, COUNT(*) FROM inventory_shipments GROUP BY status")
            )
            status_counts = result.fetchall()
            
            valid_values = {str(s) for s in ShipmentStatus}
            
            for status_value, count in status_counts:
                is_valid = status_value in valid_values
                marker = "✅" if is_valid else "❌"
                print(f"  {marker} '{status_value:15}': {count:3} 条")
                
                if not is_valid:
                    self.issues.append(
                        f"数据库中发现无效的shipment status值: '{status_value}' ({count}条记录)"
                    )
                    
                    # 检查是否是大小写问题
                    if status_value.lower() in valid_values:
                        self.issues.append(
                            f"  → 应该是: '{status_value.lower()}' (小写)"
                        )
                    elif status_value.upper().replace(' ', '_') in [s.name for s in ShipmentStatus]:
                        self.issues.append(
                            f"  → 可能是枚举名称而非值: {status_value}"
                        )
        
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
            self.issues.append(f"检查shipment status失败: {e}")
        
        # 检查 inventory_transit_logs 表
        print("\n📝 inventory_transit_logs.old_status/new_status:")
        try:
            result = self.db.execute(
                text(
                    "SELECT DISTINCT old_status, new_status FROM inventory_transit_logs "
                    "WHERE old_status IS NOT NULL OR new_status IS NOT NULL"
                )
            )
            transit_statuses = result.fetchall()
            
            if transit_statuses:
                for old_s, new_s in transit_statuses:
                    old_valid = old_s in valid_values or old_s is None
                    new_valid = new_s in valid_values
                    
                    old_marker = "✅" if old_valid else "❌"
                    new_marker = "✅" if new_valid else "❌"
                    
                    print(f"  {old_marker} '{old_s}' → {new_marker} '{new_s}'")
                    
                    if not old_valid and old_s:
                        self.issues.append(
                            f"transit_log中发现无效的old_status: '{old_s}'"
                        )
                    if not new_valid:
                        self.issues.append(
                            f"transit_log中发现无效的new_status: '{new_s}'"
                        )
            else:
                print("  (暂无状态变更日志)")
        
        except Exception as e:
            print(f"  ❌ 检查失败: {e}")
    
    def check_code_usage(self):
        """检查代码中的状态使用"""
        print("\n" + "=" * 80)
        print("3. 检查代码中的状态使用")
        print("=" * 80)
        
        # 检查关键文件
        files_to_check = [
            'crud/shipment_operations.py',
            'api/routes/shipment.py',
            'gui/shipment_view.py',
            'client/api_client.py'
        ]
        
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
                
            print(f"\n📄 {file_path}:")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找硬编码的状态值
                patterns = [
                    (r"status\s*[=!]=\s*['\"]([A-Z_]+)['\"]", "大写状态值"),
                    (r"status\s*[=!]=\s*['\"]([a-z_]+)['\"]", "小写状态值"),
                    (r"ShipmentStatus\.(\w+)", "枚举引用"),
                    (r"'status':\s*['\"]([^'\"]+)['\"]", "status字段赋值"),
                ]
                
                for pattern, desc in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        matched_value = match.group(1) if match.groups() else match.group(0)
                        print(f"  L{line_num:4}: {desc} → {matched_value}")
    
    def check_api_routes(self):
        """检查API路由中的status处理"""
        print("\n" + "=" * 80)
        print("4. 检查API路由status处理")
        print("=" * 80)
        
        api_file = project_root / 'api' / 'routes' / 'shipment.py'
        if not api_file.exists():
            print("  ⚠️  文件不存在")
            return
        
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查status转换逻辑
        print("\n🔍 状态转换逻辑:")
        
        # 查找 ShipmentStatus(xxx) 的调用
        enum_calls = re.finditer(r'ShipmentStatus\(([^)]+)\)', content)
        for match in enum_calls:
            line_num = content[:match.start()].count('\n') + 1
            arg = match.group(1).strip()
            print(f"  L{line_num:4}: ShipmentStatus({arg})")
        
        # 查找 .value 或 .name 的使用
        attr_uses = re.finditer(r'\.(?:value|name)\b', content)
        for match in attr_uses:
            line_num = content[:match.start()].count('\n') + 1
            # 获取上下文
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context = content[start:end].replace('\n', ' ')
            print(f"  L{line_num:4}: {context}")
    
    def generate_report(self):
        """生成检查报告"""
        print("\n" + "=" * 80)
        print("检查报告")
        print("=" * 80)
        
        if not self.issues:
            print("\n✅ 所有检查通过！没有发现大小写格式问题。")
            print("\n格式规范:")
            print("  • 枚举名称: 全大写下划线 (如 IN_TRANSIT)")
            print("  • 枚举值: 全小写下划线 (如 'in_transit')")
            print("  • 数据库存储: 小写下划线格式")
            print("  • 代码使用: ShipmentStatus.IN_TRANSIT")
            print("  • 字符串转换: str(ShipmentStatus.IN_TRANSIT) → 'in_transit'")
        else:
            print(f"\n❌ 发现 {len(self.issues)} 个问题:\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")
            
            print("\n建议修复步骤:")
            print("  1. 运行 fix_shipment_status.py 统一数据库值为小写")
            print("  2. 确保所有代码使用枚举对象而非硬编码字符串")
            print("  3. API接口使用 str(ShipmentStatus.XXX) 转换为字符串")
            print("  4. 数据库查询时使用小写值进行比较")
        
        print("\n" + "=" * 80)
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'db'):
            self.db.close()


def main():
    """主函数"""
    checker = CaseFormatChecker()
    try:
        checker.check_all()
    except Exception as e:
        print(f"\n❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0 if not checker.issues else 1


if __name__ == '__main__':
    sys.exit(main())
