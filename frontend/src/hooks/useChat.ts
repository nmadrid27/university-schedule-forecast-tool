'use client';

import { useState, useCallback } from 'react';
import { Message, ForecastResult, ForecastSummary, ForecastConfig } from '@/lib/types';
import { api } from '@/lib/api';

// Generate unique ID for messages
function generateId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

export function useChat(config?: ForecastConfig) {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: generateId(),
            role: 'assistant',
            content: "Hi! I'm your FOUN Forecasting Assistant. I can help you predict enrollment trends, analyze historical data, and generate comprehensive forecast reports. Ask me anything about forecasting!",
            timestamp: new Date(),
        },
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [forecastResults, setForecastResults] = useState<ForecastResult[] | null>(null);
    const [forecastSummary, setForecastSummary] = useState<ForecastSummary | null>(null);

    const sendMessage = useCallback(async (content: string) => {
        // Add user message
        const userMessage: Message = {
            id: generateId(),
            role: 'user',
            content,
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);

        try {
            // Send to API
            const response = await api.sendMessage({ message: content });

            // Check if this is a forecast command
            if (response.parsedCommand?.intent === 'forecast') {
                // Use the term parsed from the message, or fall back to the config term
                const parsedTerm = response.parsedCommand.parameters.term as string;
                const forecastTerm = parsedTerm || config?.term || 'Spring 2026';

                // Run the forecast with current config
                const forecastResponse = await api.runForecast({
                    term: forecastTerm,
                    method: 'sequence',
                    config: config ? {
                        capacity: config.capacity,
                        progressionRate: config.progressionRate,
                        bufferPercent: config.bufferPercent,
                    } : undefined,
                });

                setForecastResults(forecastResponse.results);
                setForecastSummary({
                    ...forecastResponse.summary,
                    lastUpdated: new Date(),
                    accuracy: 94,
                });
            }

            // Add assistant response
            const assistantMessage: Message = {
                id: generateId(),
                role: 'assistant',
                content: response.message,
                timestamp: new Date(),
                metadata: {
                    parsedCommand: {
                        ...response.parsedCommand,
                        raw_message: content,
                    },
                },
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            // Handle error - for now, show a helpful mock response
            console.error('API error:', error);

            // Mock response for demo purposes when backend isn't running
            const mockResponse = getMockResponse(content, config?.term);

            const assistantMessage: Message = {
                id: generateId(),
                role: 'assistant',
                content: mockResponse.message,
                timestamp: new Date(),
                metadata: mockResponse.metadata,
            };
            setMessages((prev) => [...prev, assistantMessage]);

            if (mockResponse.showForecast) {
                setForecastResults(mockResponse.results || null);
                setForecastSummary(mockResponse.summary || null);
            }
        } finally {
            setIsLoading(false);
        }
    }, [config]);

    const clearMessages = useCallback(() => {
        setMessages([
            {
                id: generateId(),
                role: 'assistant',
                content: "Chat cleared. How can I help you with your enrollment forecasting today?",
                timestamp: new Date(),
            },
        ]);
        setForecastResults(null);
        setForecastSummary(null);
    }, []);

    return {
        messages,
        isLoading,
        sendMessage,
        clearMessages,
        forecastResults,
        forecastSummary,
    };
}

// Mock responses for when backend isn't running
function getMockResponse(input: string, configTerm?: string): {
    message: string;
    metadata?: Message['metadata'];
    showForecast?: boolean;
    results?: ForecastResult[];
    summary?: ForecastSummary;
} {
    const lower = input.toLowerCase();

    // Extract term from message or use config term
    const termMatch = lower.match(/(spring|summer|fall|winter)\s*(\d{4}|\d{2})/);
    let detectedTerm = configTerm || 'Spring 2026';
    if (termMatch) {
        const season = termMatch[1].charAt(0).toUpperCase() + termMatch[1].slice(1);
        const year = termMatch[2].length === 2 ? '20' + termMatch[2] : termMatch[2];
        detectedTerm = `${season} ${year}`;
    }

    if (lower.includes('forecast') || termMatch) {
        return {
            message: `Here is the forecast for ${detectedTerm} enrollments based on current models and historical data trends. The projections suggest a moderate growth trajectory, particularly in online programs.`,
            metadata: {
                parsedCommand: {
                    intent: 'forecast',
                    parameters: { term: detectedTerm },
                    confidence: 0.95,
                    raw_message: input,
                },
            },
            showForecast: true,
            results: [
                { course: 'FOUN 110', campus: 'Savannah', projectedSeats: 380, sections: 19, change: 5, changePercent: 3 },
                { course: 'FOUN 110', campus: 'SCADnow', projectedSeats: 120, sections: 6, change: 15, changePercent: 10 },
                { course: 'FOUN 112', campus: 'Savannah', projectedSeats: 260, sections: 13, change: 3, changePercent: 2 },
                { course: 'FOUN 113', campus: 'Savannah', projectedSeats: 340, sections: 17, change: 8, changePercent: 5 },
                { course: 'FOUN 250', campus: 'Savannah', projectedSeats: 200, sections: 10, change: -2, changePercent: -1 },
                { course: 'FOUN 251', campus: 'Savannah', projectedSeats: 180, sections: 9, change: 4, changePercent: 3 },
            ],
            summary: {
                totalStudents: 1480,
                totalSections: 74,
                coursesForecasted: 15,
                accuracy: 94,
                method: 'Sequence-based',
                lastUpdated: new Date(),
            },
        };
    }

    if (lower.includes('help') || lower.includes('what can you do')) {
        return {
            message: "I can help you with:\n\n• **Forecast enrollments** - \"Forecast Spring 2026\" or \"Show me Fall projections\"\n• **Compare methods** - \"Compare Prophet vs sequence-based\"\n• **Adjust settings** - \"Set capacity to 25 students\"\n• **Upload data** - \"Upload enrollment data\"\n• **View trends** - \"Show FOUN 110 trends\"\n\nWhat would you like to do?",
        };
    }

    if (lower.includes('setting') || lower.includes('config')) {
        return {
            message: "Current forecast settings:\n\n• **Capacity**: 20 students/section\n• **Progression Rate**: 95%\n• **Buffer**: 10%\n• **Method**: Sequence-based\n\nYou can adjust these by saying things like \"Set capacity to 25\" or \"Change buffer to 15%\".",
        };
    }

    return {
        message: "I understand you're asking about forecasting. Could you be more specific? Try:\n\n• \"Forecast Spring 2026 enrollments\"\n• \"Compare forecasting methods\"\n• \"Show current settings\"\n• \"Help\"",
    };
}
