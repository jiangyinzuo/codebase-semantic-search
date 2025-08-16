from tree_sitter import Language, Parser


def remove_header_junk(file_content: str, language: Language) -> str:
    """
    Chunk策略: 使用 Tree-sitter 移除文件开头的所有注释和 #include 语句。
    """
    parser = Parser(language)

    tree = parser.parse(bytes(file_content, "utf8"))
    root_node = tree.root_node

    first_code_node_start = None

    # 遍历根节点的所有子节点
    for node in root_node.children:
        # 跳过空行和空格节点
        if node.type in ["\n", " "]:
            continue

        # 寻找第一个非注释、非 #include 预处理、非import指令的节点
        if node.type not in ["comment", "preproc_include", "import_statement", "import_from_statement"]:
            first_code_node_start = node.start_byte
            break

    # 如果没有找到任何代码节点，则返回空字符串
    if first_code_node_start is None:
        return ""

    # 从第一个代码节点开始切片，去除前面的所有内容
    return file_content[first_code_node_start:].strip()


# --- 示例用法 ---
if __name__ == "__main__":
    code_with_headers = """
# hello
# world
import sys

import os
from pathlib import Path

print('xxx')
print('xxx')
"""

    import tree_sitter_python

    PY_LANGUAGE = Language(tree_sitter_python.language())
    cleaned_code = remove_header_junk(code_with_headers, PY_LANGUAGE)

    print("--- 原始代码 ---")
    print(code_with_headers)
    print("\n" + "=" * 20 + "\n")
    print("--- 清理后代码 ---")
    print(cleaned_code)
