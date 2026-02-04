'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { Message } from '@/lib/types';

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
                            // Bold text
                            const formattedLine = line.replace(
                                /\*\*(.*?)\*\*/g,
                                '<strong>$1</strong>'
                            );
                            // Bullet points
                            if (line.startsWith('• ')) {
                                return (
                                    <div key={i} className="flex gap-2">
                                        <span>•</span>
                                        <span dangerouslySetInnerHTML={{ __html: formattedLine.slice(2) }} />
                                    </div>
                                );
                            }
                            return (
                                <span key={i}>
                                    <span dangerouslySetInnerHTML={{ __html: formattedLine }} />
                                    {i < message.content.split('\n').length - 1 && <br />}
                                </span>
                            );
                        })}
                    </div>
                </div>

                {/* Timestamp */}
                <span className="text-xs text-muted-foreground mt-1 px-1">
                    {timeString}
                </span>

                {/* Intent badge for parsed commands */}
                {message.metadata?.parsedCommand?.intent &&
                    message.metadata.parsedCommand.intent !== 'unknown' && (
                        <span className="mt-1 inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium text-muted-foreground">
                            {message.metadata.parsedCommand.intent}
                        </span>
                    )}
            </div>
        </div>
    );
}
