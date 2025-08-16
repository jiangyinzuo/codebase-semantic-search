from pathlib import Path
from codebase.pgvector import PGVectorConnector
from codebase.ts_chunk import remove_header_junk
from tree_sitter import Language
from codebase.model_provider import EMBEDDING_MODEL, ModelProvider


class Indexer:

    def __init__(self, model: ModelProvider, language_map: dict[str, Language]):
        self.model: ModelProvider = model
        self.language_map: dict[str, Language] = language_map

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

    def process_files(self, updater: PGVectorConnector, files_to_add: str, files_to_delete: str) -> None:
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


def main():
    import argparse
    import tree_sitter_python
    import tree_sitter_cpp

    parser = argparse.ArgumentParser(description="Update codebase index.")
    parser.add_argument("--dbname", type=str, default="", help="PGVector database name")
    parser.add_argument("--add", "-a", type=str, default="", help="Files to add")
    parser.add_argument("--delete", "-d", type=str, default="", help="Files to delete")

    args = parser.parse_args()
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
    indexer.process_files(updater, args.add, args.delete)


if __name__ == "__main__":
    main()
