"""
AST-based code chunker using tree-sitter.
Each function, class, and method becomes its own chunk.
This is what separates this project from naive RAG tutorials.
"""

from pathlib import Path
from typing import List, Optional
from tree_sitter import Language, Parser
from models.schemas import CodeChunk
import tiktoken

def _load_language(name: str) -> Optional[Language]:
    try:
        if name == "python":
            import tree_sitter_python as m
        elif name in ("typescript", "tsx"):
            import tree_sitter_typescript as m
            if name == "tsx":
                return Language(m.language_tsx())
            return Language(m.language_typescript())
        elif name in ("javascript", "jsx"):
            import tree_sitter_javascript as m
        elif name == "go":
            import tree_sitter_go as m
        elif name == "rust":
            import tree_sitter_rust as m
        elif name == "java":
            import tree_sitter_java as m
        elif name == "cpp":
            import tree_sitter_cpp as m
        elif name == "c":
            import tree_sitter_c as m
        elif name == "c_sharp":
            import tree_sitter_c_sharp as m
        elif name == "ruby":
            import tree_sitter_ruby as m
        elif name == "php":
            import tree_sitter_php as m
            return Language(m.language_php())
        elif name == "swift":
            import tree_sitter_swift as m
        elif name == "kotlin":
            import tree_sitter_kotlin as m
        else:
            return None
        return Language(m.language())
    except Exception:
        return None


def _get_parser(language_name: str) -> Optional[Parser]:
    lang = _load_language(language_name)
    if lang is None:
        return None
    return Parser(lang)


LANGUAGE_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx",
    ".js": "javascript", ".jsx": "javascript", ".go": "go",
    ".rs": "rust", ".java": "java", ".cpp": "cpp", ".c": "c",
    ".h": "c", ".hpp": "cpp", ".cs": "c_sharp", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".kt": "kotlin",
}

FUNCTION_NODE_TYPES = {
    "python": ["function_definition", "async_function_definition", "class_definition"],
    "typescript": ["function_declaration", "method_definition", "class_declaration"],
    "tsx": ["function_declaration", "method_definition", "class_declaration"],
    "javascript": ["function_declaration", "method_definition", "class_declaration"],
    "jsx": ["function_declaration", "method_definition", "class_declaration"],
    "go": ["function_declaration", "method_declaration", "type_declaration"],
    "rust": ["function_item", "impl_item", "struct_item", "enum_item"],
    "java": ["method_declaration", "class_declaration", "constructor_declaration"],
    "cpp": ["function_definition", "class_specifier"],
    "c": ["function_definition"],
    "c_sharp": ["method_declaration", "class_declaration", "constructor_declaration"],
    "ruby": ["method", "class", "singleton_method"],
    "swift": ["function_declaration", "class_declaration", "struct_declaration"],
    "kotlin": ["function_declaration", "class_declaration", "object_declaration"],
}

MAX_CHUNK_TOKENS = 512
ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def get_node_name(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return "unknown"


def split_large_chunk(content: str, max_tokens: int = MAX_CHUNK_TOKENS) -> List[str]:
    lines = content.split("\n")
    chunks, current, current_tokens = [], [], 0
    for line in lines:
        line_tokens = count_tokens(line)
        if current_tokens + line_tokens > max_tokens and current:
            chunks.append("\n".join(current))
            current = current[-10:]
            current_tokens = count_tokens("\n".join(current))
        current.append(line)
        current_tokens += line_tokens
    if current:
        chunks.append("\n".join(current))
    return chunks


def chunk_code_file(file_path: Path, repo_root: Path, repo_id: str) -> List[CodeChunk]:
    suffix = file_path.suffix.lower()
    language_name = LANGUAGE_MAP.get(suffix)
    if not language_name:
        return []

    parser = _get_parser(language_name)
    if parser is None:
        return []

    try:
        source = file_path.read_bytes()
        relative_path = str(file_path.relative_to(repo_root))
        tree = parser.parse(source)
        node_types = FUNCTION_NODE_TYPES.get(language_name, [])
        chunks: List[CodeChunk] = []

        def walk(node):
            if node.type in node_types:
                content = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                symbol_name = get_node_name(node, source)
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1

                if count_tokens(content) > MAX_CHUNK_TOKENS:
                    for i, sub in enumerate(split_large_chunk(content)):
                        chunks.append(CodeChunk(
                            repo_id=repo_id, file_path=relative_path,
                            language=language_name, chunk_type=node.type,
                            symbol_name=f"{symbol_name}_part{i+1}",
                            start_line=start_line, end_line=end_line, content=sub
                        ))
                else:
                    chunks.append(CodeChunk(
                        repo_id=repo_id, file_path=relative_path,
                        language=language_name, chunk_type=node.type,
                        symbol_name=symbol_name, start_line=start_line,
                        end_line=end_line, content=content
                    ))
                return  # don't recurse into matched nodes

            for child in node.children:
                walk(child)

        walk(tree.root_node)

        if not chunks:
            content = source.decode("utf-8", errors="replace")
            chunks = chunk_text_file(content, relative_path, repo_id, language_name)

        return chunks
    except Exception as e:
        print(f"[chunker] Failed to parse {file_path}: {e}")
        return []


def chunk_text_file(content: str, relative_path: str, repo_id: str, language: str = "text") -> List[CodeChunk]:
    lines = content.split("\n")
    chunks, current_lines, current_tokens, chunk_index = [], [], 0, 0

    for line in lines:
        line_tokens = count_tokens(line)
        is_heading = line.startswith("## ") or line.startswith("# ")
        over_limit = current_tokens + line_tokens > MAX_CHUNK_TOKENS

        if (is_heading or over_limit) and current_lines:
            chunks.append(CodeChunk(
                repo_id=repo_id, file_path=relative_path, language=language,
                chunk_type="text", symbol_name=f"chunk_{chunk_index}",
                start_line=0, end_line=0, content="\n".join(current_lines)
            ))
            chunk_index += 1
            current_lines, current_tokens = [], 0

        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunks.append(CodeChunk(
            repo_id=repo_id, file_path=relative_path, language=language,
            chunk_type="text", symbol_name=f"chunk_{chunk_index}",
            start_line=0, end_line=0, content="\n".join(current_lines)
        ))

    return chunks


def chunk_file(file_path: Path, repo_root: Path, repo_id: str) -> List[CodeChunk]:
    suffix = file_path.suffix.lower()
    if suffix in LANGUAGE_MAP:
        return chunk_code_file(file_path, repo_root, repo_id)
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        relative_path = str(file_path.relative_to(repo_root))
        return chunk_text_file(content, relative_path, repo_id, suffix.lstrip(".") or "text")
    except Exception:
        return []
