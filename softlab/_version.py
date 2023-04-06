from pathlib import Path

def get_version() -> str:
    """Get package version"""
    return Path(Path(__file__).parent, 'VERSION.txt').read_text().rstrip()
