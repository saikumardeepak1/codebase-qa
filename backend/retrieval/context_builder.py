from typing import List, Dict, Any, Tuple
from models.schemas import Citation


def build_context(chunks: List[Dict[str, Any]]) -> Tuple[str, List[Citation]]:
    # Text chunks carry prose explanation; show them before AST code chunks
    # so the LLM sees context → code in the same order it should answer.
    ordered = sorted(chunks, key=lambda c: (0 if c.get("chunk_strategy") == "text" else 1))

    context_parts = []
    citations = []

    for i, chunk in enumerate(ordered, start=1):
        file_path = chunk.get("file_path", "unknown")
        symbol = chunk.get("symbol_name", "unknown")
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
            context_parts.append(
                f"[{i}] {file_path} — {symbol} (lines {start_line}-{end_line}) [code]\n"
                f"```{language}\n{content}\n```"
            )

        citations.append(Citation(
            index=i, file_path=file_path, symbol_name=symbol,
            start_line=start_line, end_line=end_line, language=language,
            chunk_strategy=strategy,
        ))

    return "\n\n---\n\n".join(context_parts), citations
