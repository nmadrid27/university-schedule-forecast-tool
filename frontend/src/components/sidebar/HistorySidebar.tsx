'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface Conversation {
    id: string;
    title: string;
    date: string;
    active?: boolean;
}

interface HistorySidebarProps {
    onNewChat: () => void;
    isCollapsed?: boolean;
}

export function HistorySidebar({ onNewChat, isCollapsed = false }: HistorySidebarProps) {
    const [conversations] = useState<Conversation[]>([
        { id: '1', title: 'Spring 2026 Forecast', date: 'Today', active: true },
        { id: '2', title: 'Data Analysis Q3', date: 'Today' },
        { id: '3', title: 'Model Comparison', date: 'Yesterday' },
        { id: '4', title: 'Spring 2026 Forecast - T...', date: 'Yesterday' },
        { id: '5', title: 'Data Analysis Q3, Model ...', date: 'Previous 7 Days' },
    ]);

    if (isCollapsed) {
        return (
            <div className="w-12 border-r border-border bg-muted/20 flex flex-col items-center py-4">
                <Button variant="ghost" size="icon" onClick={onNewChat}>
                    <PlusIcon className="h-5 w-5" />
                </Button>
            </div>
        );
    }

    // Group conversations by date
    const grouped = conversations.reduce((acc, conv) => {
        if (!acc[conv.date]) acc[conv.date] = [];
        acc[conv.date].push(conv);
        return acc;
    }, {} as Record<string, Conversation[]>);

    return (
        <div className="w-64 border-r border-border bg-muted/20 flex flex-col">
            {/* Header */}
            <div className="p-4">
                <Button onClick={onNewChat} variant="outline" className="w-full justify-start gap-2">
                    <PlusIcon className="h-4 w-4" />
                    New Chat
                </Button>
            </div>

            <Separator />

            {/* Conversation list */}
            <ScrollArea className="flex-1 px-2 py-2">
                {Object.entries(grouped).map(([date, convs]) => (
                    <div key={date} className="mb-4">
                        <p className="text-xs text-muted-foreground font-medium px-2 mb-1">{date}</p>
                        {convs.map((conv) => (
                            <button
                                key={conv.id}
                                className={`w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors ${conv.active
                                        ? 'bg-accent text-accent-foreground'
                                        : 'hover:bg-muted/50 text-muted-foreground'
                                    }`}
                            >
                                {conv.title}
                            </button>
                        ))}
                    </div>
                ))}
            </ScrollArea>

            {/* Footer */}
            <Separator />
            <div className="p-4">
                <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-muted-foreground">
                    <ExitIcon className="h-4 w-4" />
                    Exit
                </Button>
            </div>
        </div>
    );
}

function PlusIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M5 12h14" />
            <path d="M12 5v14" />
        </svg>
    );
}

function ExitIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={className}
        >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" x2="9" y1="12" y2="12" />
        </svg>
    );
}
