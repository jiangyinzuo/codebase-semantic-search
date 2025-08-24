import pytest
import subprocess
import os
from unittest.mock import Mock
from codebase.indexing import Indexer


@pytest.fixture
def mock_indexer():
    """创建带有mock model的Indexer实例"""
    mock_model = Mock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]  # 简单的mock embedding
    return Indexer(mock_model, {})


@pytest.fixture
def mock_git_repo(mocker):
    """模拟git仓库环境"""
    # 模拟git rev-parse成功
    mocker.patch('subprocess.run', side_effect=lambda *args, **kwargs: 
        Mock(stdout="abc123\n") if "rev-parse" in args[0] else Mock(stdout="")
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up test database before running integration tests"""
    # Only run if TEST_WITH_DB environment variable is set
    if not os.environ.get("TEST_WITH_DB"):
        return
    
    try:
        # Check if test database exists and create if not
        result = subprocess.run([
            "psql", "-h", "127.0.0.1", "-p", "5439", "-U", "postgres", 
            "-d", "codebase_test", "-c", "SELECT 1"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Test database doesn't exist, create it
            print("Creating test database 'codebase_test'...")
            subprocess.run([
                "createdb", "-h", "127.0.0.1", "-p", "5439", "-U", "postgres", 
                "codebase_test"
            ], check=True)
            
            # Create tables with pgvector extension
            subprocess.run([
                "psql", "-h", "127.0.0.1", "-p", "5439", "-U", "postgres", 
                "-d", "codebase_test", "-f", "create_tables.sql", "-v", "dim=1024"
            ], check=True)
            print("Test database 'codebase_test' created successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to setup test database: {e}")
        pytest.skip("Test database setup failed")
    except FileNotFoundError:
        print("PostgreSQL commands not found, skipping database tests")
        pytest.skip("PostgreSQL not available")