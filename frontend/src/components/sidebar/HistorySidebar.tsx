'use client';

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
    onSelectConversation?: (id: string) => void;
    conversations?: Conversation[];
    isCollapsed?: boolean;
}

export function HistorySidebar({ onNewChat, onSelectConversation, conversations = [], isCollapsed = false }: HistorySidebarProps) {
    if (isCollapsed) {
        return (
            <div className="hidden lg:flex flex-col items-center w-12 border-r border-border bg-muted/20 py-4">
                <Button variant="ghost" size="icon" onClick={onNewChat} aria-label="New chat">
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
        <div className="hidden lg:flex flex-col w-64 border-r border-border bg-muted/20">
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
                {conversations.length === 0 ? (
                    <p className="text-xs text-muted-foreground px-2 py-4 text-center">
                        No conversations yet. Start a new chat to begin forecasting.
                    </p>
                ) : (
                    Object.entries(grouped).map(([date, convs]) => (
                        <div key={date} className="mb-4">
                            <p className="text-xs text-muted-foreground font-medium px-2 mb-1">{date}</p>
                            {convs.map((conv) => (
                                <button
                                    key={conv.id}
                                    onClick={() => onSelectConversation?.(conv.id)}
                                    className={`w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors cursor-pointer ${conv.active
                                            ? 'bg-accent text-accent-foreground'
                                            : 'hover:bg-muted/50 text-muted-foreground'
                                        }`}
                                    aria-label={`Select conversation: ${conv.title}`}
                                    aria-current={conv.active ? 'page' : undefined}
                                >
                                    {conv.title}
                                </button>
                            ))}
                        </div>
                    ))
                )}
            </ScrollArea>
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
