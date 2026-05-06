"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { indexRepo } from "@/lib/api";
import { GitBranch, Loader2 } from "lucide-react";

export function RepoInput() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setError("");
    setLoading(true);
    try {
      const { repo_id } = await indexRepo(url.trim());
      const recent = getRecent();
      const entry = { repo_id, url: url.trim(), ts: Date.now() };
      localStorage.setItem(
        "recent_repos",
        JSON.stringify(
          [entry, ...recent.filter((r) => r.repo_id !== repo_id)].slice(0, 5),
        ),
      );
      router.push(`/chat/${repo_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start indexing");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3">
      <div
        className="flex items-center rounded-xl overflow-hidden"
        style={{ border: "1px solid #3a3a3a", background: "#2a2a2a" }}
      >
        <div className="pl-4 pr-2 shrink-0">
          <GitBranch className="w-4 h-4" style={{ color: "#9b9b9b" }} />
        </div>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 py-3.5 pr-2 text-base outline-none"
          style={{
            background: "transparent",
            color: "#ececec",
            fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
          }}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="shrink-0 flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: "#d4a853",
            color: "#1a1a1a",
          }}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : null}
          {loading ? "Starting…" : "Analyze Repository"}
        </button>
      </div>
      {error && (
        <p className="text-sm px-1" style={{ color: "#ef4444" }}>
          {error}
        </p>
      )}
    </form>
  );
}

export function getRecent(): { repo_id: string; url: string; ts: number }[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("recent_repos") || "[]");
  } catch {
    return [];
  }
}
