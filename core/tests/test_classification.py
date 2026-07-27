import pytest
from core.tools.classification import AUTO, CONFIRM, REVIEW, classify_command


def test_classify_safe_commands():
    assert classify_command("ls") == AUTO
    assert classify_command("ls -la") == AUTO
    assert classify_command("cat file.py") == AUTO
    assert classify_command("pwd") == AUTO
    assert classify_command("git status") == AUTO
    assert classify_command("git log") == AUTO
    assert classify_command("git diff") == AUTO
    assert classify_command("python --version") == AUTO
    assert classify_command("npm test") == AUTO
    assert classify_command("cargo test") == AUTO
    assert classify_command("pip list") == AUTO


def test_classify_destructive_commands():
    assert classify_command("rm -rf /") == REVIEW
    assert classify_command("git push --force") == REVIEW
    assert classify_command("git reset --hard") == REVIEW
    assert classify_command("sudo rm file") == REVIEW
    assert classify_command("git commit -m 'msg'") == CONFIRM
    assert classify_command("git merge branch") == REVIEW


def test_classify_confirm_commands():
    assert classify_command("pip install requests") == CONFIRM
    assert classify_command("npm install express") == CONFIRM
    assert classify_command("git add .") == CONFIRM
    assert classify_command("mkdir newdir") == CONFIRM
    assert classify_command("touch file.txt") == CONFIRM
    assert classify_command("cp file1 file2") == CONFIRM
    assert classify_command("python script.py") == CONFIRM


def test_classify_unknown_defaults_to_confirm():
    assert classify_command("some_unknown_command") == CONFIRM


def test_classify_empty_command():
    assert classify_command("") == CONFIRM


def test_classify_whitespace_handling():
    assert classify_command("  ls  ") == AUTO
    assert classify_command("  rm file  ") == REVIEW
