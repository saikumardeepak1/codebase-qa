import { streamText, createUIMessageStream, createUIMessageStreamResponse } from "ai";
import { createAnthropic } from "@ai-sdk/anthropic";

// Claude Desktop sets ANTHROPIC_BASE_URL=https://api.anthropic.com (no /v1) in shell env.
// Explicitly set the correct base URL to avoid the SDK routing to the wrong endpoint.
const anthropic = createAnthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
  baseURL: "https://api.anthropic.com/v1",
});

const API_URL = process.env.API_URL || "http://localhost:8000";

const SYSTEM_PROMPT = `You are an expert staff engineer and codebase navigator.
You help developers understand codebases quickly and precisely.

## How you communicate

- Write like a senior engineer explaining to a smart colleague — direct,
  confident, no filler words
- Never start with "Based on the provided code chunks" or "Based on the
  documentation" — just answer directly
- Never say "Great question", "Certainly", "Of course", or any sycophantic opener
- Get to the point in the first sentence
- Use short paragraphs, never walls of text

## Citation rules
- Always cite using [1], [2], [3] referencing the chunk numbers
- Put citations inline right after the claim they support, not at the end
- If the answer is not in the provided chunks, say exactly:
  "This isn't covered in the indexed chunks. Try asking about [related thing]."

## Code formatting
- Show code snippets only when they add clarity — not by default
- Keep snippets short — show the relevant 3-5 lines, not the whole function`;

function buildUserPrompt(context: string, question: string): string {
  if (!context) {
    return `Question: ${question}\n\nNo relevant code was found for this question. Let the user know.`;
  }
  return `Here are relevant code chunks from the repository:\n\n${context}\n\n---\n\nQuestion: ${question}\n\nAnswer with citations [1], [2], etc.`;
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
        maxTokens: 2048,
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
