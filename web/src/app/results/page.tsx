'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RotateCcw } from 'lucide-react';
import { FinancialMetrics } from '@/components/FinancialMetrics';
import { BundleViewer } from '@/components/BundleViewer';
import { HedgeResponse, PortfolioMetrics } from '@/lib/types';

export default function ResultsPage() {
    const [data, setData] = useState<HedgeResponse | null>(null);
    const [concern, setConcern] = useState<string>('');
    const [openBundleIndex, setOpenBundleIndex] = useState<number | null>(0);

    // Interactive State
    const [originalBundles, setOriginalBundles] = useState<any[]>([]); // For Reset
    const [currentBundles, setCurrentBundles] = useState<any[]>([]);
    const [metrics, setMetrics] = useState<PortfolioMetrics | null>(null);
    const [budgetInput, setBudgetInput] = useState<string>('');

    const handleSelectBundle = (index: number) => {
        setOpenBundleIndex(index);
        setTimeout(() => {
            const element = document.getElementById(`bundle-${index}`);
            if (element) {
                const headerOffset = 100; // Buffer to keep it in view comfortably
                const elementPosition = element.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth"
                });
            }
        }, 100);
    };

    const handleToggleBundle = (index: number) => {
        setOpenBundleIndex(openBundleIndex === index ? null : index);
    };

    const recalculatemetrics = async (bundles: any[]) => {
        const { calculatePortfolioMetrics } = await import('@/lib/metrics');
        const newMetrics = calculatePortfolioMetrics(bundles);
        setMetrics(newMetrics);
        setCurrentBundles(bundles);
    };

    // Reset Handler
    const handleReset = (bundleIndex: number) => {
        if (!originalBundles.length) return;

        const updatedBundles = [...currentBundles];
        // Deep copy original to restore
        updatedBundles[bundleIndex] = JSON.parse(JSON.stringify(originalBundles[bundleIndex]));

        // If current total budget is different from original, we might want to preserve the CURRENT budget setting?
        // User asked for "Reset". Usually means reset composition. 
        // If user changed Budget from 100 -> 200, then Reset... 
        // Let's assume Reset restores the Original generated composition AND allocations (so budget resets too if it was changed).
        // OR we can scale the original composition to the CURRENT budget.
        // Let's scale original composition to current budget for better UX.

        const currentBudget = updatedBundles[bundleIndex].budget || 100; // Actually this is the reverted budget
        // Wait, if we revert to original, we get original budget. 
        // Let's stick to simple revert first. If they want to change budget back, they can.

        // Actually, let's keep the *current global budget preference* if possible.
        const intendedBudget = parseFloat(budgetInput) || 100;
        const originalBudget = updatedBundles[bundleIndex].budget || 100;

        if (intendedBudget !== originalBudget && originalBudget > 0) {
            const scale = intendedBudget / originalBudget;
            updatedBundles[bundleIndex].budget = intendedBudget;
            updatedBundles[bundleIndex].bets = updatedBundles[bundleIndex].bets.map((b: any) => ({
                ...b,
                allocation: b.allocation * scale,
                potential_payout: b.potential_payout * scale
            }));
        }

        recalculatemetrics(updatedBundles);
    };

    // Budget Update
    const handleUpdateBudget = (val: string) => {
        setBudgetInput(val);
        const newBudget = parseFloat(val);

        if (!currentBundles.length || isNaN(newBudget) || newBudget <= 0) return;

        const oldBudget = currentBundles[0].budget || 100;
        if (oldBudget <= 0) return;

        const scale = newBudget / oldBudget;

        const updatedBundles = currentBundles.map(bundle => ({
            ...bundle,
            budget: newBudget,
            bets: bundle.bets.map((bet: any) => ({
                ...bet,
                allocation: bet.allocation * scale,
                potential_payout: bet.potential_payout * scale
            }))
        }));

        recalculatemetrics(updatedBundles);
    };

    // Proportional Rebalancing Bet Update
    const handleUpdateBet = (bundleIndex: number, betIndex: number, field: 'allocation' | 'multiplier', value: number) => {
        const updatedBundles = [...currentBundles];
        const bundle = { ...updatedBundles[bundleIndex] };
        const bets = [...bundle.bets];
        const targetBet = bets[betIndex];

        if (field === 'allocation') {
            // Proportional Rebalancing Logic
            // value is the NEW allocation for this bet
            // We must adjust OTHER bets so Sum(Allocations) == TotalBudget

            const totalBudget = bundle.budget || 100;
            const newAllocation = Math.min(Math.max(value, 0), totalBudget); // Clamp

            // Calculate remainder to distribute
            const remainder = totalBudget - newAllocation;

            // Get sum of current allocations of ALL OTHER bets
            const otherBets = bets.filter((_, idx) => idx !== betIndex);
            const currentSumOthers = otherBets.reduce((sum, b) => sum + b.allocation, 0);

            // Distribute remainder
            bets.forEach((bet, idx) => {
                if (idx === betIndex) {
                    bet.allocation = newAllocation;
                    bet.potential_payout = newAllocation * bet.payout_multiplier;
                } else {
                    let share = 0;
                    if (currentSumOthers > 0) {
                        // Proportional to current share
                        share = bet.allocation / currentSumOthers;
                    } else {
                        // If all others were 0, distribute equally? Or keep 0?
                        // If we are reducing target from 100% to 50%, and others are 0, they should implicitly gain.
                        // But if they are 0, we don't know their weight.
                        // Fallback to equal weight if sum is 0
                        share = 1 / otherBets.length;
                    }

                    const newAlloc = remainder * share;
                    bet.allocation = newAlloc;
                    bet.potential_payout = newAlloc * bet.payout_multiplier;
                }
            });

            bundle.bets = bets;
            bundle.total_allocated = totalBudget; // Should match matches

        } else if (field === 'multiplier') {
            // Just update value, no rebalancing needed (locked/read-only anyway per user)
            targetBet.payout_multiplier = value;
            targetBet.potential_payout = targetBet.allocation * value;
            bets[betIndex] = targetBet;
            bundle.bets = bets;
        }

        updatedBundles[bundleIndex] = bundle;
        recalculatemetrics(updatedBundles);
    };

    useEffect(() => {
        const storedData = sessionStorage.getItem('hedgeResults');
        const storedConcern = sessionStorage.getItem('hedgeConcern');

        if (storedData) {
            try {
                const parsed = JSON.parse(storedData);
                setData(parsed);
                // Store deep copy for reset
                setOriginalBundles(JSON.parse(JSON.stringify(parsed.bundles)));
                setCurrentBundles(parsed.bundles);
                setMetrics(parsed.metrics);
                setBudgetInput(parsed.metrics.total_budget?.toFixed(0) || '100');
            } catch (e) {
                console.error('Failed to parse hedge results', e);
            }
        }

        if (storedConcern) {
            setConcern(storedConcern);
        }
    }, []);

    if (!currentBundles.length || !metrics) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading your strategy...</p>
                </div>
            </div>
        );
    }

    return (
        <main className="min-h-screen bg-gray-50 pb-20">
            {/* Header / Nav */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <Link
                            href="/"
                            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium transition-colors"
                        >
                            <ArrowLeft className="h-5 w-5" />
                            Back to Search
                        </Link>

                        <div className="flex items-center gap-3 bg-gray-50 px-4 py-2 rounded-lg border border-gray-200">
                            <span className="text-sm font-medium text-gray-700">Total Budget:</span>
                            <div className="relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">$</span>
                                <input
                                    type="number"
                                    value={budgetInput}
                                    onChange={(e) => handleUpdateBudget(e.target.value)}
                                    className="w-24 pl-6 pr-2 py-1 border border-gray-300 rounded text-right focus:ring-blue-500 focus:border-blue-500 font-mono"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="mb-8">
                    <div className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-sm font-semibold rounded-full mb-3">
                        Hedge Strategy For
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-4">
                        {concern || "Your Risk Profile"}
                    </h1>
                </div>

                <div className="mb-12">
                    <FinancialMetrics
                        metrics={metrics}
                        onSelectBundle={handleSelectBundle}
                    />
                </div>

                <div>
                    <BundleViewer
                        bundles={currentBundles}
                        metrics={metrics.bundle_metrics}
                        activeIndex={openBundleIndex}
                        onToggle={handleToggleBundle}
                        onUpdateBet={handleUpdateBet}
                        onReset={handleReset}
                    />
                </div>
            </div>
        </main>
    );
}
