"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { Send, Loader2 } from "lucide-react";

interface Props {
  repoId: string;
  repoUrl: string;
}

export function ChatWindow({ repoId, repoUrl }: Props) {
  const { messages, isLoading, sendMessage } = useChat(repoId);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q || isLoading) return;
    setInput("");
    sendMessage({ text: q });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  const repoName = repoUrl ? repoUrl.replace("https://github.com/", "") : repoId;

  return (
    <div className="flex flex-col h-screen" style={{ background: "#1a1a1a" }}>
      {/* Header */}
      <header
        className="shrink-0 px-6 py-3 flex items-center gap-3"
        style={{ borderBottom: "1px solid #2a2a2a" }}
      >
        <div className="flex flex-col">
          <span className="text-xs" style={{ color: "#9b9b9b" }}>
            Chatting with
          </span>
          <a
            href={repoUrl || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-mono transition-colors"
            style={{ color: "#ececec" }}
            onMouseEnter={(e) => ((e.target as HTMLElement).style.color = "#d4a853")}
            onMouseLeave={(e) => ((e.target as HTMLElement).style.color = "#ececec")}
          >
            {repoName}
          </a>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-8 px-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <p className="text-base" style={{ color: "#9b9b9b" }}>
              Ask anything about this codebase
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                "How does dependency injection work?",
                "What does the main entry point do?",
                "How is authentication handled?",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage({ text: s })}
                  className="text-sm px-4 py-2 rounded-full transition-colors"
                  style={{
                    border: "1px solid #3a3a3a",
                    color: "#9b9b9b",
                    background: "transparent",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = "#4a4a4a";
                    (e.currentTarget as HTMLElement).style.color = "#ececec";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = "#3a3a3a";
                    (e.currentTarget as HTMLElement).style.color = "#9b9b9b";
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="max-w-[720px] mx-auto w-full space-y-8">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} repoUrl={repoUrl} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        className="shrink-0 px-4 py-4"
        style={{ borderTop: "1px solid #2a2a2a" }}
      >
        <form
          onSubmit={handleSubmit}
          className="max-w-[720px] mx-auto flex items-end gap-0 rounded-xl overflow-hidden"
          style={{ border: "1px solid #3a3a3a", background: "#2a2a2a" }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? "Waiting for response…" : "Ask a question…"}
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none px-4 py-3.5 text-base outline-none disabled:opacity-50"
            style={{
              background: "transparent",
              color: "#ececec",
              fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
              minHeight: "52px",
              maxHeight: "160px",
            }}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="shrink-0 flex items-center justify-center w-10 h-10 rounded-lg m-1.5 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            style={{
              background: input.trim() && !isLoading ? "#d4a853" : "#3a3a3a",
              color: input.trim() && !isLoading ? "#1a1a1a" : "#666",
            }}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
        <p className="text-center mt-2 text-xs" style={{ color: "#555" }}>
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}
