import type { Message } from "../types";
import { TracePanel } from "./TracePanel";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  return (
    <div className="max-w-3xl mx-auto space-y-2">
      {/* User question */}
      <div className="flex justify-end">
        <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm max-w-[80%] leading-relaxed">
          {message.question}
        </div>
      </div>

      {/* Loading */}
      {message.loading && (
        <div className="flex justify-start">
          <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-500">
            <span className="animate-pulse">Thinking…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {message.error && (
        <div className="flex justify-start">
          <div className="bg-red-950 border border-red-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-red-300 max-w-[80%] leading-relaxed">
            {message.error}
          </div>
        </div>
      )}

      {/* Answer + trace */}
      {message.response && (
        <div className="flex flex-col items-start gap-2">
          <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-100 max-w-[80%] leading-relaxed">
            {message.response.answer}
          </div>
          <TracePanel response={message.response} />
        </div>
      )}
    </div>
  );
}
