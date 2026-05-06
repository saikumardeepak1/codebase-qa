"use client";

import { useEffect } from "react";
import { useIndexingStatus } from "@/hooks/useIndexingStatus";
import { CheckCircle, XCircle } from "lucide-react";

const STEPS = ["cloning", "chunking", "embedding", "storing", "done"];
const STEP_LABELS: Record<string, string> = {
  pending:   "Queued",
  cloning:   "Cloning repository",
  chunking:  "Parsing & chunking code",
  embedding: "Generating embeddings",
  storing:   "Storing in vector DB",
  done:      "Ready",
  error:     "Failed",
};

interface Props {
  repoId: string;
  onComplete: () => void;
}

export function IndexingStatus({ repoId, onComplete }: Props) {
  const { status, progress, totalChunks, error } = useIndexingStatus(repoId);

  useEffect(() => {
    if (status === "done") onComplete();
  }, [status, onComplete]);

  const isDone = status === "done";
  const isError = status === "error";
  const currentStep = STEPS.indexOf(status);

  return (
    <div className="w-full max-w-md mx-auto space-y-5">
      {/* Step label */}
      <div className="flex items-center gap-2.5">
        {isError ? (
          <XCircle className="w-4 h-4 shrink-0" style={{ color: "#ef4444" }} />
        ) : isDone ? (
          <CheckCircle className="w-4 h-4 shrink-0" style={{ color: "#d4a853" }} />
        ) : (
          <div
            className="w-4 h-4 rounded-full shrink-0 border-2 border-t-transparent animate-spin"
            style={{ borderColor: "#d4a853", borderTopColor: "transparent" }}
          />
        )}
        <span className="text-sm font-medium" style={{ color: "#ececec" }}>
          {STEP_LABELS[status] ?? status}
        </span>
        {!isDone && !isError && (
          <span className="text-sm" style={{ color: "#9b9b9b" }}>
            — {progress}%
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ background: "#2a2a2a", height: "3px" }}
      >
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${isDone ? 100 : progress}%`,
            background: isError ? "#ef4444" : "#d4a853",
          }}
        />
      </div>

      {/* Steps row */}
      <div className="flex justify-between">
        {STEPS.filter((s) => s !== "done").map((step, i) => {
          const past = currentStep > i;
          const active = currentStep === i;
          return (
            <span
              key={step}
              className="text-xs"
              style={{
                color: active ? "#d4a853" : past ? "#9b9b9b" : "#555",
                fontWeight: active ? 500 : 400,
              }}
            >
              {STEP_LABELS[step].split(" ")[0]}
            </span>
          );
        })}
      </div>

      {/* Chunk count */}
      {totalChunks > 0 && (
        <p className="text-sm" style={{ color: "#9b9b9b" }}>
          {isDone ? "✓ " : ""}{totalChunks.toLocaleString()} chunks indexed
        </p>
      )}

      {/* Error */}
      {error && (
        <div
          className="text-sm rounded-lg px-4 py-3"
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "#ef4444",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
