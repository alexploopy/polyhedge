'use client';

import { Check, Loader2 } from 'lucide-react';

interface Props {
  steps: string[];
}

export function ProgressTracker({ steps }: Props) {
  if (steps.length === 0) return null;

  return (
    <div className="mt-6 bg-gray-50 rounded-lg p-6">
      <h3 className="text-sm font-medium text-gray-700 mb-4">Progress</h3>
      <div className="space-y-3">
        {steps.map((step, idx) => {
          const isLast = idx === steps.length - 1;

          return (
            <div key={idx} className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                {isLast ? (
                  <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                ) : (
                  <Check className="h-5 w-5 text-green-600" />
                )}
              </div>
              <p className={`text-sm ${isLast ? 'text-blue-700 font-medium' : 'text-gray-600'}`}>
                {step}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
