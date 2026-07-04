import { useRef, useState } from "react";
import { postChat } from "./api";
import type { Message } from "./types";
import { ChatInput } from "./components/ChatInput";
import { MessageBubble } from "./components/MessageBubble";

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }

  async function handleSubmit(question: string) {
    const id = crypto.randomUUID();
    setMessages((prev) => [...prev, { id, question, loading: true }]);
    setLoading(true);
    scrollToBottom();

    try {
      const response = await postChat(question);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, response, loading: false } : m))
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? { ...m, error: (err as Error).message, loading: false }
            : m
        )
      );
    } finally {
      setLoading(false);
      scrollToBottom();
    }
  }

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-slate-800 px-6 py-4">
        <h1 className="text-lg font-semibold text-white tracking-tight">QueryMind</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Natural-language queries for the Chinook music database
        </p>
      </header>

      {/* Message list */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <p className="text-slate-400 text-sm">Ask a question about the Chinook music database</p>
            <p className="text-slate-600 text-xs">
              Try: "Which artist has the most albums?" or "Top 5 selling tracks"
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      {/* Input */}
      <ChatInput onSubmit={handleSubmit} disabled={loading} />
    </div>
  );
}
