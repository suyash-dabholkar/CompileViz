# CompileViz

An interactive web platform for visualizing compiler construction concepts:
a regex-to-automata playground (direct followpos method vs. indirect
Thompson + subset construction), a grammar analysis tool (FIRST/FOLLOW,
LL(1)), DFA minimization, and a full six-phase toy-language compiler with
a live visualization dashboard.

Built for BCSE307P (Compiler Design Lab), VIT Vellore.

## Project status

This repo is at **Milestone 1: project scaffolding**. See `docs/ROADMAP.md`
for the full milestone list and the current progress.

## Repo structure

```
backend/    FastAPI + Python: automata engines, grammar tools, and the
            toy-language compiler pipeline
frontend/   React (Vite) + Tailwind: the dashboard and playground UI
docs/       Architecture notes, roadmap, benchmark results
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be running at `http://localhost:8000`, with interactive docs
at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app will be running at `http://localhost:5173` and will show the
backend connection status on load.

### Running tests

```bash
cd backend
pytest -v
```

CI runs this automatically on every pull request into `main`.

## Contributing workflow

Every feature is built on its own branch and merged into `main` through a
pull request, never pushed directly. See `docs/CONTRIBUTING.md` for the
exact convention.

## License

MIT, see `LICENSE`.
