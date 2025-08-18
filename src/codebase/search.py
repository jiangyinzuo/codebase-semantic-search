from argparse import Namespace


def main(args: Namespace):
    import sys
    from tabulate import tabulate

    if len(args.dbname) > 0:
        from codebase.pgvector import CONFIG

        CONFIG["pgvector"]["dbname"] = args.dbname

    sql_params: dict = {}

    if "%(embedding)s" in args.sql:
        if len(args.query_text) == 0:
            print(
                "ERROR: Query text must be provided when using embedding search. See `codebase search -h`."
            )
            exit(1)
        print("Converting query text to embedding...", file=sys.stderr)
        from codebase.model_provider import EMBEDDING_MODEL

        user_query_embedding = EMBEDDING_MODEL.encode(args.query_text)
        sql_params["embedding"] = user_query_embedding

    from codebase.pgvector import PGVectorConnector

    pgvector_connector = PGVectorConnector()
    column_names, records = pgvector_connector.execute_select(args.sql, sql_params)
    print(
        tabulate(
            records,
            headers=column_names if column_names is not None else (),
            tablefmt="plain",
        )
    )
