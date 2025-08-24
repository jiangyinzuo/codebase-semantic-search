from pathlib import Path
from codebase.pgvector import PGVectorConnector
from codebase.ts_chunk import remove_header_junk
from tree_sitter import Language
from codebase.model_provider import EMBEDDING_MODEL, ModelProvider
from argparse import Namespace
import subprocess
import os


class Indexer:

    def __init__(self, model: ModelProvider, language_map: dict[str, Language]):
        self.model: ModelProvider = model
        self.language_map: dict[str, Language] = language_map

    def get_git_changes(
        self, target_commit: str = "HEAD"
    ) -> tuple[list[str], list[str], list[str]]:
        """
        检测自target_commit以来的git变更
        返回: (added_files, modified_files, deleted_files)
        """
        # 检查是否在git仓库中
        try:
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                check=True,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ValueError("当前目录不是git仓库")

        # 获取当前commit hash
        current_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()

        # 如果target_commit是HEAD或与当前相同，返回空变更
        if target_commit == "HEAD" or target_commit == current_commit:
            return [], [], []

        # 检查target_commit是否存在
        try:
            subprocess.run(
                ["git", "rev-parse", target_commit], capture_output=True, check=True
            )
        except subprocess.CalledProcessError:
            raise ValueError(f"commit '{target_commit}' 不存在")

        # 使用git diff检测变更
        result = subprocess.run(
            ["git", "diff", "--name-status", f"{target_commit}..HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        added, modified, deleted = [], [], []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status, file_path = parts[0], parts[1]
            if status == "A":  # Added
                added.append(file_path)
            elif status == "M":  # Modified
                modified.append(file_path)
            elif status == "D":  # Deleted
                deleted.append(file_path)

        return added, modified, deleted

    def _load_codebase_ignore(self) -> list[str]:
        """加载.codebaseignore文件中的忽略规则"""
        ignore_patterns = []
        codebase_ignore_path = Path(".codebaseignore")

        if codebase_ignore_path.exists() and codebase_ignore_path.is_file():
            with open(codebase_ignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore_patterns.append(line)

        return ignore_patterns

    def _should_ignore_file(self, file_path: str, ignore_patterns: list[str]) -> bool:
        """检查文件是否应该被忽略"""
        from fnmatch import fnmatch

        for pattern in ignore_patterns:
            if fnmatch(file_path, pattern):
                return True
        return False

    def _filter_ignored_files(
        self, file_list: list[str], ignore_patterns: list[str]
    ) -> list[str]:
        """过滤掉被忽略的文件"""
        return [
            f for f in file_list if not self._should_ignore_file(f, ignore_patterns)
        ]

    def _get_all_git_files(self) -> list[str]:
        """获取git仓库中的所有文件"""
        import subprocess

        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []

    def process_git_changes(
        self, updater: PGVectorConnector, target_commit: str = "HEAD"
    ) -> None:
        """处理git变更，包括.codebaseignore过滤"""
        # 检查是否是首次索引（没有上次commit记录）
        last_commit_hash = updater.get_last_commit_hash()

        # 获取git变更
        if last_commit_hash is None:
            # 首次索引，获取所有文件
            added = self._get_all_git_files()
            modified, deleted = [], []
            print("首次索引: 索引所有git文件")
        else:
            # 增量索引，获取变更
            added, modified, deleted = self.get_git_changes(target_commit)

        # 加载忽略规则
        ignore_patterns = self._load_codebase_ignore()

        # 过滤被忽略的文件
        added = self._filter_ignored_files(added, ignore_patterns)
        modified = self._filter_ignored_files(modified, ignore_patterns)
        deleted = self._filter_ignored_files(deleted, ignore_patterns)

        print(
            f"Git变更检测: 新增 {len(added)} 个文件, 修改 {len(modified)} 个文件, 删除 {len(deleted)} 个文件"
        )

        # 处理新增和修改的文件
        for file_path in added + modified:
            p = Path(file_path)
            if p.exists() and p.is_file():
                file_embedding = self._file_to_embedding(
                    p, self.language_map.get(p.suffix)
                )
                if file_embedding is None:
                    continue
                embedding, code_text = file_embedding
                updater.append_file_chunk(str(p), code_text, embedding)

        # 处理删除的文件
        for file_path in deleted:
            updater.append_files_to_remove(file_path)

        updater.flush()

        # 如果是首次索引，更新commit hash
        if last_commit_hash is None:
            import subprocess

            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            updater.update_last_commit_hash(current_commit)

    def _file_to_embedding(
        self, file_path: Path, language: Language | None
    ) -> tuple[list[float], str] | None:
        """
        Convert a file to an embedding using the SentenceTransformer model.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            if language is not None:
                content = remove_header_junk(content, language)
            if content.strip() == "":
                return None

        # Generate the embedding
        embedding: list[float] = self.model.encode(content)

        return embedding, content

    def process_files(
        self, updater: PGVectorConnector, files_to_add: str, files_to_delete: str
    ) -> None:
        files_to_add_list: list[str] = files_to_add.split()
        for file_path in files_to_add_list:
            p = Path(file_path.strip())
            if p.exists() and p.is_file():
                file_embedding = self._file_to_embedding(
                    p, self.language_map.get(p.suffix)
                )
                if file_embedding is None:
                    continue
                embedding, code_text = file_embedding
                updater.append_file_chunk(str(p), code_text, embedding)

        files_to_delete_list: list[str] = files_to_delete.split()
        for file_path in files_to_delete_list:
            p = Path(file_path.strip())
            if p.is_file():
                updater.append_files_to_remove(str(p))
        updater.flush()


def main(args: Namespace):
    import tree_sitter_python
    import tree_sitter_cpp

    # 检查参数互斥性
    if hasattr(args, "git") and args.git is not None:
        if args.add or args.delete:
            raise ValueError("--git 参数不能与 --add/--delete 同时使用")
    elif not args.add and not args.delete:
        raise ValueError("必须指定 --add/--delete 或 --git 参数")

    if len(args.dbname) > 0:
        from pgvector import CONFIG

        CONFIG["pgvector"]["dbname"] = args.dbname

    CPP = Language(tree_sitter_cpp.language())
    language_map = {
        ".py": Language(tree_sitter_python.language()),
        ".cpp": CPP,
        ".hpp": CPP,
    }
    updater = PGVectorConnector()
    indexer = Indexer(EMBEDDING_MODEL, language_map)

    if hasattr(args, "git") and args.git is not None:
        indexer.process_git_changes(updater, args.git)
        # 更新最后一次索引的commit hash
        import subprocess

        current_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        updater.update_last_commit_hash(current_commit)
    else:
        indexer.process_files(updater, args.add, args.delete)
