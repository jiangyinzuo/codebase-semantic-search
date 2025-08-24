import pytest
import tempfile
import subprocess
import os
from typing import override
from pathlib import Path
from unittest.mock import Mock
from codebase.indexing import Indexer
from codebase.pgvector import PGVectorConnector
from codebase.model_provider import ModelProvider


class MockModelProvider(ModelProvider):
    """Mock model provider for testing"""

    def __init__(self):
        self.embedding_dim = 1024

    @override
    def encode(self, text: str) -> list[float]:
        # Simple mock embedding based on text length
        return [float(len(text)) / 100.0] * self.embedding_dim

    @override
    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(text) for text in texts]


def create_test_git_repo():
    """Create a temporary git repository with sample files"""
    temp_dir = tempfile.mkdtemp()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=temp_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True
    )

    # Create initial files
    files = {
        "main.py": "def hello():\
    print('Hello, World!')\
",
        "utils.py": "def add(a, b):\
    return a + b\
",
        "README.md": "# Test Project\
This is a test project for integration testing.\
",
    }

    for filename, content in files.items():
        filepath = Path(temp_dir) / filename
        filepath.write_text(content)

    # Add and commit initial files
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True)

    return temp_dir


def get_test_db_config():
    """Get test database configuration"""
    return {
        "host": "127.0.0.1",
        "port": "5439",
        "dbname": "codebase_test",
        "user": "postgres",
        "password": "",
    }


@pytest.fixture
def test_git_repo():
    """Fixture to create a test git repository"""
    repo_path = create_test_git_repo()
    yield repo_path
    # Cleanup
    import shutil

    shutil.rmtree(repo_path)


@pytest.fixture
def test_db_connector():
    """Fixture to create test database connector"""
    db_config = get_test_db_config()
    connector = PGVectorConnector(db_config)

    # Clean up any existing test data
    try:
        connector.cur.execute("DELETE FROM code_chunks")
        connector.cur.execute(
            "UPDATE index_metadata SET last_commit_hash = NULL WHERE id = 1"
        )
        connector.conn.commit()
    except Exception:
        pass

    yield connector

    # Cleanup after test
    try:
        connector.cur.execute("DELETE FROM code_chunks")
        connector.cur.execute(
            "UPDATE index_metadata SET last_commit_hash = NULL WHERE id = 1"
        )
        connector.conn.commit()
    except Exception:
        pass
    connector.cur.close()
    connector.conn.close()


@pytest.fixture
def mock_model():
    """Fixture to create mock model"""
    return MockModelProvider()


@pytest.fixture
def mock_language_map():
    """Fixture to create mock language map"""
    try:
        import tree_sitter_python
        import tree_sitter_cpp
        from tree_sitter import Language
        
        CPP = Language(tree_sitter_cpp.language())
        return {
            ".py": Language(tree_sitter_python.language()),
            ".cpp": CPP,
            ".hpp": CPP,
        }
    except ImportError:
        pytest.skip("Tree-sitter language bindings not available")


def test_git_indexing_initial_commit(
    test_git_repo, test_db_connector, mock_model, mock_language_map
):
    """Test indexing initial git commit"""
    # Change to test repository directory
    original_cwd = os.getcwd()
    os.chdir(test_git_repo)

    try:
        # Create indexer and process git changes
        indexer = Indexer(mock_model, mock_language_map)
        indexer.process_git_changes(test_db_connector, "HEAD")

        # Verify data was inserted into database
        test_db_connector.cur.execute("SELECT COUNT(*) FROM code_chunks")
        count = test_db_connector.cur.fetchone()[0]

        # Should have indexed all git files (main.py, utils.py, README.md)
        assert count == 3  # main.py, utils.py, and README.md

        # Verify specific files were indexed
        test_db_connector.cur.execute(
            "SELECT file_path FROM code_chunks ORDER BY file_path"
        )
        files = [row[0] for row in test_db_connector.cur.fetchall()]
        assert "main.py" in files
        assert "utils.py" in files
        assert "README.md" in files  # All git files are indexed by default

        # Verify commit hash was stored
        test_db_connector.cur.execute(
            "SELECT last_commit_hash FROM index_metadata WHERE id = 1"
        )
        commit_hash = test_db_connector.cur.fetchone()[0]
        assert commit_hash is not None

    finally:
        os.chdir(original_cwd)


