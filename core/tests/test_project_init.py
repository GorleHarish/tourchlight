import json
import shutil
import tempfile
from pathlib import Path
import pytest

from core.memory.persistence import ProjectMemory, ensure_project_initialized, init_new_project, ensure_git_repository


@pytest.fixture
def temp_project_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_ensure_project_initialized_creates_memory(temp_project_dir):
    assert not (temp_project_dir / ".git").exists()
    assert not (temp_project_dir / ".context-memory.json").exists()

    result_path = ensure_project_initialized(temp_project_dir)
    assert result_path == temp_project_dir.resolve()

    # Memory file created, skills folder created, git not forced by default
    assert (temp_project_dir / ".context-memory.json").exists()
    assert (temp_project_dir / ".agents" / "skills").is_dir()
    assert not (temp_project_dir / ".git").exists()


def test_ensure_git_repository_creates_git(temp_project_dir):
    assert not (temp_project_dir / ".git").exists()

    result_path = ensure_git_repository(temp_project_dir)
    assert result_path == temp_project_dir.resolve()
    assert (temp_project_dir / ".git").exists()


def test_init_new_project_creates_memory_and_git(temp_project_dir):
    assert not (temp_project_dir / ".git").exists()
    assert not (temp_project_dir / ".context-memory.json").exists()

    result_path = init_new_project(temp_project_dir)
    assert result_path == temp_project_dir.resolve()

    # Both memory file and git repo created for new project
    assert (temp_project_dir / ".context-memory.json").exists()
    assert (temp_project_dir / ".git").exists()


def test_project_memory_auto_init(temp_project_dir):
    assert not (temp_project_dir / ".git").exists()
    assert not (temp_project_dir / ".context-memory.json").exists()

    pm = ProjectMemory(temp_project_dir)
    assert pm.memory_file.exists()
    assert not (temp_project_dir / ".git").exists()

    # Load should return data and save updates
    data = pm.load()
    assert isinstance(data, dict)
    
    pm.update("Project created successfully")
    data_updated = pm.load()
    assert any("Project created successfully" in str(f) for f in data_updated.get("facts", []))


def test_idempotent_project_init(temp_project_dir):
    ensure_project_initialized(temp_project_dir)
    
    # Modify memory file content
    pm = ProjectMemory(temp_project_dir)
    pm.update("Custom memory fact")

    # Run ensure_project_initialized again
    ensure_project_initialized(temp_project_dir)

    # Custom memory fact should be preserved
    data = pm.load()
    assert any("Custom memory fact" in str(f) for f in data.get("facts", []))


def test_manual_deletion_context_memory_self_heals(temp_project_dir):
    pm = ProjectMemory(temp_project_dir)
    assert pm.memory_file.exists()
    
    # Manually delete .context-memory.json
    pm.memory_file.unlink()
    assert not pm.memory_file.exists()

    # Calling load() self-heals by recreating the file on disk
    data = pm.load()
    assert pm.memory_file.exists()
    assert isinstance(data, dict)

    # Delete again and call save()
    pm.memory_file.unlink()
    assert not pm.memory_file.exists()

    pm.save({"facts": ["re-saved fact"]})
    assert pm.memory_file.exists()
    reloaded = pm.load()
    assert "re-saved fact" in reloaded.get("facts", [])


def test_manual_deletion_git_repo_self_heals(temp_project_dir):
    ensure_git_repository(temp_project_dir)
    assert (temp_project_dir / ".git").exists()

    # Manually delete .git directory
    shutil.rmtree(temp_project_dir / ".git")
    assert not (temp_project_dir / ".git").exists()

    # ensure_git_repository self-heals by re-initializing git repo
    ensure_git_repository(temp_project_dir)
    assert (temp_project_dir / ".git").exists()


def test_corrupt_memory_file_self_heals(temp_project_dir):
    pm = ProjectMemory(temp_project_dir)
    assert pm.memory_file.exists()

    # Overwrite memory file with invalid truncated JSON
    with open(pm.memory_file, "w") as f:
        f.write("{invalid_json: truncated")

    # load() detects corrupted JSON and self-heals valid memory file on disk
    data = pm.load()
    assert isinstance(data, dict)
    assert pm.memory_file.exists()
    with open(pm.memory_file) as f:
        reloaded = json.load(f)
        assert isinstance(reloaded, dict)


def test_directory_memory_file_self_heals(temp_project_dir):
    # Manually create .context-memory.json as a directory
    bad_dir = temp_project_dir / ".context-memory.json"
    bad_dir.mkdir(parents=True, exist_ok=True)
    assert bad_dir.is_dir()

    # ensure_project_initialized removes directory and replaces with valid file
    ensure_project_initialized(temp_project_dir)
    assert (temp_project_dir / ".context-memory.json").is_file()


