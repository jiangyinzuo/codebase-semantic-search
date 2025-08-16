def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run SQL to search codebase.")
    parser.add_argument("--dbname", type=str, default="", help="PGVector database name")
    parser.add_argument(
        "--query_text",
        "-q",
        type=str,
        default="",
        help="User query text to search in the codebase",
    )
    parser.add_argument(
        "--sql",
        type=str,
        default="""
    SELECT file_path
    FROM code_chunks
    ORDER BY embedding <-> %(embedding)s::vector
    LIMIT 10;
            """,
    )

    args = parser.parse_args()
    if len(args.dbname) > 0:
        from codebase.pgvector import CONFIG

        CONFIG["pgvector"]["dbname"] = args.dbname

    sql_params: dict = {}

    if "%(embedding)s" in args.sql:
        if len(args.query_text) == 0:
            print("ERROR: Query text must be provided when using embedding search.")
            parser.print_help()
            exit(1)
        print("Converting query text to embedding...", file=sys.stderr)
        from codebase.model_provider import EMBEDDING_MODEL

        user_query_embedding = EMBEDDING_MODEL.encode(args.query_text)
        sql_params["embedding"] = user_query_embedding

    from codebase.pgvector import PGVectorConnector

    pgvector_connector = PGVectorConnector()
    records = pgvector_connector.execute_select(args.sql, sql_params)

    for record in records:
        print(record[0])


if __name__ == "__main__":
    main()
