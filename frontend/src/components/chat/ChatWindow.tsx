'use client';

import { useRef, useEffect, useState } from 'react';
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Message } from '@/lib/types';

interface ChatWindowProps {
    messages: Message[];
    isLoading: boolean;
    onSendMessage: (message: string) => void;
}

export function ChatWindow({ messages, isLoading, onSendMessage }: ChatWindowProps) {
    const viewportRef = useRef<HTMLDivElement>(null);
    const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (viewportRef.current && isAutoScrollEnabled) {
            viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
        }
    }, [messages, isAutoScrollEnabled]);

    // Detect manual scroll to disable auto-scroll
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const target = e.currentTarget;
        const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 50;
        setIsAutoScrollEnabled(isAtBottom);
    };

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
            <ScrollArea className="flex-1">
                <ScrollAreaPrimitive.Viewport
                    ref={viewportRef}
                    onScroll={handleScroll}
                    className="flex-1 p-4"
                >
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
                </ScrollAreaPrimitive.Viewport>
                <ScrollBar />
            </ScrollArea>

            {/* Input */}
            <ChatInput onSend={onSendMessage} isLoading={isLoading} />
        </div>
    );
}
