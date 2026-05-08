import { streamText, createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { createAnthropic } from "@ai-sdk/anthropic";

// Claude Desktop sets ANTHROPIC_BASE_URL=https://api.anthropic.com (no /v1) in shell env.
// Explicitly set the correct base URL to avoid the SDK routing to the wrong endpoint.
const anthropic = createAnthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
  baseURL: "https://api.anthropic.com/v1",
});

const API_URL = process.env.API_URL || "http://localhost:8000";

const SYSTEM_PROMPT = `You are a senior engineer who knows this codebase deeply.
Answer every question as if you wrote this code yourself.

## Forbidden phrases — never say these, ever:
- "indexed chunks", "chunks don't contain", "based on what's in the index"
- "cannot be inferred from chunks", "the provided chunks", "the retrieved chunks"
- "based on the context", "based on the provided code"
- "Great question", "Certainly", "Of course", "I'd be happy to"

## How you communicate
- Get to the point in the first sentence — lead with the answer, not a preamble
- Write like a senior engineer explaining to a smart colleague: "In this codebase...",
  "Looking at the code...", "This project uses..."
- Short paragraphs, never walls of text

## For every technical answer — mandatory format:
1. One-sentence direct answer
2. The most relevant code snippet in a fenced code block with language tag:
   \`\`\`python
   # the relevant code
   \`\`\`
   Always add the file path and line range on a line ABOVE the code block, like:
   \`backend/ingestion/chunker.py (lines 45–67)\`
3. Plain-English explanation of what the code does
4. If the symbol appears in multiple files: "Defined in X, used in Y and Z" [1][2]

## Citation rules
- Cite using [1], [2], [3] — inline, right after the claim they support
- If multiple chunks say the same thing, cite only the most specific one
- Use exact names from the codebase, never vague descriptions

## Architecture questions
- Lead directly with the answer — never say "this isn't covered" or apologize
- Use the file paths and chunk types visible in the context to describe the architecture confidently

## When the question has no good match in the context
- Do NOT show hardcoded topic suggestions
- Look at the file_paths in the retrieved context to understand what this repo covers
- Suggest 2–3 specific questions the user could actually ask, inferred from real
  file names and content you can see, e.g.:
  "This codebase covers ingestion pipelines, vector search, and REST endpoints —
  try asking how the embedding step works or what the chunking strategy is"

## Code formatting
- Show snippets when they add clarity — always show at least one for technical questions
- Keep snippets to the most relevant 5–15 lines — never dump an entire function verbatim
- Always include the function signature when referencing a function`;

function buildUserPrompt(context: string, question: string): string {
  if (!context) {
    return `Question: ${question}\n\nNo matching code was found. Look at what you know about the repo from the conversation and suggest 2-3 specific related questions the user could ask, based on the actual file names and content you've seen. Do not use generic suggestions.`;
  }
  return `Here are relevant code chunks from the repository.
Chunks tagged [prose] are from docs/config; chunks tagged [code] are from parsed source files.

${context}

---

Question: ${question}

Answer with inline citations [1], [2], etc. For every technical answer, show the relevant code snippet with the file path and line range above it.`;
}

function getTextFromParts(parts: Array<{ type: string; text?: string }> | undefined): string {
  if (!parts) return "";
  return parts
    .filter((p) => p.type === "text" && p.text)
    .map((p) => p.text!)
    .join("");
}

export async function POST(req: Request) {
  const body = await req.json();
  const { messages, repoId } = body;

  if (!messages?.length || !repoId) {
    return new Response("Missing messages or repoId", { status: 400 });
  }

  const lastMessage = messages[messages.length - 1];
  const question = getTextFromParts(lastMessage.parts) || lastMessage.content || "";
  const history = messages.slice(0, -1).map((m: { role: string; parts?: Array<{ type: string; text?: string }>; content?: string }) => ({
    role: m.role as "user" | "assistant",
    content: getTextFromParts(m.parts) || m.content || "",
  }));

  const stream = createUIMessageStream({
    execute: async ({ writer }) => {
      // 1. Retrieve context + citations from FastAPI (pure retrieval, no LLM)
      const retrieveRes = await fetch(`${API_URL}/retrieve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_id: repoId, question, history }),
      });

      if (!retrieveRes.ok) {
        writer.write({ type: "error", errorText: "Retrieval failed" });
        return;
      }

      const { context, citations } = await retrieveRes.json();

      // 2. Call Claude with streamText
      const result = streamText({
        model: anthropic("claude-sonnet-4-6"),
        maxOutputTokens: 2048,
        system: SYSTEM_PROMPT,
        messages: [
          ...history,
          { role: "user", content: buildUserPrompt(context, question) },
        ],
      });

      // 3. Pipe text chunks to the UI message stream
      for await (const chunk of result.toUIMessageStream()) {
        writer.write(chunk);
      }

      // 4. Append citations as message metadata — readable via message.metadata.citations
      writer.write({
        type: "message-metadata",
        messageMetadata: { citations },
      });
    },
  });

  return createUIMessageStreamResponse({ stream });
}
