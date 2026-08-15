#!/usr/bin/env python3
"""
GLM-5.3 Cyber-Engine Desktop Auditor Client
An automated codebase security scanner that packs local repositories, parses AST structures,
and streams prompts to an LLM endpoint for deep security vulnerability detection and patch generation.
"""

import os
import sys
import ast
import json
import urllib.request
import urllib.error
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Default configurations
DEFAULT_MODEL = "glm-4"  # Default active endpoint model name
DEFAULT_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
IGNORE_DIRS: Set[str] = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", 
    "dist", "build", ".idea", ".vscode", "coverage", ".pytest_cache"
}
IGNORE_EXTS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", 
    ".zip", ".tar", ".gz", ".7z", ".exe", ".dll", ".so", ".dylib", ".pyc", ".bin"
}


class ASTMapExtractor(ast.NodeVisitor):
    """Parses Python source code to extract high-level structure (classes and functions)."""
    
    def __init__(self):
        self.structure: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Record class definitions and recurse into methods."""
        self.structure.append(f"Class: {node.name} (Line {node.lineno})")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Record standard function definitions."""
        self.structure.append(f"Function: {node.name}() (Line {node.lineno})")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Record asynchronous function definitions."""
        self.structure.append(f"Async Function: {node.name}() (Line {node.lineno})")
        self.generic_visit(node)


class CodebasePacker:
    """Traverses a local repository, filters non-code files, builds AST maps, and serializes context."""

    def __init__(self, root_dir: Path, max_file_size_kb: int = 500):
        self.root_dir = root_dir.resolve()
        self.max_file_size_bytes = max_file_size_kb * 1024

    def should_ignore(self, path: Path) -> bool:
        """Checks if a file or directory should be ignored during inspection."""
        for part in path.parts:
            if part in IGNORE_DIRS:
                return True
        if path.suffix.lower() in IGNORE_EXTS:
            return True
        return False

    def extract_ast_summary(self, content: str) -> Optional[List[str]]:
        """Safely generates an AST structural map for Python files."""
        try:
            tree = ast.parse(content)
            visitor = ASTMapExtractor()
            visitor.visit(tree)
            return visitor.structure
        except Exception:
            # Non-python files or invalid syntax returns None
            return None

    def pack_repository(self) -> Dict[str, Any]:
        """Scans the repository and bundles all source code into a structured dictionary."""
        packed_data: Dict[str, Any] = {
            "root": str(self.root_dir),
            "total_files": 0,
            "estimated_tokens": 0,
            "files": []
        }

        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file() and not self.should_ignore(file_path):
                if file_path.stat().st_size > self.max_file_size_bytes:
                    continue

                try:
                    relative_path = str(file_path.relative_to(self.root_dir))
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # Estimate token count (rough rule of thumb: ~4 chars per token)
                    token_estimate = len(content) // 4
                    packed_data["estimated_tokens"] += token_estimate

                    ast_map = self.extract_ast_summary(content) if file_path.suffix == ".py" else None

                    packed_data["files"].append({
                        "path": relative_path,
                        "size_bytes": len(content),
                        "ast_map": ast_map,
                        "content": content
                    })
                    packed_data["total_files"] += 1
                except Exception as e:
                    print(f"[!] Skipping {file_path}: {e}", file=sys.stderr)

        return packed_data


class GLMAuditorEngine:
    """Interacts with the GLM/Z.AI API endpoint to conduct zero-day and logic audit analysis."""

    def __init__(self, api_key: Optional[str] = None, endpoint_url: str = DEFAULT_API_URL):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY", "")
        self.endpoint_url = endpoint_url

    def build_system_prompt(self) -> str:
        """Constructs the cybersecurity auditing persona instructions."""
        return (
            "You are GLM-5.3 Cyber-Engine, an elite offensive security auditor and code reviewer.\n"
            "Analyze the provided codebase context for business logic flaws, cryptographic weaknesses, "
            "RCE/injection vectors, memory leaks, and authentication bypasses.\n\n"
            "Provide output in strict Markdown formatting using the following structure for each finding:\n"
            "### [SEVERITY: Critical/High/Medium/Low] <Title>\n"
            "- **Target File**: <path>\n"
            "- **Vulnerability Type**: <cwe_type>\n"
            "- **Description**: <detailed explanation of attack vector>\n"
            "- **Exploit Scenario**: <step-by-step impact breakdown>\n"
            "- **Suggested Git Patch**: \n```diff\n<exact patch diff>\n```\n"
        )

    def analyze(self, packed_codebase: Dict[str, Any], model: str = DEFAULT_MODEL) -> str:
        """Packs codebase context into an LLM payload and sends the HTTP POST request."""
        # Build prompt payload
        prompt_content = [f"Repository Root: {packed_codebase['root']}"]
        prompt_content.append(f"Total Files Analyzed: {packed_codebase['total_files']}\n")
        
        for file_info in packed_codebase["files"]:
            prompt_content.append(f"--- FILE: {file_info['path']} ---")
            if file_info["ast_map"]:
                prompt_content.append(f"AST Structure: {', '.join(file_info['ast_map'])}")
            prompt_content.append(f"```\n{file_info['content']}\n```\n")

        full_user_prompt = "\n".join(prompt_content)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.build_system_prompt()},
                {"role": "user", "content": full_user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.endpoint_url, data=data, headers=headers, method="POST")

        try:
            print("[*] Transmitting codebase to GLM-5.3 Cyber-Engine endpoint...")
            with urllib.request.urlopen(request) as response:
                response_body = response.read().decode("utf-8")
                result_json = json.loads(response_body)
                return result_json["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8")
            return f"Error from API Endpoint (HTTP {e.code}): {error_msg}"
        except Exception as e:
            return f"Network or execution failure: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="GLM-5.3 Desktop Auditor CLI Client")
    parser.add_argument("repo_path", type=str, help="Path to the repository folder to audit")
    parser.add_argument("--output", "-o", type=str, default="audit_report.md", help="Output markdown report filename")
    parser.add_argument("--model", "-m", type=str, default=DEFAULT_MODEL, help="Model target (default: glm-4)")
    parser.add_argument("--api-key", "-k", type=str, help="Z.AI API Key (or set ZHIPU_API_KEY env var)")

    args = parser.parse_args()
    target_dir = Path(args.repo_path)

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"[!] Error: Directory '{args.repo_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Scanning codebase at: {target_dir.resolve()}")
    packer = CodebasePacker(target_dir)
    packed_code = packer.pack_repository()

    print(f"[+] Repository packed successfully.")
    print(f"    - Files included: {packed_code['total_files']}")
    print(f"    - Estimated context tokens: ~{packed_code['estimated_tokens']}")

    if packed_code["total_files"] == 0:
        print("[!] No readable source files found.")
        sys.exit(0)

    engine = GLMAuditorEngine(api_key=args.api_key)
    report = engine.analyze(packed_code, model=args.model)

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(f"[+] Audit complete! Report generated at: {output_path.resolve()}")


if __name__ == "__main__":
    main()
