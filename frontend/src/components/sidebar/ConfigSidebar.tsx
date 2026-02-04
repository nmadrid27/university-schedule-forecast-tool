'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ForecastConfig } from '@/lib/types';

interface ConfigSidebarProps {
    config: ForecastConfig;
    onConfigChange?: (config: Partial<ForecastConfig>) => void;
    isCollapsed?: boolean;
}

export function ConfigSidebar({
    config,
    onConfigChange,
    isCollapsed = false,
}: ConfigSidebarProps) {
    const [localConfig, setLocalConfig] = useState(config);

    if (isCollapsed) {
        return (
            <div className="w-12 border-l border-border bg-muted/20 flex flex-col items-center py-4">
                <Button variant="ghost" size="icon">
                    <SettingsIcon className="h-5 w-5" />
                </Button>
            </div>
        );
    }

    const handleChange = (key: keyof ForecastConfig, value: number | string) => {
        const newConfig = { ...localConfig, [key]: value };
        setLocalConfig(newConfig);
        onConfigChange?.({ [key]: value });
    };

    return (
        <div className="w-72 border-l border-border bg-muted/20 flex flex-col">
            {/* Header */}
            <div className="p-4 flex items-center justify-between">
                <h3 className="font-semibold">Configuration</h3>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                    <ChevronRightIcon className="h-4 w-4" />
                </Button>
            </div>

            <Separator />

            {/* Config sections */}
            <div className="flex-1 p-4 space-y-6 overflow-y-auto">
                {/* Data Source */}
                <ConfigSection title="Data Source">
                    <div className="text-sm text-muted-foreground">
                        Internal Data Lake, Banner
                    </div>
                    <Button variant="ghost" size="sm" className="mt-1 h-7 px-2 text-xs">
                        <PencilIcon className="h-3 w-3 mr-1" />
                        Edit
                    </Button>
                </ConfigSection>

                {/* Model Selection */}
                <ConfigSection title="Model Selection">
                    <div className="space-y-1">
                        <div className="text-sm font-medium">Sequence-based v2.1</div>
                        <div className="text-xs text-muted-foreground">
                            Confidence Level: <span className="text-green-500">95%</span>
                        </div>
                    </div>
                    <Button variant="ghost" size="sm" className="mt-1 h-7 px-2 text-xs">
                        <PencilIcon className="h-3 w-3 mr-1" />
                        Edit
                    </Button>
                </ConfigSection>

                {/* Forecast Horizon */}
                <ConfigSection title="Forecast Horizon">
                    <div className="text-sm font-medium">{localConfig.term}</div>
                    <Button variant="ghost" size="sm" className="mt-1 h-7 px-2 text-xs">
                        <PencilIcon className="h-3 w-3 mr-1" />
                        Edit
                    </Button>
                </ConfigSection>

                {/* Parameters */}
                <ConfigSection title="Parameters">
                    <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Capacity</span>
                            <span>{localConfig.capacity} students</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Progression</span>
                            <span>{(localConfig.progressionRate * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-muted-foreground">Buffer</span>
                            <span>{localConfig.bufferPercent}%</span>
                        </div>
                    </div>
                    <Button variant="ghost" size="sm" className="mt-2 h-7 px-2 text-xs">
                        <PencilIcon className="h-3 w-3 mr-1" />
                        Edit
                    </Button>
                </ConfigSection>
            </div>

            <Separator />

            {/* Footer */}
            <div className="p-4">
                <Button variant="outline" size="sm" className="w-full">
                    Reset to Defaults
                </Button>
            </div>
        </div>
    );
}

function ConfigSection({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <div>
            <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium">{title}</h4>
            </div>
            {children}
        </div>
    );
}

function SettingsIcon({ className }: { className?: string }) {
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
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
        </svg>
    );
}

function PencilIcon({ className }: { className?: string }) {
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
            <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
        </svg>
    );
}

function ChevronRightIcon({ className }: { className?: string }) {
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
            <path d="m9 18 6-6-6-6" />
        </svg>
    );
}
