export interface DocumentInfo {
  doc_id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
  size_bytes: number;
}

export interface UploadResponse {
  indexed: DocumentInfo[];
  errors: string[];
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
}

export interface ReindexResponse {
  reindexed_documents: number;
  total_chunks: number;
}

export interface SourceChunk {
  doc_id: string;
  filename: string;
  chunk_index: number;
  text: string;
  score: number;
  location: string | null;
}

export interface WebSource {
  title: string;
  url: string;
  snippet: string;
}

export interface ChatRequest {
  question: string;
  top_k?: number;
  model?: string;
  web_search?: boolean;
  doc_ids?: string[];
}

export interface ChatResponse {
  answer: string;
  sources: SourceChunk[];
  web_sources: WebSource[];
  has_sufficient_context: boolean;
}

export interface HealthResponse {
  status: string;
  llm_provider: string;
  llm_model: string;
  llm_reachable: boolean;
  documents_indexed: number;
  total_chunks: number;
}

export interface ModelsResponse {
  provider: string;
  current_model: string;
  available_models: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: SourceChunk[];
  webSources?: WebSource[];
  hasSufficientContext?: boolean;
  timestamp: Date;
}