def test_git_indexing_incremental_changes(
    test_git_repo, test_db_connector, mock_model, mock_language_map
):
    """Test incremental indexing with git changes"""
    original_cwd = os.getcwd()
    os.chdir(test_git_repo)

    try:
        # Get initial commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        initial_commit = result.stdout.strip()

        # Index initial state using initial commit hash
        indexer = Indexer(mock_model, mock_language_map)
        indexer.process_git_changes(test_db_connector, initial_commit)

        # Make some changes
        # Add new file
        new_file = Path("new_module.py")
        new_file.write_text("def new_function():\n    return 'new'\n")

        # Modify existing file
        main_file = Path("main.py")
        main_content = main_file.read_text()
        main_file.write_text(main_content + "\n# New comment at the end\n")

        # Delete a file
        utils_file = Path("utils.py")
        utils_file.unlink()

        # Commit changes
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Test changes"], check=True)

        # Process incremental changes
        indexer.process_git_changes(test_db_connector, initial_commit)

        # Verify database state
        test_db_connector.cur.execute(
            "SELECT file_path FROM code_chunks ORDER BY file_path"
        )
        files = [row[0] for row in test_db_connector.cur.fetchall()]

        # Should have main.py (modified), new_module.py (added), README.md, but not utils.py (deleted)
        assert "main.py" in files
        assert "new_module.py" in files
        assert "README.md" in files
        assert "utils.py" not in files
        assert len(files) == 3  # main.py, new_module.py, README.md

    finally:
        os.chdir(original_cwd)


def test_git_indexing_with_codebaseignore(
    test_git_repo, test_db_connector, mock_model, mock_language_map
):
    """Test git indexing with .codebaseignore file"""
    original_cwd = os.getcwd()
    os.chdir(test_git_repo)

    try:
        # Create .codebaseignore file
        ignore_file = Path(".codebaseignore")
        ignore_file.write_text("*.py\n# Ignore all Python files\n")

        # Index with ignore rules
        indexer = Indexer(mock_model, mock_language_map)
        indexer.process_git_changes(test_db_connector, "HEAD")

        # Verify only non-Python files were indexed due to ignore rules
        test_db_connector.cur.execute("SELECT COUNT(*) FROM code_chunks")
        count = test_db_connector.cur.fetchone()[0]

        # Only README.md should be indexed (not Python files)
        assert count == 1  # Only README.md should be indexed
        
        # Verify README.md was indexed but Python files were not
        test_db_connector.cur.execute(
            "SELECT file_path FROM code_chunks ORDER BY file_path"
        )
        files = [row[0] for row in test_db_connector.cur.fetchall()]
        assert "README.md" in files  # Should be indexed (not a Python file)
        assert "main.py" not in files  # Should be ignored (Python file)
        assert "utils.py" not in files  # Should be ignored (Python file)

    finally:
        os.chdir(original_cwd)


def test_git_changes_detection(test_git_repo, mock_model, mock_language_map):
    """Test git changes detection functionality"""
    original_cwd = os.getcwd()
    os.chdir(test_git_repo)

    try:
        # Get initial commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        initial_commit = result.stdout.strip()

        # Make changes
        new_file = Path("test_file.py")
        new_file.write_text("# Test file\n")

        main_file = Path("main.py")
        main_content = main_file.read_text()
        main_file.write_text(main_content + "\n# Modified\n")

        utils_file = Path("utils.py")
        utils_file.unlink()

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Changes for testing"], check=True)

        # Test changes detection
        indexer = Indexer(mock_model, mock_language_map)
        added, modified, deleted = indexer.get_git_changes(initial_commit)

        # Verify changes detected correctly
        assert "test_file.py" in added
        assert "main.py" in modified
        assert "utils.py" in deleted

    finally:
        os.chdir(original_cwd)


def test_git_indexing_outside_repo(mock_model, mock_language_map):
    """Test that indexing fails outside git repository"""
    # Create temporary directory that's not a git repo
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            indexer = Indexer(mock_model, mock_language_map)
            with pytest.raises(ValueError, match="当前目录不是git仓库"):
                indexer.get_git_changes("HEAD")
        finally:
            os.chdir(original_cwd)


# Test database connectivity
@pytest.mark.skipif(
    not os.environ.get("TEST_WITH_DB"),
    reason="Database tests require TEST_WITH_DB environment variable",
)
def test_database_connectivity():
    """Test database connectivity (requires running PostgreSQL with pgvector)"""
    db_config = get_test_db_config()

    try:
        connector = PGVectorConnector(db_config)
        # Simple test query
        connector.cur.execute("SELECT 1")
        result = connector.cur.fetchone()
        assert result[0] == 1
        connector.cur.close()
        connector.conn.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")
