// TypeScript types for the Forecast Tool frontend

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    parsedCommand?: ParsedCommand;
    adjustments?: Array<{
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
    llm_used?: boolean;
  };
}

export interface ParsedCommand {
  intent: string;
  parameters: Record<string, unknown>;
  confidence: number;
  raw_message: string;
}

export interface ForecastResult {
  course: string;
  campus: string;
  projectedSeats: number;
  sections: number;
  change?: number;
  changePercent?: number;
  adjusted?: boolean;
}

export interface ForecastSummary {
  totalStudents: number;
  totalSections: number;
  coursesForecasted: number;
  accuracy?: number;
  method: string;
  lastUpdated: Date;
  adjustmentsApplied?: number;
}

export interface ForecastConfig {
  capacity: number;
  progressionRate: number;
  bufferPercent: number;
  quartersToForecast: number;
  term: string;
  campus?: string;
}

export interface ChatResponse {
  message: string;
  parsedCommand: ParsedCommand;
  forecastResults?: ForecastResult[];
  summary?: ForecastSummary;
}

export interface TermOption {
  termCode: string;
  label: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}
