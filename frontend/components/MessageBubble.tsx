"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Message } from "@/hooks/useChat";
import type { Citation } from "@/lib/api";
import { CitationCard } from "./CitationCard";
import { Copy, Check } from "lucide-react";

// Extract the plain text string from a v6 UIMessage parts array
function getMessageText(message: Message): string {
  return message.parts
    .filter((p) => p.type === "text")
    .map((p) => (p as { type: "text"; text: string }).text)
    .join("");
}

// A text part has state === 'streaming' while the model is generating
function isMessageStreaming(message: Message): boolean {
  return message.parts.some(
    (p) => p.type === "text" && "state" in p && (p as { state?: string }).state === "streaming",
  );
}

interface Props {
  message: Message;
  repoUrl: string;
}

function openCitation(citation: Citation, repoUrl: string) {
  if (!repoUrl) return;
  window.open(
    `${repoUrl}/blob/main/${citation.file_path}#L${citation.start_line}`,
    "_blank",
    "noopener,noreferrer",
  );
}

// Splits a raw string by [n] markers and returns React nodes.
// Called only on string children — never on React elements.
function renderContentWithCitations(
  content: string,
  citations: Citation[] | undefined,
  repoUrl: string,
  keyPrefix: string,
): React.ReactNode[] {
  const parts = content.split(/(\[\d+\])/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const citationIndex = parseInt(match[1]);
      const citation = citations?.find((c) => c.index === citationIndex);
      return (
        <sup
          key={`${keyPrefix}-${index}`}
          onClick={() => citation && openCitation(citation, repoUrl)}
          title={citation ? citation.file_path : ""}
          className="inline-flex items-center justify-center w-[18px] h-[18px] rounded text-[10px] font-mono cursor-pointer mx-0.5 align-super select-none transition-colors"
          style={{
            background: "#3a3a3a",
            color: "#d4a853",
            border: "1px solid #4a4a4a",
          }}
        >
          {citationIndex}
        </sup>
      );
    }
    return <span key={`${keyPrefix}-${index}`}>{part}</span>;
  });
}

// Walk React children: split string nodes by citation pattern, pass elements through.
function processChildren(
  children: React.ReactNode,
  citations: Citation[] | undefined,
  repoUrl: string,
  keyPrefix: string,
): React.ReactNode {
  return React.Children.map(children, (child, i) => {
    if (typeof child === "string") {
      const nodes = renderContentWithCitations(child, citations, repoUrl, `${keyPrefix}-${i}`);
      // If no citation markers found, return the string directly (no extra spans)
      return nodes.length === 1 && typeof nodes[0] !== "object"
        ? nodes[0]
        : nodes;
    }
    return child;
  });
}

function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-1 rounded text-xs font-mono opacity-0 group-hover:opacity-100 transition-opacity"
      style={{ background: "#333", color: "#9b9b9b" }}
    >
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function AssistantAvatar() {
  return (
    <div
      className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold mt-0.5"
      style={{ background: "#d4a853", color: "#1a1a1a" }}
    >
      AI
    </div>
  );
}

export function MessageBubble({ message, repoUrl }: Props) {
  const isUser = message.role === "user";

  const text = getMessageText(message);
  const streaming = isMessageStreaming(message);

  if (isUser) {
    return (
      <div className="msg-enter flex justify-end">
        <div
          className="max-w-[72%] px-4 py-3 rounded-2xl rounded-tr-sm text-base leading-relaxed"
          style={{ background: "#2a2a2a", color: "#ececec", border: "1px solid #3a3a3a" }}
        >
          {text}
        </div>
      </div>
    );
  }

  // Plain text while streaming — no markdown, no citation processing
  if (streaming) {
    return (
      <div className="msg-enter flex gap-3">
        <AssistantAvatar />
        <div className="flex-1 min-w-0 pt-0.5">
          <span
            className="streaming-cursor text-base leading-relaxed whitespace-pre-wrap"
            style={{ color: "#ececec" }}
          >
            {text || "\u00A0"}
          </span>
        </div>
      </div>
    );
  }

  // Full markdown + citation badges once streaming is complete
  return (
    <div className="msg-enter flex gap-3">
      <AssistantAvatar />
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="assistant-prose">
          <ReactMarkdown
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "");
                const isBlock = Boolean(match);
                const codeStr = String(children).replace(/\n$/, "");
                if (isBlock) {
                  return (
                    <div className="relative group my-3">
                      <CopyButton code={codeStr} />
                      <SyntaxHighlighter
                        style={oneDark as Record<string, React.CSSProperties>}
                        language={match![1]}
                        PreTag="div"
                        customStyle={{
                          margin: 0,
                          borderRadius: "8px",
                          fontSize: "13px",
                          background: "#111",
                          border: "1px solid #3a3a3a",
                          padding: "16px",
                        }}
                      >
                        {codeStr}
                      </SyntaxHighlighter>
                    </div>
                  );
                }
                return <code {...props}>{children}</code>;
              },
              // Walk each child: strings get citation-split, React elements pass through untouched
              p({ children }) {
                return (
                  <p>
                    {processChildren(children, message.metadata?.citations, repoUrl, "p")}
                  </p>
                );
              },
              li({ children }) {
                return (
                  <li>
                    {processChildren(children, message.metadata?.citations, repoUrl, "li")}
                  </li>
                );
              },
            }}
          >
            {text}
          </ReactMarkdown>
        </div>

        {message.metadata?.citations && message.metadata.citations.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {message.metadata.citations.map((citation) => (
              <CitationCard key={citation.index} citation={citation} repoUrl={repoUrl} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
