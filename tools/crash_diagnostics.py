"""
程序崩溃诊断工具
扫描所有代码，找出可能导致崩溃的问题
"""

import os
import re
from pathlib import Path
from collections import defaultdict

class CrashDiagnostics:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.issues = defaultdict(list)
        
    def scan_all(self):
        """扫描所有潜在问题"""
        print("=" * 80)
        print("程序崩溃诊断工具")
        print("=" * 80)
        
        self.check_unprotected_operations()
        self.check_none_handling()
        self.check_type_conversions()
        self.check_resource_leaks()
        self.check_infinite_loops()
        
        self.generate_report()
    
    def check_unprotected_operations(self):
        """检查未保护的危险操作"""
        print("\n[1] 检查未保护的危险操作...")
        
        patterns = [
            (r'\.get_all_products\(\)', '数据库查询'),
            (r'\.get_sales_orders\(\)', '数据库查询'),
            (r'dal\.\w+\(', 'DAL层调用'),
            (r'api_client\.\w+\(', 'API调用'),
            (r'open\(', '文件操作'),
            (r'\.read\(\)', '文件读取'),
            (r'\.write\(', '文件写入'),
            (r'json\.loads\(', 'JSON解析'),
            (r'json\.load\(', 'JSON加载'),
            (r'int\(', '类型转换'),
            (r'float\(', '类型转换'),
        ]
        
        gui_files = list(self.project_root.glob('gui/**/*.py'))
        
        for file_path in gui_files:
            if file_path.name.startswith('__'):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # 找出所有函数定义
                functions = []
                current_func = None
                func_start = 0
                indent_level = 0
                
                for i, line in enumerate(lines, 1):
                    if re.match(r'^\s*def \w+\(', line):
                        if current_func:
                            functions.append((current_func, func_start, i-1, indent_level))
                        match = re.search(r'def (\w+)\(', line)
                        current_func = match.group(1)
                        func_start = i
                        indent_level = len(line) - len(line.lstrip())
                    elif current_func and line.strip() and not line.strip().startswith('#'):
                        # 检查缩进是否回到原位（函数结束）
                        curr_indent = len(line) - len(line.lstrip())
                        if curr_indent <= indent_level and not line.strip().startswith('@'):
                            functions.append((current_func, func_start, i-1, indent_level))
                            current_func = None
                
                if current_func:
                    functions.append((current_func, func_start, len(lines), indent_level))
                
                # 检查每个函数
                for func_name, start, end, indent in functions:
                    func_content = '\n'.join(lines[start-1:end])
                    has_try = 'try:' in func_content
                    
                    # 检查危险操作
                    for pattern, op_type in patterns:
                        if re.search(pattern, func_content):
                            if not has_try:
                                rel_path = file_path.relative_to(self.project_root)
                                self.issues['unprotected_ops'].append({
                                    'file': str(rel_path),
                                    'function': func_name,
                                    'line': start,
                                    'operation': op_type,
                                    'severity': 'HIGH' if 'api' in pattern or 'dal' in pattern else 'MEDIUM'
                                })
                            break
                
            except Exception as e:
                print(f"  ⚠️  扫描文件出错 {file_path}: {e}")
        
        count = len(self.issues['unprotected_ops'])
        print(f"  找到 {count} 个未保护的危险操作")
    
    def check_none_handling(self):
        """检查None值处理"""
        print("\n[2] 检查None值处理...")
        
        dangerous_patterns = [
            r'\.get\([^)]+\)\.\w+',  # dict.get().attribute
            r'\[\w+\]\.\w+',  # list[index].attribute
            r'= \w+\(\)[\s\n]+\w+\.\w+',  # func() followed by attribute access
        ]
        
        py_files = list(self.project_root.glob('gui/**/*.py'))
        
        for file_path in py_files:
            if file_path.name.startswith('__'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    for pattern in dangerous_patterns:
                        if re.search(pattern, line) and 'if' not in line and 'None' not in line:
                            # 检查前后几行是否有None检查
                            context = '\n'.join(lines[max(0, i-3):min(len(lines), i+2)])
                            if 'if' not in context or 'None' not in context:
                                rel_path = file_path.relative_to(self.project_root)
                                self.issues['none_handling'].append({
                                    'file': str(rel_path),
                                    'line': i,
                                    'code': line.strip(),
                                    'severity': 'MEDIUM'
                                })
                                break
            except Exception as e:
                print(f"  ⚠️  扫描文件出错 {file_path}: {e}")
        
        count = len(self.issues['none_handling'])
        print(f"  找到 {count} 个可能的None访问问题")
    
    def check_type_conversions(self):
        """检查类型转换"""
        print("\n[3] 检查危险的类型转换...")
        
        patterns = [
            (r'int\([^)]+\)', 'int转换'),
            (r'float\([^)]+\)', 'float转换'),
            (r'\.split\([^)]*\)\[\d+\]', '字符串分割索引'),
        ]
        
        py_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in py_files:
            if file_path.name.startswith('__') or 'test_' in file_path.name:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    for pattern, conv_type in patterns:
                        if re.search(pattern, line):
                            # 检查是否在try块内
                            context = ''.join(lines[max(0, i-10):i])
                            if 'try:' not in context:
                                rel_path = file_path.relative_to(self.project_root)
                                self.issues['type_conversion'].append({
                                    'file': str(rel_path),
                                    'line': i,
                                    'type': conv_type,
                                    'code': line.strip(),
                                    'severity': 'LOW'
                                })
            except Exception as e:
                continue
        
        count = len(self.issues['type_conversion'])
        print(f"  找到 {count} 个可能失败的类型转换")
    
    def check_resource_leaks(self):
        """检查资源泄漏"""
        print("\n[4] 检查资源泄漏...")
        
        py_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in py_files:
            if file_path.name.startswith('__'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查open()是否使用with
                if 'open(' in content and 'with open' not in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'open(' in line and 'with' not in line and '#' not in line:
                            rel_path = file_path.relative_to(self.project_root)
                            self.issues['resource_leak'].append({
                                'file': str(rel_path),
                                'line': i,
                                'resource': '文件句柄',
                                'code': line.strip(),
                                'severity': 'MEDIUM'
                            })
                
            except Exception as e:
                continue
        
        count = len(self.issues['resource_leak'])
        print(f"  找到 {count} 个可能的资源泄漏")
    
    def check_infinite_loops(self):
        """检查无限循环"""
        print("\n[5] 检查潜在的无限循环...")
        
        py_files = list(self.project_root.glob('**/*.py'))
        
        for file_path in py_files:
            if file_path.name.startswith('__'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    if re.match(r'^\s*while\s+True:', line):
                        # 检查循环体内是否有break
                        loop_body = []
                        indent = len(line) - len(line.lstrip())
                        for j in range(i, min(i+20, len(lines))):
                            next_line = lines[j]
                            next_indent = len(next_line) - len(next_line.lstrip())
                            if next_indent > indent:
                                loop_body.append(next_line)
                            elif next_indent <= indent and next_line.strip():
                                break
                        
                        has_break = any('break' in l for l in loop_body)
                        has_return = any('return' in l for l in loop_body)
                        
                        if not (has_break or has_return):
                            rel_path = file_path.relative_to(self.project_root)
                            self.issues['infinite_loop'].append({
                                'file': str(rel_path),
                                'line': i,
                                'severity': 'HIGH'
                            })
            except Exception as e:
                continue
        
        count = len(self.issues['infinite_loop'])
        print(f"  找到 {count} 个可能的无限循环")
    
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "=" * 80)
        print("诊断报告")
        print("=" * 80)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        if total_issues == 0:
            print("\n✅ 未发现明显的崩溃风险！")
            return
        
        print(f"\n⚠️  发现 {total_issues} 个潜在问题")
        
        # 按严重程度统计
        severity_count = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for category, issues_list in self.issues.items():
            if not issues_list:
                continue
            
            print(f"\n{'='*80}")
            print(f"【{category.upper().replace('_', ' ')}】 - {len(issues_list)} 个问题")
            print('='*80)
            
            # 按严重程度分组
            by_severity = defaultdict(list)
            for issue in issues_list:
                severity = issue.get('severity', 'LOW')
                by_severity[severity].append(issue)
                severity_count[severity] += 1
            
            # 先显示HIGH
            for severity in ['HIGH', 'MEDIUM', 'LOW']:
                if severity not in by_severity:
                    continue
                
                print(f"\n  [{severity}] - {len(by_severity[severity])} 个")
                
                # 只显示前5个
                for issue in by_severity[severity][:5]:
                    print(f"    📍 {issue['file']}:{issue.get('line', '?')}")
                    if 'function' in issue:
                        print(f"       函数: {issue['function']}")
                    if 'code' in issue:
                        print(f"       代码: {issue['code'][:60]}...")
                    if 'operation' in issue:
                        print(f"       操作: {issue['operation']}")
                
                if len(by_severity[severity]) > 5:
                    print(f"    ... 还有 {len(by_severity[severity]) - 5} 个类似问题")
        
        # 总结
        print(f"\n{'='*80}")
        print("严重程度统计:")
        print(f"  🔴 HIGH:   {severity_count['HIGH']} 个（需要立即修复）")
        print(f"  🟡 MEDIUM: {severity_count['MEDIUM']} 个（建议修复）")
        print(f"  🟢 LOW:    {severity_count['LOW']} 个（可以稍后处理）")
        print("="*80)
        
        # 保存详细报告
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """保存详细报告到文件"""
        report_file = self.project_root / 'crash_diagnostic_report.txt'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("程序崩溃诊断详细报告\n")
            f.write("=" * 80 + "\n\n")
            
            for category, issues_list in self.issues.items():
                if not issues_list:
                    continue
                
                f.write(f"\n{'='*80}\n")
                f.write(f"{category.upper().replace('_', ' ')}\n")
                f.write(f"{'='*80}\n\n")
                
                for i, issue in enumerate(issues_list, 1):
                    f.write(f"{i}. [{issue.get('severity', 'LOW')}] ")
                    f.write(f"{issue['file']}:{issue.get('line', '?')}\n")
                    
                    for key, value in issue.items():
                        if key not in ['file', 'line', 'severity']:
                            f.write(f"   {key}: {value}\n")
                    f.write("\n")
        
        print(f"\n📄 详细报告已保存到: {report_file}")


if __name__ == '__main__':
    import sys
    
    project_root = Path(__file__).parent.parent
    
    diagnostics = CrashDiagnostics(project_root)
    diagnostics.scan_all()
