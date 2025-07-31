"""Tests for Alembic database migrations."""

import subprocess
from pathlib import Path


def test_alembic_current_shows_migration():
    """Test that alembic current command works and shows the applied migration."""
    # Change to the project directory
    project_root = Path(__file__).parent.parent

    # Run alembic current command
    result = subprocess.run(
        ["alembic", "current"], cwd=project_root, capture_output=True, text=True
    )

    # Should succeed
    assert result.returncode == 0

    # Should show a migration ID (not empty)
    assert len(result.stdout.strip()) > 0
    assert "head" in result.stdout or len(result.stdout.strip().split()[0]) == 12


def test_alembic_history_shows_initial_migration():
    """Test that alembic history shows our initial migration."""
    # Change to the project directory
    project_root = Path(__file__).parent.parent

    # Run alembic history command
    result = subprocess.run(
        ["alembic", "history"], cwd=project_root, capture_output=True, text=True
    )

    # Should succeed
    assert result.returncode == 0

    # Should contain our initial migration
    assert "Initial schema setup" in result.stdout


def test_alembic_check_does_not_fail():
    """Test that alembic check command passes (no pending migrations)."""
    # Change to the project directory
    project_root = Path(__file__).parent.parent

    # Run alembic check command (this will fail if there are pending migrations)
    result = subprocess.run(
        ["alembic", "check"], cwd=project_root, capture_output=True, text=True
    )

    # Should succeed (return code 0 means no pending migrations)
    assert result.returncode == 0


def test_migration_files_exist():
    """Test that migration files were created in the expected location."""
    project_root = Path(__file__).parent.parent
    versions_dir = project_root / "alembic" / "versions"

    # Should exist
    assert versions_dir.exists()

    # Should contain at least one migration file
    migration_files = list(versions_dir.glob("*.py"))
    assert len(migration_files) > 0

    # At least one should contain "Initial schema setup"
    initial_migration_found = False
    for migration_file in migration_files:
        content = migration_file.read_text()
        if "Initial schema setup" in content:
            initial_migration_found = True
            break

    assert initial_migration_found, "Initial schema setup migration not found"
