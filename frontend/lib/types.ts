export type Source = {
  source_id: string;
  document_id: string;
  title: string;
  text: string;
  source_uri?: string;
  page?: number;
  chunk_index: number;
  language: string;
  score: number;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  language: "ar" | "en" | "mixed";
  sources: Source[];
  grounded: boolean;
  request_id: string;
  latency_ms: number;
  model: string;
  retrieval_backend: string;
};

export type UIMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  meta?: Pick<ChatResponse, "grounded" | "latency_ms" | "model" | "retrieval_backend">;
};
