import pytest
import asyncio
from unittest.mock import Mock, patch


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model that returns a simple vector"""
    mock_model = Mock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3, 0.4]  # Simple 4D vector
    return mock_model


@pytest.fixture
def mock_pgvector_connector():
    """Mock PGVector connector"""
    mock_connector = Mock()
    mock_connector.execute_select.return_value = (
        ["file_path", "distance"],
        [
            ("src/codebase/cli.py", 0.1234),
            ("src/codebase/search.py", 0.2345),
            ("src/codebase/config.py", 0.3456),
        ],
    )
    return mock_connector


@pytest.fixture
def mock_config():
    """Mock configuration"""
    return {
        "pgvector": {
            "default_sql": "SELECT file_path, embedding <=> %(embedding)s::vector as distance FROM code_chunks ORDER BY embedding <=> %(embedding)s::vector LIMIT 10;"
        }
    }


@pytest.fixture
def mcp_server_instance(mock_embedding_model, mock_pgvector_connector, mock_config):
    """Create MCP server instance with mocked dependencies"""
    with (
        patch("codebase.mcp_server.EMBEDDING_MODEL", mock_embedding_model),
        patch("codebase.mcp_server.PGVectorConnector") as mock_connector_class,
        patch("codebase.mcp_server.CONFIG", mock_config),
    ):

        mock_connector_class.return_value = mock_pgvector_connector

        from codebase.mcp_server import semantic_search

        yield semantic_search


@pytest.mark.asyncio
async def test_semantic_search_success(
    mcp_server_instance, mock_embedding_model, mock_pgvector_connector
):
    """Test successful semantic search execution"""
    query = "test search query"

    # Test the semantic_search function directly
    result = await mcp_server_instance(query)

    # Verify embedding model was called
    mock_embedding_model.encode.assert_called_once_with("test search query")

    # Verify database query was executed
    mock_pgvector_connector.execute_select.assert_called_once()

    # Verify results
    assert isinstance(result, str)
    assert "Semantic search results" in result
    assert "src/codebase/cli.py" in result
    assert "src/codebase/search.py" in result


@pytest.mark.asyncio
async def test_semantic_search_empty_query(mcp_server_instance):
    """Test semantic search with empty query"""
    query = ""

    result = await mcp_server_instance(query)

    assert "Error" in result
    assert "Query parameter is required" in result


@pytest.mark.asyncio
async def test_semantic_search_no_results(mcp_server_instance, mock_pgvector_connector):
    """Test semantic search when no results are found"""
    # Mock empty results
    mock_pgvector_connector.execute_select.return_value = ([], [])

    query = "test query"

    result = await mcp_server_instance(query)

    assert "No results found" in result


@pytest.mark.asyncio
async def test_semantic_search_database_error(
    mcp_server_instance, mock_pgvector_connector
):
    """Test semantic search when database operation fails"""
    # Mock database error
    mock_pgvector_connector.execute_select.side_effect = Exception(
        "Database connection failed"
    )

    query = "test query"

    result = await mcp_server_instance(query)

    assert "Error during semantic search" in result
    assert "Database connection failed" in result


# Note: Full MCP server integration testing requires complex setup
# with stdio streams and proper MCP protocol handling. The unit tests
# above cover the core semantic_search functionality which is the most
# important part for integration testing.
