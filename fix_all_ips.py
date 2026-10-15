import os
import json

OLD_IP = "192.168.1.3"
NEW_IP = "192.168.1.3"

# 扩展名白名单，确保只处理文本文件
TEXT_EXTENSIONS = {
    '.py', '.bat', '.md', '.txt', '.json', '.ini', 
    '.spec', '.nsi', '.xml', '.html', '.css', '.js'
}

IGNORED_DIRS = {'.git', '__pycache__', 'build', 'node_modules', '.idea', '.vscode'}

def is_text_file(filename):
    return os.path.splitext(filename)[1].lower() in TEXT_EXTENSIONS

def process_erp_settings(file_path):
    """专门处理 erp_settings.json，使用 json 模块确保安全"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        
        # 检查 server_address 字段
        if 'server_address' in data:
            val = data['server_address']
            if isinstance(val, str) and OLD_IP in val:
                new_val = val.replace(OLD_IP, NEW_IP)
                data['server_address'] = new_val
                modified = True
        
        # 也检查一下是否有其他字段包含旧IP
        for key, value in data.items():
            if key != 'server_address' and isinstance(value, str) and OLD_IP in value:
                data[key] = value.replace(OLD_IP, NEW_IP)
                modified = True

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"[JSON FIX] Modified: {file_path}")
            return True
        return False
    except json.JSONDecodeError:
        print(f"[WARN] Failed to parse JSON: {file_path}, falling back to text replacement.")
        return process_text_file(file_path) # 回退到文本替换
    except Exception as e:
        print(f"[ERR] Error processing json {file_path}: {e}")
        return False

def process_text_file(file_path):
    """通用文本替换"""
    # 尝试不同的编码
    encodings = ['utf-8', 'gbk', 'cp1252']
    content = None
    used_encoding = None

    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
            used_encoding = enc
            break
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    
    if content is None:
        # print(f"[SKIP] Check binary or unknown encoding: {file_path}")
        return False

    if OLD_IP in content:
        new_content = content.replace(OLD_IP, NEW_IP)
        try:
            with open(file_path, 'w', encoding=used_encoding) as f:
                f.write(new_content)
            print(f"[TEXT FIX] Modified: {file_path}")
            return True
        except Exception as e:
            print(f"[ERR] Could not write to {file_path}: {e}")
    
    return False

def main():
    print(f"Starting IP replacement: {OLD_IP} -> {NEW_IP}")
    root_dir = os.getcwd()
    
    count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # 过滤忽略的目录
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # 跳过二进制文件或者非目标扩展名
            if not is_text_file(file):
                continue

            # 特殊处理 erp_settings.json
            if file.lower() == 'erp_settings.json':
                if process_erp_settings(file_path):
                    count += 1
            else:
                if process_text_file(file_path):
                    count += 1
                    
    print(f"Done. Modified {count} files.")

if __name__ == '__main__':
    main()
