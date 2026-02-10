'use client';

import { useState, useCallback } from 'react';
import { ChatWindow } from '@/components/chat';
import { ResultsPanel } from '@/components/results';
import { HistorySidebar, ConfigSidebar } from '@/components/sidebar';
import { useChat } from '@/hooks/useChat';
import { ForecastConfig } from '@/lib/types';

export default function Home() {
  const [config, setConfig] = useState<ForecastConfig>({
    capacity: 20,
    progressionRate: 0.95,
    bufferPercent: 10,
    quartersToForecast: 2,
    term: 'Spring 2026',
  });

  const { messages, isLoading, sendMessage, clearMessages, forecastResults, forecastSummary } = useChat(config);

  const [showConfig] = useState(true);

  const handleConfigChange = useCallback((partial: Partial<ForecastConfig>) => {
    setConfig((prev) => ({ ...prev, ...partial }));
  }, []);

  const handleNewChat = () => {
    clearMessages();
  };

  const handleDownload = useCallback(() => {
    if (!forecastResults) return;
    // Create CSV content
    const headers = ['Course', 'Campus', 'Projected Seats', 'Sections', 'Change %'];
    const rows = forecastResults.map(r => [
      r.course,
      r.campus,
      r.projectedSeats.toString(),
      r.sections.toString(),
      r.changePercent !== undefined ? `${r.changePercent}%` : 'N/A'
    ]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');

    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecast_${config.term.replace(/\s+/g, '_').toLowerCase()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [forecastResults, config.term]);

  const handleCompare = useCallback(() => {
    // TODO: Implement compare functionality
    console.log('Compare feature not yet implemented');
  }, []);

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
            onDownload={handleDownload}
            onCompare={handleCompare}
          />
        </div>
      </div>

      {/* Right Sidebar - Config */}
      {showConfig && (
        <ConfigSidebar
          config={config}
          onConfigChange={handleConfigChange}
          onToggleCollapse={() => {
            // TODO: Add a way to re-open the sidebar
            console.log('Config sidebar collapsed');
          }}
        />
      )}
    </div>
  );
}
