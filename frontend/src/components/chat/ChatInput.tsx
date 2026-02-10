'use client';

import { useState, useRef, useEffect, KeyboardEvent, FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ChatInputProps {
    onSend: (message: string) => void;
    isLoading?: boolean;
    placeholder?: string;
}

export function ChatInput({
    onSend,
    isLoading = false,
    placeholder = 'Ask me anything about forecasting...',
}: ChatInputProps) {
    const [value, setValue] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Focus input on mount
    useEffect(() => {
        textareaRef.current?.focus();
    }, []);

    const handleSend = () => {
        if (value.trim() && !isLoading) {
            onSend(value.trim());
            setValue('');
            // Reset textarea height
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleInput = (e: FormEvent<HTMLTextAreaElement>) => {
        const target = e.currentTarget;
        setValue(target.value);

        // Auto-resize textarea
        target.style.height = 'auto';
        target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
    };

    return (
        <div className="border-t border-border bg-background p-4">
            <div className="flex gap-2 max-w-3xl mx-auto">
                <Textarea
                    ref={textareaRef}
                    value={value}
                    onInput={handleInput}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    disabled={isLoading}
                    className="flex-1 bg-muted/50 border-border focus-visible:ring-1 focus-visible:ring-ring min-h-[44px] max-h-[200px] resize-none"
                    rows={1}
                />
                <Button
                    onClick={handleSend}
                    disabled={!value.trim() || isLoading}
                    size="icon"
                    className="shrink-0 self-end"
                    aria-label="Send message"
                >
                    {isLoading ? (
                        <LoadingSpinner />
                    ) : (
                        <SendIcon />
                    )}
                </Button>
            </div>

            {/* Quick action suggestions */}
            <div className="flex gap-2 mt-3 max-w-3xl mx-auto overflow-x-auto pb-1">
                {['Forecast Spring 2026', 'Compare methods', 'Show settings', 'Help'].map(
                    (action) => (
                        <button
                            key={action}
                            onClick={() => onSend(action)}
                            disabled={isLoading}
                            className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-full border border-border bg-muted/30 hover:bg-muted transition-colors disabled:opacity-50"
                        >
                            {action}
                        </button>
                    )
                )}
            </div>
        </div>
    );
}

function SendIcon() {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
        >
            <path d="m22 2-7 20-4-9-9-4Z" />
            <path d="M22 2 11 13" />
        </svg>
    );
}

function LoadingSpinner() {
    return (
        <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
        >
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
        </svg>
    );
}
