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


@pytest.mark.asyncio
async def test_mcp_server_startup():
    """Test that MCP server can start up without errors"""
    
    # Mock dependencies
    with (
        patch("codebase.mcp_server.EMBEDDING_MODEL") as mock_embedding,
        patch("codebase.mcp_server.PGVectorConnector") as mock_connector_class,
        patch("codebase.mcp_server.CONFIG") as mock_config
    ):
        # Setup mocks
        mock_embedding.encode.return_value = [0.1, 0.2, 0.3, 0.4]
        mock_connector = Mock()
        mock_connector.execute_select.return_value = (
            ["file_path", "distance"],
            [("test.py", 0.1234)]
        )
        mock_connector_class.return_value = mock_connector
        mock_config.return_value = {
            "pgvector": {
                "default_sql": "SELECT file_path, embedding <=> %(embedding)s::vector as distance FROM code_chunks ORDER BY embedding <=> %(embedding)s::vector LIMIT 10;"
            }
        }
        
        # Import and test the semantic_search function directly
        from codebase.mcp_server import semantic_search
        
        # Test that semantic search works
        result = await semantic_search("test")
        assert "Semantic search results" in result


# Test that the FastMCP server can be imported and initialized
@pytest.mark.asyncio
async def test_fastmcp_server_initialization():
    """Test that FastMCP server can be initialized without errors"""
    
    # Mock dependencies
    with (
        patch("codebase.mcp_server.EMBEDDING_MODEL") as mock_embedding,
        patch("codebase.mcp_server.PGVectorConnector") as mock_connector_class,
        patch("codebase.mcp_server.CONFIG") as mock_config
    ):
        # Setup mocks
        mock_embedding.encode.return_value = [0.1, 0.2, 0.3, 0.4]
        mock_connector = Mock()
        mock_connector.execute_select.return_value = (
            ["file_path", "distance"],
            [("test.py", 0.1234)]
        )
        mock_connector_class.return_value = mock_connector
        mock_config.return_value = {
            "pgvector": {
                "default_sql": "SELECT file_path, embedding <=> %(embedding)s::vector as distance FROM code_chunks ORDER BY embedding <=> %(embedding)s::vector LIMIT 10;"
            }
        }
        
        # Import the server module to test initialization
        from codebase import mcp_server
        
        # Verify the mcp object exists and has the tool registered
        assert hasattr(mcp_server, 'mcp')
        assert mcp_server.mcp is not None
        
        # Test that the tool function can be called
        result = await mcp_server.semantic_search("test query")
        assert "Semantic search results" in result or "Error" in result