# PolyHedge

IRL Insurance via Polymarket - hedge real-life risks with prediction markets.

## Installation

```bash
# Install backend dependencies
pip install -e .

# Install frontend dependencies
cd web
npm install
cd ..

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running the Backend

```bash
uvicorn polyhedge.api.main:app --reload --host 0.0.0.0 --port 8000
```

API available at http://localhost:8000

## Running the Frontend

```bash
cd web
npm run dev
```

Web app available at http://localhost:3000
