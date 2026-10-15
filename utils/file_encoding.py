"""
文件编码工具模块
提供统一的文件读写接口，确保编码正确性
"""
import configparser
from pathlib import Path
from typing import Union, Dict, Any


def read_text_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """读取文本文件
    
    Args:
        file_path: 文件路径
        encoding: 编码格式，默认 UTF-8
        
    Returns:
        文件内容
    """
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_text_file(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    ensure_no_bom: bool = False
) -> None:
    """写入文本文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式，默认 UTF-8
        ensure_no_bom: 是否确保无 BOM（仅对 UTF-8 有效）
    """
    # 确保父目录存在
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 如果需要无 BOM 的 UTF-8
    if ensure_no_bom and encoding.lower() in ('utf-8', 'utf8'):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)


def read_ini_file(file_path: Union[str, Path]) -> configparser.ConfigParser:
    """读取 INI 配置文件
    
    Args:
        file_path: 配置文件路径
        
    Returns:
        ConfigParser 对象
    """
    config = configparser.ConfigParser()
    config.read(file_path, encoding='utf-8')
    return config


def write_ini_file(
    file_path: Union[str, Path],
    config: Union[configparser.ConfigParser, Dict[str, Dict[str, Any]]],
    ensure_no_bom: bool = True
) -> None:
    """写入 INI 配置文件（UTF-8 无 BOM）
    
    Args:
        file_path: 配置文件路径
        config: ConfigParser 对象或字典
        ensure_no_bom: 是否确保无 BOM，默认 True
    """
    # 确保父目录存在
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # 如果是字典，转换为 ConfigParser
    if isinstance(config, dict):
        cp = configparser.ConfigParser()
        for section, values in config.items():
            cp[section] = values
        config = cp
    
    # 写入文件（UTF-8 无 BOM）
    with open(file_path, 'w', encoding='utf-8') as f:
        config.write(f)


def update_ini_section(
    file_path: Union[str, Path],
    section: str,
    key: str,
    value: str
) -> None:
    """更新 INI 文件中的单个配置项
    
    Args:
        file_path: 配置文件路径
        section: 节名称
        key: 配置键
        value: 配置值
    """
    config = read_ini_file(file_path)
    
    # 确保节存在
    if section not in config:
        config[section] = {}
    
    # 更新值
    config[section][key] = str(value)
    
    # 写回文件
    write_ini_file(file_path, config)


def read_json_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> dict:
    """读取 JSON 文件
    
    Args:
        file_path: 文件路径
        encoding: 编码格式，默认 UTF-8
        
    Returns:
        解析后的字典
    """
    import json
    with open(file_path, 'r', encoding=encoding) as f:
        return json.load(f)


def write_json_file(
    file_path: Union[str, Path],
    data: dict,
    encoding: str = 'utf-8',
    indent: int = 4,
    ensure_ascii: bool = False
) -> None:
    """写入 JSON 文件
    
    Args:
        file_path: 文件路径
        data: 要写入的数据
        encoding: 编码格式，默认 UTF-8
        indent: 缩进空格数，默认 4
        ensure_ascii: 是否转义非 ASCII 字符，默认 False（保留中文）
    """
    import json
    
    # 确保父目录存在
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)


def read_csv_file(
    file_path: Union[str, Path],
    encoding: str = 'utf-8-sig'
) -> list:
    """读取 CSV 文件
    
    Args:
        file_path: 文件路径
        encoding: 编码格式，默认 UTF-8-sig（自动处理 BOM）
        
    Returns:
        行列表
    """
    import csv
    with open(file_path, 'r', encoding=encoding, newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv_file(
    file_path: Union[str, Path],
    data: list,
    fieldnames: list = None,
    encoding: str = 'utf-8-sig'
) -> None:
    """写入 CSV 文件
    
    Args:
        file_path: 文件路径
        data: 数据列表（字典列表）
        fieldnames: 字段名列表，如果为 None 则从第一行数据提取
        encoding: 编码格式，默认 UTF-8-sig（Excel 兼容）
    """
    import csv
    
    # 确保父目录存在
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        return
    
    if fieldnames is None and isinstance(data[0], dict):
        fieldnames = list(data[0].keys())
    
    with open(file_path, 'w', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
