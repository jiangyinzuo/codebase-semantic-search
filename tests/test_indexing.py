import pytest
from unittest.mock import Mock
import tempfile
import os
from pathlib import Path


def test_git_changes_added_files(mocker):
    """测试检测新增文件"""
    from codebase.indexing import Indexer

    mock_run = mocker.patch("subprocess.run")

    # 模拟git diff输出：新增file1.py, file2.cpp
    mock_run.return_value.stdout = "A\tfile1.py\nA\tfile2.cpp"

    indexer = Indexer(None, {})
    added, modified, deleted = indexer.get_git_changes("abc123")

    assert added == ["file1.py", "file2.cpp"]
    assert modified == []
    assert deleted == []


def test_git_changes_mixed_changes(mocker):
    """测试混合变更"""
    from codebase.indexing import Indexer

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "A\tnew.py\nM\tmodified.py\nD\tdeleted.py"

    indexer = Indexer(None, {})
    added, modified, deleted = indexer.get_git_changes("abc123")

    assert added == ["new.py"]
    assert modified == ["modified.py"]
    assert deleted == ["deleted.py"]


def test_git_changes_no_changes(mocker):
    """测试无变更情况"""
    from codebase.indexing import Indexer

    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = ""

    indexer = Indexer(None, {})
    added, modified, deleted = indexer.get_git_changes("abc123")

    assert added == []
    assert modified == []
    assert deleted == []


def test_git_changes_same_commit(mocker):
    """测试相同commit返回空变更"""
    from codebase.indexing import Indexer

    mock_run = mocker.patch("subprocess.run")
    # 模拟当前commit和target commit相同
    mock_run.side_effect = [
        Mock(stdout="abc123\n"),  # 当前commit
        Mock(stdout="abc123\n"),  # target commit相同
    ]

    indexer = Indexer(None, {})
    added, modified, deleted = indexer.get_git_changes("abc123")

    assert added == []
    assert modified == []
    assert deleted == []


def test_git_changes_invalid_commit(mocker):
    """测试无效commit抛出异常"""
    import subprocess
    from codebase.indexing import Indexer

    mock_run = mocker.patch("subprocess.run")
    # 模拟git rev-parse失败
    def mock_side_effect(*args, **kwargs):
        if "rev-parse" in args[0] and args[0][-1] == "invalid":
            raise subprocess.CalledProcessError(1, "git rev-parse", "commit not found")
        elif "rev-parse" in args[0]:
            return Mock(stdout="abc123\n")
        return Mock(stdout="")
    
    mock_run.side_effect = mock_side_effect

    indexer = Indexer(None, {})
    with pytest.raises(ValueError, match="commit 'invalid' 不存在"):
        indexer.get_git_changes("invalid")


def test_load_codebase_ignore(tmp_path):
    """测试加载.codebaseignore文件"""
    from codebase.indexing import Indexer

    indexer = Indexer(None, {})

    # 创建临时.codebaseignore文件
    ignore_file = tmp_path / ".codebaseignore"
    ignore_file.write_text("# 注释行\n*.py\nbuild/\n# 另一个注释")

    # 切换到临时目录
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        patterns = indexer._load_codebase_ignore()
        assert patterns == ["*.py", "build/"]
    finally:
        os.chdir(original_cwd)


def test_load_codebase_ignore_not_exists(mocker):
    """测试.codebaseignore文件不存在时返回空列表"""
    from codebase.indexing import Indexer
    from pathlib import Path

    # Mock Path.exists to return False for .codebaseignore
    mocker.patch.object(Path, "exists", return_value=False)
    mocker.patch.object(Path, "is_file", return_value=False)
    
    indexer = Indexer(None, {})
    patterns = indexer._load_codebase_ignore()
    assert patterns == []


def test_should_ignore_file():
    """测试文件忽略逻辑"""
    from codebase.indexing import Indexer

    indexer = Indexer(None, {})

    # 测试匹配模式
    assert indexer._should_ignore_file("test.py", ["*.py"]) == True
    assert indexer._should_ignore_file("build/", ["build/", "*.py"]) == True
    assert indexer._should_ignore_file("src/build/", ["*/build/*", "*.py"]) == True

    # 测试不匹配模式
    assert indexer._should_ignore_file("test.cpp", ["*.py"]) == False
    assert indexer._should_ignore_file("src/main.py", ["test*"]) == False


def test_filter_ignored_files():
    """测试过滤被忽略的文件"""
    from codebase.indexing import Indexer

    indexer = Indexer(None, {})

    files = ["main.py", "utils.cpp", "test.py", "build/script.sh"]
    ignore_patterns = ["*.py", "build/*"]

    filtered = indexer._filter_ignored_files(files, ignore_patterns)
    assert filtered == ["utils.cpp"]
