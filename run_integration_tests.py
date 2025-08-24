"""
Integration test runner for codebase-semantic-search

This script runs integration tests that require a real PostgreSQL database with pgvector.
Before running, make sure you have:
1. PostgreSQL with pgvector running on localhost:5439
2. The script will automatically create 'codebase_test' database if needed
3. Tables will be created using create_tables.sql

Usage:
    # Run all integration tests (requires database)
    TEST_WITH_DB=1 python run_integration_tests.py

    # Run only unit tests (no database required)
    python run_integration_tests.py --unit-only
"""

import os
import subprocess
import sys
import argparse

# Database configuration constants
DB_HOST = "127.0.0.1"
DB_PORT = "5439"
DB_USER = "postgres"
DB_NAME = "codebase_test"
DB_PASSWORD = ""
EMBEDDING_DIM = "1024"

# Test configuration
TEST_INDEXING_FILE = "tests/test_indexing.py"
TEST_GIT_INTEGRATION_FILE = "tests/test_git_integration.py"


def check_database_connection():
    """Check if test database is available"""
    try:
        result = subprocess.run(
            [
                "psql",
                "-h",
                DB_HOST,
                "-p",
                DB_PORT,
                "-U",
                DB_USER,
                "-d",
                DB_NAME,
                "-c",
                "SELECT 1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ):
        return False


def run_tests(with_db=False, unit_only=False):
    """Run the appropriate test suite"""

    if unit_only:
        # Run only unit tests (no database required)
        print("Running unit tests only...")
        return subprocess.run(["pytest", "tests/test_indexing.py", "-v"]).returncode

    if with_db:
        # delete DB if it exists
        subprocess.run(
            [
                "dropdb",
                "-h",
                DB_HOST,
                "-p",
                DB_PORT,
                "-U",
                DB_USER,
                "--if-exists",
                DB_NAME,
            ]
        )
        # createdb
        subprocess.run(
            [
                "createdb",
                "-h",
                DB_HOST,
                "-p",
                DB_PORT,
                "-U",
                DB_USER,
                DB_NAME,
            ]
        )

        # Create tables
        subprocess.run(
            [
                "psql",
                "-h",
                DB_HOST,
                "-p",
                DB_PORT,
                "-U",
                DB_USER,
                "-d",
                DB_NAME,
                "-f",
                "create_tables.sql",
                "-v",
                f"dim={EMBEDDING_DIM}",
            ],
            check=True,
        )

        # Check if database is available
        if not check_database_connection():
            print("Error: Database not available!")
            print(
                f"Please make sure PostgreSQL with pgvector is running on {DB_HOST}:{DB_PORT}"
            )
            print(
                f"The script will automatically create '{DB_NAME}' database if needed."
            )
            return 1

        # Run integration tests with database
        print("Running integration tests with database...")
        env = os.environ.copy()
        env["TEST_WITH_DB"] = "1"
        return subprocess.run(
            ["pytest", "tests/test_git_integration.py", "-v"], env=env
        ).returncode
    else:
        # Run integration tests without database (they will be skipped)
        print("Running integration tests (database tests will be skipped)...")
        return subprocess.run(
            ["pytest", "tests/test_git_integration.py", "-v"]
        ).returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run integration tests for codebase-semantic-search"
    )
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument(
        "--with-db", action="store_true", help="Run integration tests with database"
    )

    args = parser.parse_args()

    if args.unit_only and args.with_db:
        print("Error: Cannot specify both --unit-only and --with-db")
        return 1

    return run_tests(with_db=args.with_db, unit_only=args.unit_only)


if __name__ == "__main__":
    sys.exit(main())
