'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Layers, PieChart as PieChartIcon, RotateCcw, AlertTriangle, DollarSign } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { BundleMetrics, HedgeBundle } from '@/lib/types';
import { MarketCard } from './MarketCard';

interface Props {
    bundles: HedgeBundle[];
    metrics?: BundleMetrics[];
    activeIndex?: number | null;
    onToggle?: (index: number) => void;
    onUpdateBet?: (bundleIndex: number, betIndex: number, field: 'allocation' | 'multiplier', value: number) => void;
    onReset?: (bundleIndex: number) => void;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658'];

export function BundleViewer({ bundles, metrics, activeIndex, onToggle, onUpdateBet, onReset }: Props) {
    const [internalIndex, setInternalIndex] = useState<number | null>(0);
    const openIndex = activeIndex !== undefined ? activeIndex : internalIndex;
    const [expandedCardIndex, setExpandedCardIndex] = useState<number | null>(null);

    const handleToggle = (index: number) => {
        if (onToggle) {
            onToggle(index);
        } else {
            setInternalIndex(internalIndex === index ? null : index);
        }
    };

    const handleMarketClick = (betIndex: number) => {
        setExpandedCardIndex(betIndex);
        setTimeout(() => {
            const targetIndex = activeIndex !== undefined ? activeIndex : (internalIndex ?? 0);
            const element = document.getElementById(`market-card-${targetIndex}-${betIndex}`);
            if (element) {
                const headerOffset = 150; // Buffer to keep it in the upper half but not stuck at top
                const elementPosition = element.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth"
                });
            }
        }, 100);
    };

    return (
        <div className="space-y-8">
            <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <Layers className="h-6 w-6 text-blue-600" />
                    Hedge Strategy Options
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                    Choose one strategy below. Each option uses your full ${bundles[0]?.budget?.toFixed(0) || '100'} budget.
                </p>
            </div>
            <div className="space-y-4">
                {bundles.map((bundle, index) => {
                    const isOpen = openIndex === index;
                    const themeName = bundle.coverage_summary.split(':')[0] || `Strategy ${index + 1}`;
                    const bundleMetric = metrics ? metrics[index] : null;

                    const allocationData = bundle.bets.map((bet, betIndex) => ({
                        name: bet.market.market.question.length > 30
                            ? bet.market.market.question.substring(0, 30) + '...'
                            : bet.market.market.question,
                        value: bet.allocation,
                        color: COLORS[betIndex % COLORS.length]
                    }));

                    return (
                        <div
                            key={index}
                            id={`bundle-${index}`}
                            className={`border rounded-xl bg-white overflow-hidden transition-all duration-200 ${isOpen ? 'border-blue-200 shadow-md ring-1 ring-blue-100' : 'border-gray-300 hover:border-gray-400'}`}
                        >
                            <button
                                onClick={() => handleToggle(index)}
                                className="w-full flex items-center justify-between p-5 text-left bg-white group"
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`p-2 rounded-lg ${isOpen ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors'}`}>
                                        <Layers className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900">
                                            {themeName}
                                        </h3>
                                        <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                                            <span>{bundle.bets.length} positions</span>

                                            {bundleMetric && (
                                                <>
                                                    <span className="text-gray-300">|</span>
                                                    <span className={`flex items-center gap-1 ${bundleMetric.risk_score > 70 ? 'text-red-600' : bundleMetric.risk_score > 40 ? 'text-orange-500' : 'text-green-600'}`}>
                                                        <AlertTriangle className="h-3 w-3" />
                                                        Risk: {bundleMetric.risk_score.toFixed(0)}
                                                    </span>
                                                    <span className="text-gray-300">|</span>
                                                    <span className="flex items-center gap-1 text-gray-700">
                                                        <DollarSign className="h-3 w-3" />
                                                        Max: ${bundleMetric.total_max_payout?.toFixed(0)}
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    {isOpen ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
                                </div>
                            </button>

                            {isOpen && (
                                <div className="p-5 pt-0 border-t border-gray-100 bg-gray-50/50">
                                    <div className="bg-white p-4 rounded-xl border border-gray-300 shadow-sm mb-6">
                                        <h4 className="text-md font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                            <PieChartIcon className="h-4 w-4 text-gray-500" />
                                            Portfolio Diversity
                                        </h4>
                                        <div className="h-[200px] w-full">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <PieChart>
                                                    <Pie
                                                        data={allocationData}
                                                        cx="50%"
                                                        cy="50%"
                                                        innerRadius={50}
                                                        outerRadius={70}
                                                        paddingAngle={3}
                                                        dataKey="value"
                                                    >
                                                        {allocationData.map((entry, idx) => (
                                                            <Cell key={`cell-${idx}`} fill={entry.color} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip
                                                        formatter={(value: number) => `$${value.toFixed(2)}`}
                                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                    />
                                                    <Legend
                                                        verticalAlign="bottom"
                                                        height={36}
                                                        formatter={(value) => <span className="text-xs">{value}</span>}
                                                    />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between mb-4">
                                        <h4 className="text-sm font-semibold text-gray-900">Allocation & Multipliers</h4>
                                        {onReset && (
                                            <button
                                                onClick={() => onReset(index)}
                                                className="text-xs flex items-center gap-1 text-blue-600 hover:text-blue-700 bg-blue-50 px-2 py-1 rounded-md hover:bg-blue-100 transition-colors"
                                            >
                                                <RotateCcw className="h-3 w-3" />
                                                Reset to Default
                                            </button>
                                        )}
                                    </div>

                                    <div className="bg-white rounded-lg border border-gray-300 overflow-hidden mb-6">
                                        <table className="min-w-full divide-y divide-gray-200">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/3">Market</th>
                                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Prob.</th>
                                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Allocation ($)</th>
                                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Multiplier (x)</th>
                                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Est. Payout</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-200">
                                                {bundle.bets.map((bet, betIndex) => (
                                                    <tr
                                                        key={betIndex}
                                                        onClick={() => handleMarketClick(betIndex)}
                                                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                                                    >
                                                        <td className="px-4 py-3 text-sm text-gray-900">
                                                            <div className="flex items-center justify-between gap-2 max-w-[300px]">
                                                                <span className="truncate font-medium flex-1 text-blue-600 hover:text-blue-800 hover:underline" title={bet.market.market.question}>
                                                                    {bet.market.market.question}
                                                                </span>
                                                                <span className={`flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${bet.outcome === 'Yes' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                                                    {bet.outcome}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3 text-right whitespace-nowrap text-sm text-gray-600">
                                                            {(bet.current_price * 100).toFixed(0)}%
                                                        </td>
                                                        <td className="px-4 py-3 text-right whitespace-nowrap">
                                                            ${Number(bet.allocation).toFixed(2)}
                                                        </td>
                                                        <td className="px-4 py-3 text-right whitespace-nowrap">
                                                            <span className="text-sm text-gray-900">{Number(bet.payout_multiplier).toFixed(1)}x</span>
                                                        </td>
                                                        <td className="px-4 py-3 text-right whitespace-nowrap text-sm font-medium text-green-600">
                                                            ${Number(bet.potential_payout).toFixed(2)}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <BundleMarketsGrid
                                            bets={bundle.bets}
                                            onUpdateBet={onUpdateBet ? (betIdx, field, val) => onUpdateBet(index, betIdx, field, val) : undefined}
                                            totalBudget={bundle.budget || 100}
                                            expandedCardIndex={expandedCardIndex}
                                            setExpandedCardIndex={setExpandedCardIndex}
                                            bundleIndex={index}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function BundleMarketsGrid({
    bets,
    onUpdateBet,
    totalBudget,
    expandedCardIndex,
    setExpandedCardIndex,
    bundleIndex
}: {
    bets: any[],
    onUpdateBet?: (betIndex: number, field: any, val: number) => void,
    totalBudget: number,
    expandedCardIndex: number | null,
    setExpandedCardIndex: (index: number | null) => void,
    bundleIndex: number
}) {
    return (
        <>
            {bets.map((bet, betIndex) => (
                <div key={bet.market.market.id + betIndex} id={`market-card-${bundleIndex}-${betIndex}`} className={expandedCardIndex === betIndex ? "col-span-1 md:col-span-2" : ""}>
                    <MarketCard
                        bet={bet}
                        isExpanded={expandedCardIndex === betIndex}
                        onToggle={() => {
                            const isOpening = expandedCardIndex !== betIndex;
                            setExpandedCardIndex(isOpening ? betIndex : null);

                            if (isOpening) {
                                setTimeout(() => {
                                    const element = document.getElementById(`market-card-${bundleIndex}-${betIndex}`);
                                    if (element) {
                                        const headerOffset = 150; // Buffer to keep it in the upper half
                                        const elementPosition = element.getBoundingClientRect().top;
                                        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                                        window.scrollTo({
                                            top: offsetPosition,
                                            behavior: "smooth"
                                        });
                                    }
                                }, 100);
                            }
                        }}
                        className=""
                        onUpdateAllocation={onUpdateBet ? (val) => onUpdateBet(betIndex, 'allocation', val) : undefined}
                        totalBudget={totalBudget}
                    />
                </div>
            ))}
        </>
    );
}
