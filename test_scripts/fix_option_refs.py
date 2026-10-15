"""修复API服务器中的所有option引用"""
import re


def fix_option_references(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换模式
    patterns = [
        (r'variant\.option(?!\w)', r'variant.option_name'),
        (r'option=product\.option', r'option_name=product.option'),
        (r'"option":\s*variant\.option\s*(?=[\s,}])', 
         r'"option": variant.option_name'),
        (r'option=product\.option_name', r'option_name=product.option_name'),
    ]
    
    # 应用所有替换
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    fix_option_references('api_server_full.py')
    print("✓ 已修复所有 option 引用")
