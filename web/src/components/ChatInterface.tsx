'use client';

import { useState } from 'react';
import { Send, DollarSign } from 'lucide-react';
import { generateHedgeStream } from '@/lib/api';
import { ProgressTracker } from './ProgressTracker';

export function ChatInterface() {
  const [concern, setConcern] = useState('');
  const [budget, setBudget] = useState(100);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!concern.trim()) return;

    setIsLoading(true);
    setProgress([]);

    try {
      // Stream results using SSE
      await generateHedgeStream(
        { concern, budget, num_markets: 500 },
        (event) => {
          if (event.type === 'progress') {
            console.log('[ChatInterface] Progress:', event.data.message);
            setProgress(prev => [...prev, event.data.message]);
          } else if (event.type === 'search_complete') {
            setProgress(prev => [...prev, `✓ Found ${event.data.markets_found} markets`]);
          } else if (event.type === 'filter_complete') {
            setProgress(prev => [...prev, `✓ Filtered to ${event.data.markets_filtered} relevant markets`]);
          } else if (event.type === 'bundles_complete') {
            setProgress(prev => [...prev, `✓ Created ${event.data.num_bundles} themed portfolios`]);
          } else if (event.type === 'complete') {
            console.log('[ChatInterface] Complete event received', event.data);
            // Navigate to results page with data
            if (typeof window !== 'undefined') {
              console.log('[ChatInterface] Saving to session storage and redirecting...');
              sessionStorage.setItem('hedgeResults', JSON.stringify(event.data));
              sessionStorage.setItem('hedgeConcern', concern);
              window.location.href = '/results';
            }
          } else if (event.type === 'error') {
            console.error('[ChatInterface] Error event:', event.data);
            alert(`Error: ${event.data.message}`);
            setIsLoading(false);
          }
        }
      );
    } catch (error) {
      console.error('Error:', error);
      alert('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const exampleConcerns = [
    "AI replacing software engineers",
    "Recession affecting tech sector",
    "Housing market crash",
    "Climate change impacting agriculture"
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold text-blue-600 mb-4">
          PolyHedge
        </h1>
        <p className="text-xl text-blue-500">
          Insurance on anything.
        </p>
      </div>

      {/* Chat Form */}
      <div className="bg-white rounded-2xl shadow-xl p-8 border border-blue-100">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Concern Input */}
          <div>
            <label className="block text-sm font-medium text-blue-700 mb-2">
              What are you worried about?
            </label>
            <textarea
              value={concern}
              onChange={(e) => setConcern(e.target.value)}
              placeholder="I am ... I am worried about ..."
              className="w-full h-32 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={isLoading}
            />
          </div>

          {/* Budget Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Hedge Budget
            </label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                min={10}
                step={10}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !concern.trim()}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                Analyzing...
              </>
            ) : (
              <>
                <Send className="h-5 w-5" />
                Generate Hedge Strategy
              </>
            )}
          </button>
        </form>

        {/* Progress Tracker */}
        {isLoading && progress.length > 0 && (
          <ProgressTracker steps={progress} />
        )}
      </div>
    </div>
  );
}
