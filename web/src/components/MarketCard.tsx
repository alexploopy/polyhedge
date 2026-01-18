'use client';

import { useRef, useEffect } from 'react';
import { TrendingUp, DollarSign, Target, ChevronDown, ChevronUp } from 'lucide-react';
import { HedgeBet } from '@/lib/types';
import { PriceChart } from './PriceChart';

interface Props {
  bet: HedgeBet;
  className?: string;
  onUpdateAllocation?: (value: number) => void;
  totalBudget?: number;
  isExpanded?: boolean;
  onToggle?: () => void;
}

export function MarketCard({ bet, className = '', onUpdateAllocation, totalBudget, isExpanded = false, onToggle }: Props) {
  const { market, outcome, allocation, allocation_percent, current_price, potential_payout, payout_multiplier } = bet;
  const cardRef = useRef<HTMLDivElement>(null);
  const wasExpandedRef = useRef(isExpanded);
  const expandedHeightRef = useRef<number>(0);

  useEffect(() => {
    if (!cardRef.current) return;

    // Opening: Save the current height, then scroll after expansion
    if (!wasExpandedRef.current && isExpanded) {
      // Wait for expansion to complete, then scroll to show content
      setTimeout(() => {
        if (cardRef.current) {
          expandedHeightRef.current = cardRef.current.offsetHeight;
          cardRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'nearest'
          });
        }
      }, 50);
    }

    // Closing: Always scroll to follow the collapse
    if (wasExpandedRef.current && !isExpanded) {
      const card = cardRef.current;
      const rectBefore = card.getBoundingClientRect();

      // After collapse animation completes, scroll to keep card in view
      setTimeout(() => {
        if (cardRef.current) {
          const rectAfter = cardRef.current.getBoundingClientRect();
          const heightDelta = rectBefore.height - rectAfter.height;

          // If the card was in view and collapsed significantly, scroll up with it
          if (heightDelta > 100) {
            cardRef.current.scrollIntoView({
              behavior: 'smooth',
              block: 'center', // Center the collapsed card
              inline: 'nearest'
            });
          }
        }
      }, 320); // Match animation duration (300ms) + small buffer
    }

    wasExpandedRef.current = isExpanded;
  }, [isExpanded]);

  const handleClick = (e: React.MouseEvent) => {
    // Prevent expansion if clicking on links or slider
    if ((e.target as HTMLElement).closest('a') || (e.target as HTMLElement).closest('input[type="range"]')) {
      return;
    }

    if (onToggle) {
      onToggle();
    }
  };

  return (
    <div
      ref={cardRef}
      className={`border border-gray-300 rounded-lg p-5 transition-all duration-300 ease-in-out bg-white cursor-pointer ${
        isExpanded ? 'ring-2 ring-blue-200 shadow-xl' : 'hover:shadow-md hover:border-gray-400'
      } ${className}`}
      onClick={handleClick}
    >
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1">
          {/* Market Question */}
          <h4 className={`font-semibold text-gray-900 mb-2 transition-all duration-200 ${
            isExpanded ? 'text-xl' : 'text-lg'
          }`}>
            <a
              href={`https://polymarket.com/event/${market.market.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {market.market.question}
            </a>
          </h4>

          {/* Correlation Explanation */}
          <p className={`text-sm text-gray-600 mb-4 transition-all duration-200 ${
            isExpanded ? '' : 'line-clamp-2'
          }`}>
            {market.correlation_explanation}
          </p>
        </div>

        {/* Expand/Collapse Icon */}
        <div className="flex-shrink-0 mt-1">
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-blue-600 transition-transform duration-200" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400 transition-transform duration-200 hover:text-gray-600" />
          )}
        </div>
      </div>

      {/* Recommended Outcome */}
      <div className={`mb-4 p-3 rounded-lg transition-all duration-200 ${
        outcome.toLowerCase() === 'no' ? 'bg-red-50' : 'bg-green-50'
      }`}>
        <div className="flex items-center gap-2 mb-1">
          <Target className={`h-4 w-4 ${outcome.toLowerCase() === 'no' ? 'text-red-600' : 'text-green-600'}`} />
          <span className={`text-sm font-medium ${outcome.toLowerCase() === 'no' ? 'text-red-900' : 'text-green-900'}`}>
            Recommended Bet
          </span>
        </div>
        <p className={`text-sm ${outcome.toLowerCase() === 'no' ? 'text-red-700' : 'text-green-700'}`}>
          <span className="font-semibold">{outcome}</span> @ ${current_price.toFixed(2)}
        </p>
      </div>

      {/* Financial Details */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-300">
        <div>
          <div className="flex items-center gap-1 mb-1">
            <DollarSign className="h-4 w-4 text-gray-400" />
            <span className="text-xs text-gray-500">Allocation</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            ${allocation.toFixed(2)}
          </p>
          <p className="text-xs text-gray-500">
            {totalBudget && totalBudget > 0 ? ((allocation / totalBudget) * 100).toFixed(1) : allocation_percent.toFixed(1)}%
          </p>
        </div>

        <div>
          <div className="flex items-center gap-1 mb-1">
            <TrendingUp className="h-4 w-4 text-gray-400" />
            <span className="text-xs text-gray-500">Multiplier</span>
          </div>
          <p className="text-sm font-semibold text-gray-900">
            {payout_multiplier.toFixed(2)}x
          </p>
        </div>

        <div>
          <div className="flex items-center gap-1 mb-1">
            <TrendingUp className="h-4 w-4 text-green-500" />
            <span className="text-xs text-gray-500">Max Payout</span>
          </div>
          <p className="text-sm font-semibold text-green-600">
            ${potential_payout.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Expanded Content */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="mt-6 pt-6 border-t border-gray-200">
          {/* Allocation Slider */}
          {onUpdateAllocation && totalBudget && (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-5 rounded-lg border border-blue-200 mb-6 transform transition-all duration-200" onClick={(e) => e.stopPropagation()}>
              <label className="block text-sm font-semibold text-gray-800 mb-3">
                Adjust Allocation
              </label>
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-gray-600 w-12 text-right">0%</span>
                <input
                  type="range"
                  min="0"
                  max={totalBudget}
                  step={totalBudget / 100}
                  value={allocation}
                  onChange={(e) => onUpdateAllocation(parseFloat(e.target.value))}
                  className="flex-1 h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <span className="text-sm font-medium text-gray-600 w-12">100%</span>
              </div>
              <div className="flex justify-between items-center mt-3">
                <span className="text-xs text-gray-600">
                  Current: <strong className="text-gray-900">${allocation.toFixed(2)}</strong> ({((allocation / totalBudget) * 100).toFixed(1)}%)
                </span>
                <span className="text-xs text-blue-700 font-semibold">
                  Est. Payout: ${(allocation * (payout_multiplier || 1)).toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {/* Price History Chart */}
          <div className="mb-6" onClick={(e) => e.stopPropagation()}>
            {(() => {
              // Find the outcome index for the recommended outcome
              const outcomeIdx = market.market.outcomes.findIndex(
                (o) => o.name.toLowerCase() === outcome.toLowerCase()
              );
              return (
                <PriceChart
                  marketId={market.market.id}
                  outcomeIndex={outcomeIdx >= 0 ? outcomeIdx : 0}
                  outcomeName={outcome}
                />
              );
            })()}
          </div>

          {/* Additional Market Info */}
          <div className="bg-gray-50 p-5 rounded-lg border border-gray-200">
            <h5 className="text-sm font-semibold text-gray-800 mb-3">Market Details</h5>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-500 block mb-1">Liquidity</span>
                <span className="font-semibold text-gray-900">
                  ${(market.market.liquidity || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Volume</span>
                <span className="font-semibold text-gray-900">
                  ${(market.market.volume || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">24h Volume</span>
                <span className="font-semibold text-gray-900">
                  ${(market.market.volume_24hr || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Current Price</span>
                <span className="font-semibold text-gray-900">
                  ${current_price.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Risk-Reward</span>
                <span className="font-semibold text-gray-900">
                  {payout_multiplier.toFixed(2)}x
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Status</span>
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                  market.market.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {market.market.active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          {/* Market Description */}
          {market.market.description && (
            <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg">
              <h5 className="text-sm font-semibold text-gray-800 mb-2">Description</h5>
              <p className="text-sm text-gray-600 leading-relaxed">
                {market.market.description}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Liquidity Badge (Collapsed only) */}
      {!isExpanded && (
        <div className="mt-3 pt-3 border-t border-gray-100 flex justify-between items-center">
          <span className="inline-block text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
            Liquidity: ${(market.market.liquidity || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
          <span className="text-xs text-gray-400">Click for details</span>
        </div>
      )}
    </div>
  );
}
