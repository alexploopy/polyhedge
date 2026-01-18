'use client';

import { ChatInterface } from '@/components/ChatInterface';

export default function Home() {
    return (
        <main className="min-h-screen flex flex-col bg-white">
            <div className="flex-1 w-full">
                <ChatInterface />
            </div>

            <footer className="py-8 text-center text-blue-600 text-sm">
                <p>Powered by Polymarket • AI Agentic Hedging</p>
            </footer>
        </main>
    );
}
