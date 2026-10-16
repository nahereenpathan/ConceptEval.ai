"""
Language Runtimes, Compilers, and Template Specifications
Provides centralized detection and configuration for Python, Java, and C++.
"""

import os
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional


class LanguageDetector:
    """Detects and reports available compiler/runtime environments on the system."""

    @classmethod
    def get_python_info(cls) -> Dict[str, Any]:
        """Detect local Python runtime."""
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return {
            "id": "python",
            "name": "Python 3.12",
            "monaco_lang": "python",
            "file_extension": ".py",
            "executable": sys.executable,
            "version": version_str,
            "is_available": True,
            "compiler": None,
            "requires_compilation": False,
        }

    @classmethod
    def get_java_info(cls) -> Dict[str, Any]:
        """Detect JDK compiler (javac) and JRE (java)."""
        javac_bin = shutil.which("javac")
        java_bin = shutil.which("java")
        available = bool(javac_bin and java_bin)
        version_str = "Unavailable"

        if available:
            try:
                res = subprocess.run(
                    [javac_bin, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
                output = (res.stdout or "") + (res.stderr or "")
                m = re.search(r"javac\s+([\d._]+)", output)
                if m:
                    version_str = f"JDK {m.group(1)}"
                else:
                    version_str = output.strip().splitlines()[0] if output.strip() else "JDK (Installed)"
            except Exception:
                version_str = "JDK (Installed)"

        return {
            "id": "java",
            "name": "Java (JDK 25 / OpenJDK)",
            "monaco_lang": "java",
            "file_extension": ".java",
            "executable": java_bin,
            "compiler": javac_bin,
            "version": version_str,
            "is_available": available,
            "requires_compilation": True,
        }

    @classmethod
    def get_cpp_info(cls) -> Dict[str, Any]:
        """Detect C++ compiler (g++ or clang++)."""
        gpp_bin = shutil.which("g++") or shutil.which("clang++")
        available = bool(gpp_bin)
        version_str = "Unavailable"

        if available:
            try:
                res = subprocess.run(
                    [gpp_bin, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                    check=False,
                )
                output = (res.stdout or "") + (res.stderr or "")
                first_line = output.strip().splitlines()[0] if output.strip() else "g++ (Installed)"
                version_str = first_line
            except Exception:
                version_str = "g++ (Installed)"

        return {
            "id": "cpp",
            "name": "C++ (g++ C++17)",
            "monaco_lang": "cpp",
            "file_extension": ".cpp",
            "executable": None,
            "compiler": gpp_bin,
            "version": version_str,
            "is_available": available,
            "requires_compilation": True,
        }

    @classmethod
    def get_all_languages(cls) -> List[Dict[str, Any]]:
        """Return full list of supported languages and their live status."""
        return [
            cls.get_python_info(),
            cls.get_java_info(),
            cls.get_cpp_info(),
        ]

    @classmethod
    def get_language_spec(cls, language_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve specification for a normalized language identifier."""
        norm_id = language_id.lower().strip()
        if norm_id in ("c++", "cpp"):
            norm_id = "cpp"
        for lang in cls.get_all_languages():
            if lang["id"] == norm_id:
                return lang
        return None


def extract_java_class_name(source_code: str) -> str:
    """Extract public class name or fallback to Solution."""
    match = re.search(r"public\s+class\s+([A-Za-z0-9_]+)", source_code)
    if match:
        return match.group(1)
    match_class = re.search(r"class\s+([A-Za-z0-9_]+)", source_code)
    if match_class:
        return match_class.group(1)
    return "Solution"


def get_default_starter_template(language: str, problem_title: str = "") -> str:
    """Generate professional starter-code templates for Python, Java, and C++."""
    norm_lang = language.lower().strip()
    if norm_lang in ("c++", "cpp"):
        norm_lang = "cpp"

    clean_title = problem_title or "Problem Solution"

    if norm_lang == "java":
        return (
            "import java.util.*;\n"
            "import java.io.*;\n\n"
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        Scanner scanner = new Scanner(System.in);\n"
            "        // TODO: Read input from standard input\n"
            "        if (!scanner.hasNext()) return;\n"
            "        \n"
            "        // Implement your solution logic here\n"
            "    }\n"
            "}\n"
        )
    elif norm_lang == "cpp":
        return (
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include <string>\n"
            "#include <algorithm>\n\n"
            "using namespace std;\n\n"
            "int main() {\n"
            "    ios_base::sync_with_stdio(false);\n"
            "    cin.tie(NULL);\n\n"
            "    // TODO: Read input from standard input\n"
            "    // Implement your solution logic here\n\n"
            "    return 0;\n"
            "}\n"
        )
    else:  # python
        return (
            "import sys\n\n"
            "def solve():\n"
            "    input_data = sys.stdin.read().strip()\n"
            "    if not input_data:\n"
            "        return\n"
            "    # TODO: Implement your solution logic here\n\n"
            "if __name__ == '__main__':\n"
            "    solve()\n"
        )
