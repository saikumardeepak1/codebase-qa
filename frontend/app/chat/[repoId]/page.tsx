"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getRepoStatus } from "@/lib/api";
import { IndexingStatus } from "@/components/IndexingStatus";
import { ChatWindow } from "@/components/ChatWindow";
import { Loader2 } from "lucide-react";

export default function ChatPage() {
  const { repoId } = useParams<{ repoId: string }>();
  const router = useRouter();

  const [phase, setPhase] = useState<"loading" | "indexing" | "ready">("loading");
  const [repoUrl, setRepoUrl] = useState("");

  useEffect(() => {
    if (!repoId) return;
    getRepoStatus(repoId)
      .then((data) => {
        setRepoUrl(data.repo_url ?? "");
        if (data.status === "done") {
          setPhase("ready");
        } else if (data.status === "error") {
          router.push("/");
        } else {
          setPhase("indexing");
        }
      })
      .catch(() => router.push("/"));
  }, [repoId, router]);

  const handleComplete = useCallback(() => {
    getRepoStatus(repoId)
      .then((data) => {
        setRepoUrl(data.repo_url ?? "");
        setPhase("ready");
      })
      .catch(() => setPhase("ready"));
  }, [repoId]);

  if (phase === "loading") {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-zinc-500 animate-spin" />
      </div>
    );
  }

  if (phase === "indexing") {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center px-4 gap-6">
        <div className="text-center space-y-1">
          <h2 className="text-white font-medium text-sm">Indexing repository</h2>
          <p className="text-zinc-500 text-xs">This takes 2–10 minutes depending on repo size</p>
        </div>
        <div className="w-full max-w-md">
          <IndexingStatus repoId={repoId} onComplete={handleComplete} />
        </div>
      </div>
    );
  }

  return <ChatWindow repoId={repoId} repoUrl={repoUrl} />;
}
