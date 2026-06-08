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

    // Callback to signal adjustment changes (parent component can reload adjustments)
    const [lastAdjustmentChange, setLastAdjustmentChange] = useState(0);

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
            // Build conversation history for LLM (last 20 messages)
            const allMessages = [...messages, userMessage];
            const history = allMessages.slice(-20).map((m) => ({
                role: m.role,
                content: m.content,
            }));

            // Send to API with history and current term
            const response = await api.sendMessage({
                message: content,
                history,
                term: config?.term,
            });

            const intent = response.parsedCommand?.intent;
            const shouldRunForecast = intent === 'forecast' || intent === 'adjust';

            // Run forecast if intent is forecast or adjust
            if (shouldRunForecast) {
                const parsedTerm = response.parsedCommand.parameters.term as string;
                const forecastTerm = parsedTerm || config?.term || 'Spring 2026';

                const forecastResponse = await api.runForecast({
                    term: forecastTerm,
                    method: 'historical',
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
                });
            }

            // If adjustments were extracted, signal a change
            if (response.adjustments && response.adjustments.length > 0) {
                setLastAdjustmentChange(Date.now());
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
                    adjustments: response.adjustments as NonNullable<Message['metadata']>['adjustments'],
                    llm_used: response.llm_used,
                },
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error('API error:', error);

            const errorMessage: Message = {
                id: generateId(),
                role: 'assistant',
                content: "I couldn't connect to the backend server. Please make sure the backend is running on port 8000. You can start it with `./Forecast_Tool_Launcher.command` or manually with `python3 api/main.py`.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    }, [config, messages]);

    // Run a forecast directly for a chosen term (e.g. the Run Forecast button),
    // without going through the chat parser. Surfaces backend errors (like the
    // no-feeder 422) as an assistant message.
    const runForecast = useCallback(async (term?: string) => {
        const forecastTerm = term || config?.term || 'Spring 2026';
        setIsLoading(true);
        try {
            const forecastResponse = await api.runForecast({
                term: forecastTerm,
                method: 'historical',
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
            });
        } catch (error) {
            const detail = error instanceof Error ? error.message : 'Forecast failed.';
            setMessages((prev) => [...prev, {
                id: generateId(),
                role: 'assistant',
                content: detail,
                timestamp: new Date(),
            }]);
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
        runForecast,
        clearMessages,
        forecastResults,
        forecastSummary,
        lastAdjustmentChange,
    };
}
