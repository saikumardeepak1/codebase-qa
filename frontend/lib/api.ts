// Browser-side requests go through Next.js rewrite (/backend → http://127.0.0.1:8000)
// to avoid IPv6/CORS issues when localhost resolves to ::1 but uvicorn is IPv4-only.
const API_BASE = "/backend";

export interface Citation {
  index: number;
  file_path: string;
  symbol_name: string;
  start_line: number;
  end_line: number;
  language: string;
}

export async function indexRepo(githubUrl: string) {
  const res = await fetch(`${API_BASE}/repos/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ github_url: githubUrl }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ repo_id: string; status: string }>;
}

export async function getRepoStatus(repoId: string) {
  const res = await fetch(`${API_BASE}/repos/${repoId}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{
    status: string;
    progress: number;
    total_chunks: number;
    error?: string;
    repo_url: string;
  }>;
}

export async function streamChat(
  repoId: string,
  question: string,
  history: { role: string; content: string }[],
  onChunk: (text: string) => void,
  onCitations: (citations: Citation[]) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_id: repoId, question, history }),
  });

  if (!res.ok || !res.body) {
    onError(`HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are delimited by double newline — split on \n\n, not \n
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";  // last element may be an incomplete event

      for (const event of events) {
        const lines = event.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (!data || data === "[DONE]") continue;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "chunk") onChunk(parsed.content);
            if (parsed.type === "citations") onCitations(parsed.data);
            if (parsed.type === "done") onDone();
            if (parsed.type === "error") onError(parsed.message);
          } catch {}
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
