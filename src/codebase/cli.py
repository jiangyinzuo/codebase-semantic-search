def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run SQL to search codebase.")
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    index_parser = subparsers.add_parser("index", help="Index codebase files")
    index_parser.add_argument(
        "--dbname", type=str, default="", help="PGVector database name"
    )
    index_parser.add_argument("--add", "-a", type=str, default="", help="Files to add")
    index_parser.add_argument(
        "--delete", "-d", type=str, default="", help="Files to delete"
    )

    config_parser = subparsers.add_parser("config", help="Show configuration")

    search_parser = subparsers.add_parser("search", help="Search the codebase")
    search_parser.add_argument(
        "--dbname", type=str, default="", help="PGVector database name"
    )
    search_parser.add_argument(
        "--query_text",
        "-q",
        type=str,
        default="",
        help="User query text to search in the codebase",
    )
    search_parser.add_argument(
        "--sql",
        type=str,
        default="""
SELECT file_path, embedding <=> %(embedding)s::vector AS distance
FROM code_chunks
ORDER BY embedding <=> %(embedding)s::vector
LIMIT 10;
            """,
    )

    args = parser.parse_args()
    match args.command:
        case "index":
            from codebase.indexing import main as index_main

            index_main(args)
        case "config":
            from codebase.config import CONFIG
            import json

            print(json.dumps(CONFIG, indent=2))
        case "search":
            from codebase.search import main as search_main

            search_main(args)
        case _:
            parser.print_help()
            exit(1)


if __name__ == "__main__":
    main()
