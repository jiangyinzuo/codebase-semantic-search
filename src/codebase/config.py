import os
from pathlib import Path
from jsonc_parser.parser import JsoncParser
from collections.abc import MutableMapping


def recursive_merge(target_dict, source_dict):
    """
    递归地将 source_dict 合并到 target_dict 中。

    :param target_dict: 目标字典，将被修改。
    :param source_dict: 源字典，其内容将被合并到 target_dict 中。
    :return: 合并后的目标字典。
    """
    for key, value in source_dict.items():
        # 如果目标字典中存在该键，并且两个值都是字典
        if (
            key in target_dict
            and isinstance(target_dict[key], MutableMapping)
            and isinstance(value, MutableMapping)
        ):
            # 递归合并子字典
            recursive_merge(target_dict[key], value)
        else:
            # 否则，直接覆盖或添加键值对
            target_dict[key] = value
    return target_dict


def get_xdg_config_path(app_name: str, config_file: str) -> Path:
    """
    根据 XDG 规范获取配置文件的完整路径。
    :param app_name: 你的应用程序名称。
    :param config_file: 配置文件的名称，如 'config.json'。
    :return: 配置文件的完整路径，如果无法获取则返回 None。
    """
    # 1. 优先使用 XDG_CONFIG_HOME 环境变量
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        config_dir = Path(xdg_config_home) / app_name
    else:
        # 2. 如果环境变量未设置，使用默认路径 ~/.config
        config_dir = Path.home() / ".config" / app_name

    # 3. 拼接完整的配置文件路径
    config_path = config_dir / config_file

    return config_path


CONFIG = {
    "pgvector": {
        "dbname": "codebase_indexing",
        "user": "postgres",
        "host": "127.0.0.1",
        "port": "5432",
    },
    # openai | sentence_transformer
    "model_provider": "openai",
    "openai": {"url": "http://localhost:8000"},
    # the last '/' matters
    "model": "/home/jiangyinzuo/Qwen3-Embedding-0.6B/",
}

# merge global jsonc config
xdg_config_path = get_xdg_config_path("codebase", "config.jsonc")
if xdg_config_path.exists():
    try:
        # 直接加载 JSONC 文件
        global_jsonc_config: dict = JsoncParser.parse_file(xdg_config_path)
        recursive_merge(CONFIG, global_jsonc_config)
    except Exception as e:
        print(f"加载 JSONC 失败: {e}")

