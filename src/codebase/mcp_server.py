from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
import numpy as np

from codebase.config import CONFIG
from codebase.model_provider import EMBEDDING_MODEL
from codebase.pgvector import PGVectorConnector

# Create FastMCP server
mcp = FastMCP("codebase-semantic-search")


@mcp.tool()
async def semantic_search(query: str) -> str:
    """Perform semantic search on the codebase using the default SQL query.
    
    Args:
        query: The search query text
        
    Returns:
        Formatted search results with file paths and similarity distances
    """
    if not query:
        return "Error: Query parameter is required"

    try:
        # Convert query text to embedding
        query_embedding = EMBEDDING_MODEL.encode(query)

        # Use default SQL from config
        default_sql = CONFIG["pgvector"].get(
            "default_sql",
            """
SELECT file_path, embedding <=> %(embedding)s::vector as distance
FROM code_chunks
ORDER BY embedding <=> %(embedding)s::vector
LIMIT 10;
            """,
        )

        # Execute search
        pgvector_connector = PGVectorConnector()
        sql_params = {"embedding": query_embedding}
        column_names, records = pgvector_connector.execute_select(
            default_sql, sql_params
        )

        # Format results
        if not records:
            return "No results found"

        result_text = "Semantic search results:\n\n"
        for i, record in enumerate(records, 1):
            result_text += f"{i}. {record[0]} (distance: {record[1]:.4f})\n"

        return result_text

    except Exception as e:
        return f"Error during semantic search: {str(e)}"


def main():
    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
