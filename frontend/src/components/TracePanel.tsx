import { useState } from "react";
import type { ApiResponse } from "../types";
import { ResultTable } from "./ResultTable";

interface Props {
  response: ApiResponse;
}

export function TracePanel({ response }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="w-full max-w-[80%]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        Agent trace · {response.row_count} row{response.row_count !== 1 ? "s" : ""} ·{" "}
        {response.execution_time_ms.toFixed(0)} ms
      </button>

      {open && (
        <div className="mt-2 border border-slate-700 rounded-xl overflow-hidden text-sm divide-y divide-slate-700">
          {/* Reasoning */}
          <div className="px-4 py-3">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">
              Reasoning
            </p>
            <p className="text-slate-300 leading-relaxed text-xs">{response.reasoning}</p>
          </div>

          {/* SQL */}
          <div className="px-4 py-3 bg-slate-900">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-1.5">
              SQL
            </p>
            <pre className="text-xs text-emerald-400 font-mono whitespace-pre-wrap break-all leading-relaxed">
              {response.sql}
            </pre>
          </div>

          {/* Results table */}
          {response.rows.length > 0 && (
            <div className="px-4 py-3">
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
                Results ({response.row_count})
              </p>
              <ResultTable rows={response.rows} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
