import { useState, useEffect } from "react";
import { getRepoStatus } from "@/lib/api";

export interface IndexingState {
  status: string;
  progress: number;
  totalChunks: number;
  error: string | null;
  repoUrl: string;
}

export function useIndexingStatus(repoId: string | null): IndexingState {
  const [state, setState] = useState<IndexingState>({
    status: "pending",
    progress: 0,
    totalChunks: 0,
    error: null,
    repoUrl: "",
  });

  useEffect(() => {
    if (!repoId) return;
    if (state.status === "done" || state.status === "error") return;

    const interval = setInterval(async () => {
      try {
        const data = await getRepoStatus(repoId);
        setState({
          status: data.status,
          progress: data.progress,
          totalChunks: data.total_chunks,
          error: data.error ?? null,
          repoUrl: data.repo_url ?? "",
        });
        if (data.status === "done" || data.status === "error") {
          clearInterval(interval);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [repoId, state.status]);

  return state;
}
