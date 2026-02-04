'use client';

import { useState } from 'react';
import { ChatWindow } from '@/components/chat';
import { ResultsPanel } from '@/components/results';
import { HistorySidebar, ConfigSidebar } from '@/components/sidebar';
import { useChat } from '@/hooks/useChat';
import { ForecastConfig } from '@/lib/types';

export default function Home() {
  const { messages, isLoading, sendMessage, clearMessages, forecastResults, forecastSummary } = useChat();

  const [showConfig, setShowConfig] = useState(true);
  const [config] = useState<ForecastConfig>({
    capacity: 20,
    progressionRate: 0.95,
    bufferPercent: 10,
    quartersToForecast: 2,
    term: 'Spring 2026',
  });

  const handleNewChat = () => {
    clearMessages();
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Left Sidebar - History */}
      <HistorySidebar onNewChat={handleNewChat} />

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Chat Panel (40%) */}
        <div className="w-[40%] min-w-[400px] border-r border-border">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSendMessage={sendMessage}
          />
        </div>

        {/* Results Panel (60%) */}
        <div className="flex-1">
          <ResultsPanel
            results={forecastResults}
            summary={forecastSummary}
          />
        </div>
      </div>

      {/* Right Sidebar - Config */}
      {showConfig && (
        <ConfigSidebar config={config} />
      )}
    </div>
  );
}
