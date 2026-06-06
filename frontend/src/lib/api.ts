// API client for communicating with the FastAPI backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ChatRequest {
    message: string;
    context?: Record<string, unknown>;
    history?: Array<{ role: string; content: string }>;
    term?: string;
}

export interface ForecastRequest {
    term: string;
    method?: 'sequence' | 'prophet' | 'demand';
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

    // Forecast endpoint - run forecast and get results
    async runForecast(request: ForecastRequest) {
        return this.request<{
            results: Array<{
                course: string;
                campus: string;
                projectedSeats: number;
                sections: number;
                change?: number;
                changePercent?: number;
                adjusted?: boolean;
            }>;
            summary: {
                totalStudents: number;
                totalSections: number;
                coursesForecasted: number;
                method: string;
                adjustmentsApplied?: number;
            };
        }>('/api/forecast', {
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

    // Get current config
    async getConfig() {
        return this.request<{
            capacity: number;
            progressionRate: number;
            bufferPercent: number;
            quartersToForecast: number;
        }>('/api/config', {
            method: 'GET',
        });
    }

    // Update config
    async updateConfig(config: Partial<{
        capacity: number;
        progressionRate: number;
        bufferPercent: number;
        quartersToForecast: number;
        defaultTerm: string;
    }>) {
        return this.request<{ success: boolean }>('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }

    // Get available terms
    async getTerms() {
        return this.request<{
            available_terms: Array<{ termCode: string; label: string }>;
            forecastable_terms: Array<{ termCode: string; label: string }>;
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
            adjustments: Array<{
                id: string;
                type: string;
                parameter?: string | null;
                operation?: string | null;
                value: number;
                scope: { course?: string | null; campus?: string | null };
                reason: string;
                enabled: boolean;
                source: string;
            }>;
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
            adjustments: Array<{
                id: string;
                type: string;
                parameter?: string | null;
                operation?: string | null;
                value: number;
                scope: { course?: string | null; campus?: string | null };
                reason: string;
                enabled: boolean;
                source: string;
            }>;
        }>(`/api/adjustments/${encodeURIComponent(term)}/${adjId}/toggle`, {
            method: 'PUT',
        });
    }

    async removeAdjustment(term: string, adjId: string) {
        return this.request<{
            term: string;
            adjustments: Array<{
                id: string;
                type: string;
                parameter?: string | null;
                operation?: string | null;
                value: number;
                scope: { course?: string | null; campus?: string | null };
                reason: string;
                enabled: boolean;
                source: string;
            }>;
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
