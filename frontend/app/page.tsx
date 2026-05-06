"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RepoInput, getRecent } from "@/components/RepoInput";
import { Clock, ArrowRight } from "lucide-react";

interface RecentRepo {
  repo_id: string;
  url: string;
  ts: number;
}

export default function Home() {
  const [recent, setRecent] = useState<RecentRepo[]>([]);
  const router = useRouter();

  useEffect(() => {
    setRecent(getRecent());
  }, []);

  return (
    <main
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ background: "#1a1a1a" }}
    >
      <div className="w-full max-w-xl space-y-10">
        {/* Hero */}
        <div className="space-y-3 text-center">
          <div
            className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-2"
            style={{ background: "#d4a853" }}
          >
            <span className="text-lg font-bold" style={{ color: "#1a1a1a" }}>
              Q
            </span>
          </div>
          <h1
            className="text-3xl font-semibold tracking-tight"
            style={{ color: "#ececec" }}
          >
            Codebase Q&amp;A
          </h1>
          <p className="text-base" style={{ color: "#9b9b9b" }}>
            Ask questions about any public GitHub repository.
            <br />
            Get cited answers pointing to exact files and functions.
          </p>
        </div>

        {/* Input card */}
        <div
          className="rounded-2xl p-6 space-y-4"
          style={{ background: "#2a2a2a", border: "1px solid #3a3a3a" }}
        >
          <RepoInput />
          <p className="text-xs text-center" style={{ color: "#555" }}>
            Works with any public repository · Indexing takes 2–10 minutes
          </p>
        </div>

        {/* Recent repos */}
        {recent.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs px-1" style={{ color: "#555" }}>
              <Clock className="w-3 h-3" />
              <span>Recent</span>
            </div>
            <ul className="space-y-0.5">
              {recent.map((r) => (
                <li key={r.repo_id}>
                  <button
                    onClick={() => router.push(`/chat/${r.repo_id}`)}
                    className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors group text-left"
                    style={{ color: "#9b9b9b" }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background = "#2a2a2a";
                      (e.currentTarget as HTMLElement).style.color = "#ececec";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background = "transparent";
                      (e.currentTarget as HTMLElement).style.color = "#9b9b9b";
                    }}
                  >
                    <span className="text-sm font-mono truncate">
                      {r.url.replace("https://github.com/", "")}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 shrink-0 ml-2 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "#d4a853" }} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}
