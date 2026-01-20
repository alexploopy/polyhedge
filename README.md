# PolyHedge

Insurance for anything

https://devpost.com/software/00000000

## Installation

```bash
# Install backend dependencies
pip install -e .

# Install frontend dependencies
cd web
npm install
cd ..

# Set your API keys, see .env.example
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
