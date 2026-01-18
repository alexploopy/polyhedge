# PolyHedge: IRL Insurance via Prediction Markets

## Inspiration
We live in an increasingly volatile world. From geopolitical instability and election outcomes to inflation and supply chain disruptions, individuals and businesses are exposed to risks that traditional insurance simply cannot cover. Traditional insurance is slow, bureaucratic, expensive, and often unavailable for "macro" risks.

We successfully identified that prediction markets—specifically Polymarket—offer a liquid, real-time mechanism to hedge these risks. However, navigating hundreds of markets to find the right hedge is complex and intimidating for the average user. We asked: *What if we could build an AI actuary that instantly constructs a personalized insurance policy using prediction markets?*

## What it does
PolyHedge is an AI-powered platform that democratizes access to financial hedging. It allows users to express complex anxieties in plain English (e.g., "I'm worried about rising inflation impacting my savings" or "How do I protect against a specific election outcome?") and instantly receives a diversified portfolio of prediction market positions that act as a hedge.

Key features include:
*   **Semantic Risk Analysis**: Users describe their fears in natural language. PolyHedge analyzes the semantic meaning of these risks to identify the underlying measurable events.
*   **Smart Market Discovery**: Using vector embeddings and semantic search, we scan thousands of active Polymarket markets to find those most relevant to the user's specific concern.
*   **AI Bundle Generation**: Our engine (powered by Anthropic's Claude) acts as a portfolio manager. It doesn't just pick one market; it intelligently correlates multiple markets into "ETF-style" themed bundles (e.g., "Economic Instability Bundle" vs. "Political Policy Bundle").
*   **Quantitative Scoring**: Every market is scored for "Hedge Relevance" and correlation strength, ensuring the user's capital is allocated efficiently to maximize protection.
*   **Risk Coverage Summary**: The user sees exactly which aspects of their risk are covered by the portfolio.

## How we built it
PolyHedge is built on a hybrid AI architecture that combines the reasoning power of large language models with the speed of specialized inference engines.

### AI & Data Pipeline
*   **Reasoning Engine (Anthropic Claude 3.5 Sonnet)**: The core intelligence of the platform. We use Sonnet for:
    *   **Risk Analysis**: Parsing user natural language to extract concrete risk factors and generating enabling context-aware web search queries.
    *   **Complex Scoring**: Determining the *correlation direction* (e.g., realizing that a "No" on a rate cut bet correlates with "Yes" on inflation risk) which requires high-level logic.
    *   **Bundle Generation**: Acting as a portfolio manager to group disparate markets into coherent "ETF-style" themes.
*   **High-Volume Inference (Cerebras + Llama 3.1-8b)**: To handle the massive scale of Polymarket's catalog, we use Cerebras to run Llama 3.1-8b for the initial filtering pass, rapidly discarding irrelevant markets with near-zero latency.
*   **Semantic Search (ChromaDB + all-MiniLM-L6-v2)**: We use **ChromaDB** as our persistent vector store, powered by the efficient `all-MiniLM-L6-v2` embedding model (384 dimensions) to map user fears to market questions in a latent semantic space.

### Backend Infrastructure
*   **Python 3.10+ & FastAPI**: The orchestration layer that ties together the AI services, vector database, and frontend.
*   **Pydantic**: Heavily used for structured data validation, ensuring that the JSON outputs from our AI agents are type-safe and reliable.
*   **NumPy**: Used for vector math calculations and similarity operations.

### Frontend Experience
*   **Next.js 14 & React**: Built with the latest App Router for a performant, server-side rendered application.
*   **Tailwind CSS & Lucide React**: For a modern, clean, and responsive UI that feels like a premium fintech product.
*   **Recharts**: For visualizing risk exposure and portfolio allocations.

## Challenges we ran into
The biggest challenge was "correlation direction." A user might fear "inflation," but a relevant market might be framed as "Will the Fed cut rates?" A "No" outcome on rate cuts might be the correct hedge for inflation. Teaching the AI to understand the *inverse* relationship between market outcomes and user risks was critical. We solved this by implementing a rigorous scoring and logical verification step within our prompt engineering pipeline.

## Accomplishments that we're proud of
We're particularly proud of the "ETF-style" bundling. Instead of overwhelming the user with single bets, we present curated options (like a "Macro Hedge" vs a "Regulatory Hedge"). This transforms a gambling-like interface into a legitimate risk-management tool. We effectively turned Polymarket into a generalized insurance primitive.

## What's next for PolyHedge
*   **Direct On-Chain Execution**: Currently, we recommend the bundle. The next step is integrating wallet connection for one-click execution.
*   **Dynamic Rebalancing**: Monitoring the portfolio over time and alerting the user if the hedge effectiveness drops.
*   **Corporate Treasury Mode**: Expanding from retail users to helping small businesses hedge against specific supply chain risks.
