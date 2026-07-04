export interface ApiResponse {
  answer: string;
  sql: string;
  reasoning: string;
  rows: Record<string, unknown>[];
  row_count: number;
  execution_time_ms: number;
}

export interface Message {
  id: string;
  question: string;
  response?: ApiResponse;
  error?: string;
  loading: boolean;
}
