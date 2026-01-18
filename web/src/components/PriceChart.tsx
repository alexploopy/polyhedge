'use client';

import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { fetchPriceHistory, PriceHistoryPoint } from '@/lib/api';

interface Props {
  marketId: string;
  outcomeIndex?: number;
  outcomeName?: string;
}

interface ChartDataPoint {
  date: string;
  price: number;
  timestamp: number;
  fullDate: string;
}

export function PriceChart({ marketId, outcomeIndex = 0, outcomeName = 'Yes' }: Props) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHistory() {
      setLoading(true);
      setError(null);

      console.log('[PriceChart] Fetching history for market:', marketId, 'outcome:', outcomeIndex);

      try {
        const history = await fetchPriceHistory(marketId, '1m', outcomeIndex);
        console.log('[PriceChart] Received history:', history.length, 'points');

        if (history.length === 0) {
          setError('No price history available');
          setData([]);
        } else {
          const chartData: ChartDataPoint[] = history.map((point: PriceHistoryPoint) => {
            const date = new Date(point.t * 1000);
            return {
              date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
              price: point.p,
              timestamp: point.t,
              fullDate: date.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              }),
            };
          });
          setData(chartData);
        }
      } catch (err) {
        console.error('Error loading price history:', err);
        setError('Failed to load price history');
      } finally {
        setLoading(false);
      }
    }

    if (marketId) {
      loadHistory();
    }
  }, [marketId, outcomeIndex]);

  if (loading) {
    return (
      <div className="h-48 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2 text-gray-500">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          <span className="text-sm">Loading price history...</span>
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
        <span className="text-sm text-gray-400">{error || 'No price data available'}</span>
      </div>
    );
  }

  const minPrice = Math.max(0, Math.min(...data.map((d) => d.price)) - 0.05);
  const maxPrice = Math.min(1, Math.max(...data.map((d) => d.price)) + 0.05);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex justify-between items-center mb-3">
        <h5 className="text-sm font-semibold text-gray-800">
          Price History (Last 30 Days)
        </h5>
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
          {outcomeName}
        </span>
      </div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#6B7280' }}
              tickLine={false}
              axisLine={{ stroke: '#E5E7EB' }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              tick={{ fontSize: 10, fill: '#6B7280' }}
              tickLine={false}
              axisLine={{ stroke: '#E5E7EB' }}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const point = payload[0].payload as ChartDataPoint;
                  return (
                    <div className="bg-white border border-gray-200 shadow-lg rounded-lg p-3">
                      <p className="text-xs text-gray-500 mb-1">{point.fullDate}</p>
                      <p className="text-sm font-semibold text-blue-600">
                        ${point.price.toFixed(3)}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {(point.price * 100).toFixed(1)}% probability
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="price"
              stroke="#3B82F6"
              strokeWidth={2}
              fill="url(#priceGradient)"
              dot={false}
              activeDot={{
                r: 5,
                fill: '#3B82F6',
                stroke: '#fff',
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
