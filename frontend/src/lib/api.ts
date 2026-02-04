// API client for communicating with the FastAPI backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ChatRequest {
    message: string;
    context?: Record<string, unknown>;
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
            }>;
            summary: {
                totalStudents: number;
                totalSections: number;
                coursesForecasted: number;
                method: string;
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
                term: string;
                records: number;
                uploadedAt: string;
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
    }>) {
        return this.request<{ success: boolean }>('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config),
        });
    }

    // Health check
    async healthCheck() {
        return this.request<{ status: string }>('/api/health', {
            method: 'GET',
        });
    }
}

export const api = new ApiClient();
export default api;
