import anthropic, json
from langfuse import Langfuse
from config import get_settings
from llm.prompts import SYSTEM_PROMPT, build_user_prompt
from models.schemas import Citation
from typing import List, AsyncGenerator, Dict, Any

settings = get_settings()
anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


async def stream_answer(
    question: str,
    context: str,
    citations: List[Citation],
    repo_id: str,
    history: List[Dict[str, str]] = []
) -> AsyncGenerator[str, None]:
    trace = langfuse.trace(
        name="rag_query",
        input={"question": question, "repo_id": repo_id},
        metadata={"num_citations": len(citations)}
    )

    user_prompt = build_user_prompt(context, question)
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-6:]]
    messages.append({"role": "user", "content": user_prompt})

    span = trace.span(name="llm_call", input={"messages": messages})
    full_response = ""

    try:
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"

        yield f"data: {json.dumps({'type': 'citations', 'data': [c.model_dump() for c in citations]})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

        span.end(output={"response": full_response})
        trace.update(output={"answer": full_response})
    except Exception as e:
        span.end(output={"error": str(e)}, level="ERROR")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        langfuse.flush()
