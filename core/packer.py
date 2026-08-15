"""
Directory scanner and repository context packing engine.
"""

import sys
from pathlib import Path
from typing import Dict, Any

from config import IGNORE_DIRS, IGNORE_EXTS, MAX_FILE_SIZE_KB, ESTIMATED_CHARS_PER_TOKEN
from core.ast_parser import parse_python_ast


class CodebasePacker:
    """
    Recursively scans target directories, filters noise, 
    and packages code into a unified structure for LLM ingestion.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.max_file_size_bytes = MAX_FILE_SIZE_KB * 1024

    def is_ignored(self, path: Path) -> bool:
        """Determines if a path matches directory or extension blacklists."""
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        return path.suffix.lower() in IGNORE_EXTS

    def pack(self) -> Dict[str, Any]:
        """Scans and packages repository files into a payload dictionary."""
        packed_data: Dict[str, Any] = {
            "root": str(self.root_dir),
            "total_files": 0,
            "estimated_tokens": 0,
            "files": []
        }

        for file_path in self.root_dir.rglob("*"):
            if not file_path.is_file() or self.is_ignored(file_path):
                continue

            if file_path.stat().st_size > self.max_file_size_bytes:
                continue

            try:
                relative_path = str(file_path.relative_to(self.root_dir))
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Approximate token count based on string length
                token_estimate = len(content) // ESTIMATED_CHARS_PER_TOKEN
                packed_data["estimated_tokens"] += token_estimate

                # Extract AST summary if Python source
                ast_map = parse_python_ast(content) if file_path.suffix == ".py" else None

                packed_data["files"].append({
                    "path": relative_path,
                    "size_bytes": len(content),
                    "ast_map": ast_map,
                    "content": content
                })
                packed_data["total_files"] += 1
            except Exception as err:
                print(f"[!] Warning: Skipping file {file_path}: {err}", file=sys.stderr)

        return packed_data
