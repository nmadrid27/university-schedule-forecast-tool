'use client';

import { useRef, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Message } from '@/lib/types';

interface ChatWindowProps {
    messages: Message[];
    isLoading: boolean;
    onSendMessage: (message: string) => void;
}

export function ChatWindow({ messages, isLoading, onSendMessage }: ChatWindowProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="border-b border-border p-4">
                <div className="max-w-3xl mx-auto">
                    <h2 className="text-lg font-semibold">Chat Assistant</h2>
                    <p className="text-sm text-muted-foreground">
                        Ask me anything about FOUN enrollment forecasting
                    </p>
                </div>
            </div>

            {/* Messages area */}
            <ScrollArea className="flex-1 p-4" ref={scrollRef}>
                <div className="max-w-3xl mx-auto">
                    {messages.map((message) => (
                        <MessageBubble key={message.id} message={message} />
                    ))}

                    {/* Loading indicator */}
                    {isLoading && (
                        <div className="flex gap-3 mb-4">
                            <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
                                <span className="text-sm font-medium text-white">AI</span>
                            </div>
                            <div className="bg-card border border-border rounded-lg px-4 py-3">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </ScrollArea>

            {/* Input */}
            <ChatInput onSend={onSendMessage} isLoading={isLoading} />
        </div>
    );
}
