// API client for communicating with the FastAPI backend

import type {
    AdjustmentRecord,
    ApiForecastConfig,
    DemandMetric,
    ForecastMethod,
    ForecastResult,
    ForecastSummary,
    TermOption,
} from '@/lib/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ChatRequest {
    message: string;
    context?: Record<string, unknown>;
    history?: Array<{ role: string; content: string }>;
    term?: string;
}

export interface ForecastRequest {
    term: string;
    // Sent top-level only; the backend reads request-level values before the
    // config dict, so repeating them inside config invites silent drift.
    method?: ForecastMethod;
    demandMetric?: DemandMetric;
    config?: {
        capacity?: number;
        progressionRate?: number;
        bufferPercent?: number;
    };
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `API request failed: ${response.status}`);
        }

        return response.json();
    }

    // Chat endpoint - parse user message and get response
    async sendMessage(request: ChatRequest) {
        return this.request<{
            message: string;
            parsedCommand: {
                intent: string;
                parameters: Record<string, unknown>;
                confidence: number;
            };
            adjustments?: Array<Record<string, unknown>>;
            llm_used: boolean;
        }>('/api/chat', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Forecast endpoint - run forecast and get results. The wire summary has
    // no lastUpdated; callers stamp it client-side (see useChat).
    async runForecast(request: ForecastRequest) {
        return this.request<{
            results: ForecastResult[];
            summary: Omit<ForecastSummary, 'lastUpdated'>;
        }>('/api/forecast', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    async runBacktest(request: ForecastRequest) {
        return this.request<{
            term: string;
            method: string;
            demandMetric: DemandMetric;
            metrics: Record<string, number | null>;
            byCampus: Record<string, Record<string, number | null>>;
            rows: Array<{
                course: string;
                campus: string;
                actual: number;
                forecast: number;
                error: number;
                absError: number;
                pctError?: number | null;
            }>;
        }>('/api/backtest', {
            method: 'POST',
            body: JSON.stringify(request),
        });
    }

    // Get available data files
    async getDataFiles() {
        return this.request<{
            files: Array<{
                name: string;
                path: string;
                size: number;
                modified: string;
            }>;
        }>('/api/data/files', {
            method: 'GET',
        });
    }

    async importDataFile(file: File, kind: 'master' | 'admits' = 'master') {
        const form = new FormData();
        form.append('file', file);
        form.append('kind', kind);
        // Use raw fetch (not this.request) so the browser sets the multipart
        // Content-Type with its boundary; do not set it manually.
        const response = await fetch(`${this.baseUrl}/api/data/import`, {
            method: 'POST',
            body: form,
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Import failed: ${response.status}`);
        }
        return response.json() as Promise<{ success: boolean; stored_as: string; kind: string; data_dir: string }>;
    }

    // Get current config
    async getConfig() {
        return this.request<ApiForecastConfig>('/api/config', {
            method: 'GET',
        });
    }

    // Update config
    async updateConfig(config: Partial<ApiForecastConfig>) {
        return this.request<{ success: boolean }>('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }

    // Get available terms
    async getTerms() {
        return this.request<{
            available_terms: TermOption[];
            forecastable_terms: TermOption[];
            forecastable_by_method?: Record<ForecastMethod, TermOption[]>;
        }>('/api/terms', {
            method: 'GET',
        });
    }

    // Health check
    async healthCheck() {
        return this.request<{ status: string }>('/api/health', {
            method: 'GET',
        });
    }

    // --- Adjustment endpoints ---

    async getAdjustments(term: string) {
        return this.request<{
            term: string;
            adjustments: AdjustmentRecord[];
        }>(`/api/adjustments/${encodeURIComponent(term)}`, {
            method: 'GET',
        });
    }

    async addAdjustment(term: string, adj: {
        type: string;
        parameter?: string | null;
        operation?: string | null;
        value: number;
        scope?: { course?: string | null; campus?: string | null };
        reason?: string;
    }) {
        return this.request<{ term: string; adjustment: Record<string, unknown> }>(
            `/api/adjustments/${encodeURIComponent(term)}`,
            {
                method: 'POST',
                body: JSON.stringify(adj),
            }
        );
    }

    async toggleAdjustment(term: string, adjId: string) {
        return this.request<{
            term: string;
            adjustments: AdjustmentRecord[];
        }>(`/api/adjustments/${encodeURIComponent(term)}/${adjId}/toggle`, {
            method: 'PUT',
        });
    }

    async removeAdjustment(term: string, adjId: string) {
        return this.request<{
            term: string;
            adjustments: AdjustmentRecord[];
        }>(`/api/adjustments/${encodeURIComponent(term)}/${adjId}`, {
            method: 'DELETE',
        });
    }

    // --- LLM config endpoints ---

    async getLLMStatus() {
        return this.request<{
            provider: string;
            model: string | null;
            base_url: string | null;
            has_key: boolean;
            configured: boolean;
        }>('/api/llm/status', {
            method: 'GET',
        });
    }

    async updateLLMConfig(config: {
        provider?: string;
        model?: string | null;
        base_url?: string | null;
        api_key?: string;
    }) {
        return this.request<{
            success: boolean;
            provider: string;
            model: string | null;
            configured: boolean;
        }>('/api/llm/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }
}

export const api = new ApiClient();
export default api;
