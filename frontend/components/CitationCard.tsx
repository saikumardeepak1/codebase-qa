"use client";

import { Citation } from "@/lib/api";

interface Props {
  citation: Citation;
  repoUrl: string;
}

export function CitationCard({ citation, repoUrl }: Props) {
  const href = repoUrl
    ? `${repoUrl}/blob/main/${citation.file_path}#L${citation.start_line}`
    : "#";

  const fileName = citation.file_path.split("/").pop() ?? citation.file_path;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono transition-colors"
      style={{
        background: "#2a2a2a",
        border: "1px solid #3a3a3a",
        color: "#9b9b9b",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.background = "#333";
        (e.currentTarget as HTMLElement).style.borderColor = "#4a4a4a";
        (e.currentTarget as HTMLElement).style.color = "#ececec";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.background = "#2a2a2a";
        (e.currentTarget as HTMLElement).style.borderColor = "#3a3a3a";
        (e.currentTarget as HTMLElement).style.color = "#9b9b9b";
      }}
    >
      <span style={{ color: "#d4a853" }}>[{citation.index}]</span>
      <span>{fileName}</span>
      <span style={{ color: "#555" }}>·</span>
      <span className="truncate max-w-[140px]">{citation.symbol_name}</span>
    </a>
  );
}
