import { useRef } from "react";
import { useChat as useVercelChat, Chat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import type { UIMessage } from "ai";
import type { Citation } from "@/lib/api";

export interface MessageMetadata {
  citations?: Citation[];
}

// UIMessage extended with our app-specific citation metadata
export type Message = UIMessage<MessageMetadata>;

export function useChat(repoId: string) {
  // DefaultChatTransport is the standard Vercel AI SDK transport —
  // expects createUIMessageStreamResponse from the server
  const chatRef = useRef(
    new Chat<Message>({
      transport: new DefaultChatTransport({
        api: "/api/chat",
        body: { repoId },
      }),
    }),
  );

  const { messages, sendMessage, status } = useVercelChat({
    chat: chatRef.current,
  });

  const isLoading = status !== "ready";

  return {
    messages,
    sendMessage,
    isLoading,
    status,
  };
}
