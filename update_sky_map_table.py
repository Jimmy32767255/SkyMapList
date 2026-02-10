#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def parse_level_list(file_path: Path) -> List[str]:
    """
    解析地图枚举文件，提取所有地图标识符
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 匹配类似 "Day Sk8 Dawn Dusk Maze PHub" 这样的标识符列表
        # 移除换行符和多余空格，然后分割
        content = content.replace('\n', ' ').replace('\r', ' ')
        content = re.sub(r'\s+', ' ', content).strip()
        
        if not content:
            return []
        
        # 过滤空字符串
        return [id for id in content.split(' ') if id]
    except Exception as e:
        print(f"解析地图枚举文件失败: {e}")
        return []

def parse_strings_file(file_path: Path) -> Dict[str, str]:
    """
    解析.strings文件，提取键值对
    格式: "key" = "value";
    """
    translations = {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式匹配所有键值对
        pattern = re.compile(r'"([^"]+)"\s*=\s*"([^"]*)"\s*;')
        matches = pattern.findall(content)
        
        for key, value in matches:
            translations[key] = value
    
    except Exception as e:
        print(f"解析翻译文件失败 {file_path}: {e}")
    
    return translations

def read_existing_table(table_path: Path) -> Tuple[List[str], Dict[str, Dict[str, str]], List[str]]:
    """
    读取现有的Markdown表格，提取表头、现有数据和非表格内容
    返回表头行、地图数据字典和非表格内容
    """
    headers = []
    existing_data = {}
    non_table_content = []
    
    try:
        with open(table_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 分割成行
        lines = content.split('\n')
        
        # 查找表格开始位置
        table_start = -1
        for i, line in enumerate(lines):
            if line.startswith('|') and '标识符' in line:
                table_start = i
                break
        
        if table_start == -1:
            print("未找到表格，将创建新表格")
            headers = ['标识符', '中文名', '玩家社区称呼', '英文名', '翻译键', '存在版本', '隶属于', '截图', '注释']
            non_table_content = lines
            return headers, existing_data, non_table_content
        
        # 保存表格之前的内容
        non_table_content = lines[:table_start]
        
        # 提取表头
        header_line = lines[table_start].strip()
        headers = [cell.strip() for cell in header_line.strip('|').split('|')]
        
        # 从分隔行之后开始读取数据
        for i in range(table_start + 2, len(lines)):
            line = lines[i].strip()
            if not line.startswith('|'):
                # 表格结束，保存剩余内容
                non_table_content.extend(lines[i:])
                break
            
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            if len(cells) >= 1 and cells[0] and cells[0] != '--':
                identifier = cells[0]
                
                # 确保有足够的列
                while len(cells) < len(headers):
                    cells.append('')
                
                existing_data[identifier] = {}
                for j, header in enumerate(headers):
                    if j < len(cells):
                        existing_data[identifier][header] = cells[j]
                    else:
                        existing_data[identifier][header] = ''
        
        print(f"成功读取 {len(existing_data)} 条现有记录")
        
    except Exception as e:
        print(f"读取现有表格失败: {e}")
        # 返回默认表头
        headers = ['标识符', '中文名', '玩家社区称呼', '英文名', '翻译键', '存在版本', '隶属于', '截图', '注释']
    
    return headers, existing_data, non_table_content

def get_translation_key(identifier: str) -> str:
    """
    根据标识符生成翻译键
    例如: Day -> name_day
    """
    # 将标识符转换为小写，并在前面加上"name_"
    return f"name_{identifier.lower()}"

def merge_table_data(
    identifiers: List[str],
    chinese_translations: Dict[str, str],
    english_translations: Dict[str, str],
    existing_data: Dict[str, Dict[str, str]]
) -> Dict[str, Dict[str, str]]:
    """
    合并表格数据：已有数据保持不变，只添加新数据
    """
    merged_data = {}
    
    # 首先添加所有现有数据
    for identifier, data in existing_data.items():
        merged_data[identifier] = data.copy()
    
    # 然后添加新标识符的数据
    new_count = 0
    for identifier in sorted(identifiers):
        if identifier in merged_data:
            # 已存在，跳过
            continue
        
        translation_key = get_translation_key(identifier)
        
        # 获取中文名和英文名
        chinese_name = chinese_translations.get(translation_key, '')
        english_name = english_translations.get(translation_key, '')
        
        # 如果两个翻译都没有找到，翻译键也置空
        if not chinese_name and not english_name:
            translation_key = ''
        
        # 创建新条目
        merged_data[identifier] = {
            '标识符': identifier,
            '中文名': chinese_name,
            '玩家社区称呼': '',
            '英文名': english_name,
            '翻译键': translation_key if translation_key else '',
            '存在版本': '',
            '隶属于': '',
            '截图': '',
            '注释': ''
        }
        new_count += 1
        
        # 调试信息
        if not chinese_name and not english_name:
            print(f"调试: 新标识符 {identifier} 未找到翻译，翻译键: {get_translation_key(identifier)}")
    
    print(f"新增了 {new_count} 条记录，保留了 {len(existing_data)} 条原有记录")
    return merged_data

def write_table(table_path: Path, headers: List[str], data: Dict[str, Dict[str, str]], non_table_content: List[str]):
    """
    写入更新后的Markdown表格
    """
    try:
        # 构建表格内容
        table_lines = []
        
        # 构建表头行
        header_row = '|'
        for header in headers:
            # 确保单元格内容不为空
            cell_content = header.strip() if header.strip() else ' '
            header_row += f' {cell_content} |'
        
        table_lines.append(header_row)
        
        # 构建分隔行
        separator_row = '|'
        for header in headers:
            separator_row += ' --- |'
        
        table_lines.append(separator_row)
        
        # 数据行（按标识符排序）
        for identifier in sorted(data.keys()):
            row_data = data[identifier]
            data_row = '|'
            for header in headers:
                value = row_data.get(header, '')
                # 确保单元格内容不为空
                cell_content = str(value).strip() if str(value).strip() else ' '
                data_row += f' {cell_content} |'
            table_lines.append(data_row)
        
        # 处理非表格内容
        if non_table_content:
            # 清理非表格内容，移除末尾的连续空行
            while non_table_content and non_table_content[-1].strip() == '':
                non_table_content.pop()
            
            # 确保非表格内容以换行符结束
            non_table_text = '\n'.join(non_table_content)
            if non_table_text and not non_table_text.endswith('\n'):
                non_table_text += '\n'
        else:
            non_table_text = ''
        
        # 构建完整内容：非表格内容 + 空行 + 表格
        # 关键：确保表格前有一个空行
        if non_table_text and not non_table_text.endswith('\n\n'):
            # 如果非表格内容不以两个换行符结束，添加一个空行
            if non_table_text.endswith('\n'):
                # 已有一个换行符，再加一个
                non_table_text += '\n'
            else:
                # 没有换行符，添加两个
                non_table_text += '\n\n'
        
        # 构建最终内容
        if non_table_text:
            new_content = non_table_text + '\n'.join(table_lines)
        else:
            # 如果没有非表格内容，在表格前添加一个空行
            new_content = '\n' + '\n'.join(table_lines)
        
        # 写入文件
        with open(table_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(new_content)
        
        print(f"表格已成功更新到: {table_path}")
        print(f"共 {len(data)} 条记录")
        
    except Exception as e:
        print(f"写入表格失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description='自动更新《光•遇》地图Dump表')
    parser.add_argument('--table', help='Dump表路径（《光•遇》所有地图.md）')
    parser.add_argument('--levels', help='地图枚举文件路径（AllLevelList.lua）')
    parser.add_argument('--chinese', help='中文翻译文件路径（zh-Hans.lproj/Localizable.strings）')
    parser.add_argument('--english', help='原始翻译文件路径（Base.lproj/Localizable.strings）')
    
    args = parser.parse_args()
    
    # 如果未通过命令行参数提供，则提示用户输入
    table_path = Path(args.table) if args.table else None
    levels_path = Path(args.levels) if args.levels else None
    chinese_path = Path(args.chinese) if args.chinese else None
    english_path = Path(args.english) if args.english else None
    
    if not table_path:
        table_input = input("请输入Dump表路径（《光•遇》所有地图.md）: ").strip('"\'')
        table_path = Path(table_input)
    
    if not levels_path:
        levels_input = input("请输入地图枚举文件路径（AllLevelList.lua）: ").strip('"\'')
        levels_path = Path(levels_input)
    
    if not chinese_path:
        chinese_input = input("请输入中文翻译文件路径（zh-Hans.lproj/Localizable.strings）: ").strip('"\'')
        chinese_path = Path(chinese_input)
    
    if not english_path:
        english_input = input("请输入原始翻译文件路径（Base.lproj/Localizable.strings）: ").strip('"\'')
        english_path = Path(english_input)
    
    # 检查文件是否存在
    for path, name in [(table_path, "Dump表"), 
                       (levels_path, "地图枚举文件"),
                       (chinese_path, "中文翻译文件"),
                       (english_path, "原始翻译文件")]:
        if not path.exists():
            print(f"错误: {name}不存在: {path}")
            return
    
    print("正在读取文件...")
    
    # 1. 读取地图标识符
    identifiers = parse_level_list(levels_path)
    print(f"找到 {len(identifiers)} 个地图标识符")
    print(f"前10个标识符: {', '.join(identifiers[:10])}{'...' if len(identifiers) > 10 else ''}")
    
    # 2. 读取翻译文件
    chinese_translations = parse_strings_file(chinese_path)
    english_translations = parse_strings_file(english_path)
    
    print(f"中文翻译: {len(chinese_translations)} 条")
    print(f"英文翻译: {len(english_translations)} 条")
    
    # 测试一些翻译键
    test_keys = ['name_day', 'name_sk8', 'name_dawn', 'name_dusk']
    print("\n测试翻译键查找:")
    for key in test_keys:
        cn = chinese_translations.get(key, '未找到')
        en = english_translations.get(key, '未找到')
        print(f"  {key}: 中文='{cn}', 英文='{en}'")
    
    # 3. 读取现有表格
    headers, existing_data, non_table_content = read_existing_table(table_path)
    print(f"\n表格列头: {headers}")
    print(f"现有表格中有 {len(existing_data)} 条记录")
    
    # 4. 合并数据（不覆盖已有数据）
    print("正在合并表格数据...")
    merged_data = merge_table_data(identifiers, chinese_translations, english_translations, existing_data)
    
    # 5. 写入新表格
    write_table(table_path, headers, merged_data, non_table_content)
    
    print("完成！")

if __name__ == "__main__":
    main()