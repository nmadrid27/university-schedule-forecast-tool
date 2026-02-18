'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { Message } from '@/lib/types';
import { AdjustmentCard } from './AdjustmentCard';
import { Adjustment } from '@/lib/adjustments';

interface MessageBubbleProps {
    message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === 'user';

    // Format timestamp
    const timeString = message.timestamp.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });

    const adjustments = (message.metadata?.adjustments || []) as Adjustment[];

    return (
        <div
            className={cn(
                'flex gap-3 mb-4',
                isUser ? 'flex-row-reverse' : 'flex-row'
            )}
        >
            {/* Avatar */}
            <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback
                    className={cn(
                        'text-sm font-medium',
                        isUser
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-blue-600 text-white'
                    )}
                >
                    {isUser ? 'U' : 'AI'}
                </AvatarFallback>
            </Avatar>

            {/* Message Content */}
            <div
                className={cn(
                    'flex flex-col max-w-[80%]',
                    isUser ? 'items-end' : 'items-start'
                )}
            >
                <div
                    className={cn(
                        'rounded-lg px-4 py-3 shadow-sm',
                        isUser
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-card border border-border'
                    )}
                >
                    {/* Message text with markdown-like formatting */}
                    <div className="text-sm whitespace-pre-wrap">
                        {message.content.split('\n').map((line, i) => {
                            // Parse bold text markers (**) safely
                            const parts = line.split(/\*\*(.*?)\*\*/g);
                            const isBullet = line.trim().startsWith('•');

                            if (isBullet) {
                                // Render bullet point with bold text support
                                return (
                                    <div key={i} className="flex gap-2">
                                        <span>•</span>
                                        <span>
                                            {parts.map((part, j) =>
                                                j % 2 === 1 ? <strong key={j}>{part}</strong> : part
                                            )}
                                        </span>
                                    </div>
                                );
                            }

                            // Regular line with bold text support
                            return (
                                <span key={i}>
                                    {parts.map((part, j) =>
                                        j % 2 === 1 ? <strong key={j}>{part}</strong> : part
                                    )}
                                    {i < message.content.split('\n').length - 1 && <br />}
                                </span>
                            );
                        })}
                    </div>

                    {/* Adjustment card inline */}
                    {adjustments.length > 0 && (
                        <AdjustmentCard adjustments={adjustments} />
                    )}
                </div>

                {/* Badges row */}
                <div className="flex items-center gap-2 mt-1 px-1">
                    {/* Timestamp */}
                    <span className="text-xs text-muted-foreground">
                        {timeString}
                    </span>

                    {/* LLM badge */}
                    {message.metadata?.llm_used && (
                        <span className="inline-flex items-center rounded-full bg-purple-100 dark:bg-purple-900/30 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 dark:text-purple-300">
                            AI
                        </span>
                    )}

                    {/* Intent badge for parsed commands */}
                    {message.metadata?.parsedCommand?.intent &&
                        message.metadata.parsedCommand.intent !== 'unknown' && (
                            <span className="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium text-muted-foreground">
                                {message.metadata.parsedCommand.intent}
                            </span>
                        )}
                </div>
            </div>
        </div>
    );
}
