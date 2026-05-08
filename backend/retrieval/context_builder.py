import re
from typing import List, Dict, Any, Tuple
from models.schemas import Citation

# Strips _part2, _part3 etc. from split AST symbol names.
_PART_SUFFIX = re.compile(r"_part\d+$")


def _clean_symbol(symbol: str) -> str:
    return _PART_SUFFIX.sub("", symbol)


def build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
    # Text chunks carry prose explanation; show them before AST code chunks
    # so the LLM sees context → code in the same order it should answer.
    ordered = sorted(chunks, key=lambda c: (0 if c.get("chunk_strategy") == "text" else 1))

    context_parts = []
    citations: List[Citation] = []
    seen_files: set[str] = set()

    for i, chunk in enumerate(ordered, start=1):
        file_path = chunk.get("file_path", "unknown")
        raw_symbol = chunk.get("symbol_name", "")
        language = chunk.get("language", "text")
        start_line = chunk.get("start_line", 0)
        end_line = chunk.get("end_line", 0)
        content = chunk.get("content", "")
        strategy = chunk.get("chunk_strategy", "ast")

        if strategy == "text":
            context_parts.append(
                f"[{i}] {file_path} (lines {start_line}-{end_line}) [prose]\n"
                f"{content}"
            )
        else:
            symbol = _clean_symbol(raw_symbol)
            context_parts.append(
                f"[{i}] {file_path} — {symbol} (lines {start_line}-{end_line}) [code]\n"
                f"```{language}\n{content}\n```"
            )

        # Deduplicate citations: one card per unique file_path.
        # symbol_name is kept for the LLM context label but never shown in the UI.
        if file_path not in seen_files:
            seen_files.add(file_path)
            citations.append(Citation(
                index=i, file_path=file_path, symbol_name=_clean_symbol(raw_symbol),
                start_line=start_line, end_line=end_line, language=language,
                chunk_strategy=strategy,
            ))

    return "\n\n---\n\n".join(context_parts), citations
