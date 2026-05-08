import os
import sys

IGNORE = {
    '.git', '__pycache__', '.venv', 'venv', 'env', '.env',
    'node_modules', '.idea', '.vscode', '.mypy_cache', '.ruff_cache',
    '.pytest_cache', 'dist', 'build', 'site-packages', '.uv',
}
IGNORE_EXT = {'.pyc', '.pyo', '.pyd', '.egg-info'}

def print_tree(root, prefix=""):
    try:
        entries = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return

    entries = [
        e for e in entries
        if e.name not in IGNORE
        and not any(e.name.endswith(x) for x in IGNORE_EXT)
    ]

    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        icon = "📁 " if entry.is_dir() else "📄 "
        print(f"{prefix}{connector}{icon}{entry.name}")
        if entry.is_dir():
            print_tree(entry.path, prefix + ("    " if is_last else "│   "))

if __name__ == "__main__":
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(f"📦 {os.path.basename(root)}/")
    print_tree(root)