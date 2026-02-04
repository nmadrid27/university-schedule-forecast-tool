// TypeScript types for the Forecast Tool frontend

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    parsedCommand?: ParsedCommand;
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
}

export interface ForecastSummary {
  totalStudents: number;
  totalSections: number;
  coursesForecasted: number;
  accuracy?: number;
  method: string;
  lastUpdated: Date;
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

export interface Conversation {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}
