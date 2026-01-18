'use client';

import { Activity, AlertTriangle, DollarSign } from 'lucide-react';
import { PortfolioMetrics, BundleMetrics } from '@/lib/types';

interface Props {
    metrics: PortfolioMetrics;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

function BundleMetricsCard({ bundle, index, onClick }: { bundle: BundleMetrics; index: number; onClick?: () => void }) {
    const riskScore = bundle.risk_score ?? 50;
    const totalMaxPayout = bundle.total_max_payout ?? bundle.max_payout ?? 0;
    const riskColor = riskScore > 70 ? 'text-red-600' : riskScore > 40 ? 'text-orange-500' : 'text-green-600';

    return (
        <div
            onClick={onClick}
            className={`bg-white p-5 rounded-xl border border-gray-300 shadow-sm cursor-pointer transition-all hover:shadow-md hover:border-blue-300 hover:scale-[1.01]`}
        >
            <div className="flex items-center gap-3 mb-4">
                <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <h3 className="text-lg font-semibold text-gray-900">{bundle.theme_name}</h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
                {/* Risk Score */}
                <div className="flex flex-col">
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        Risk Score
                    </span>
                    <span className={`text-lg font-bold ${riskColor}`}>
                        {riskScore.toFixed(0)}/100
                    </span>
                </div>

                {/* Max Payout */}
                <div className="flex flex-col">
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        Max Payout
                    </span>
                    <span className="text-lg font-bold text-gray-900">
                        ${totalMaxPayout.toFixed(0)}
                    </span>
                </div>
            </div>

            {/* Risk Indicator Bar */}
            <div className="mt-4 pt-3 border-t border-gray-300">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>Risk Level</span>
                    <span className={riskColor}>{riskScore > 70 ? 'High' : riskScore > 40 ? 'Moderate' : 'Low'}</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                        className={`h-full rounded-full ${riskScore > 70 ? 'bg-red-500' : riskScore > 40 ? 'bg-orange-400' : 'bg-green-500'}`}
                        style={{ width: `${riskScore}%` }}
                    />
                </div>
            </div>
        </div>
    );
}

export function FinancialMetrics({ metrics, onSelectBundle }: Props & { onSelectBundle?: (index: number) => void }) {
    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <Activity className="h-6 w-6 text-blue-600" />
                    Strategy Comparison
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                    Click a strategy card to view detailed holdings below.
                </p>
            </div>

            {/* Per-Bundle Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {metrics.bundle_metrics.map((bundle, index) => (
                    <BundleMetricsCard
                        key={bundle.theme_name}
                        bundle={bundle}
                        index={index}
                        onClick={() => onSelectBundle?.(index)}
                    />
                ))}
            </div>
        </div>
    );
}
