# VRP Solver

A tool that plans optimal delivery routes for a fleet of vehicles using a Genetic Algorithm, and uses GPT-4o to generate driver instructions and weekly reports from the results.

> For a deeper dive, see [docs/ARCH.md](docs/ARCH.md) for the architecture and [docs/PROD.md](docs/PROD.md) for the product design.

---

## Requirements

- Python 3.11
- An OpenAI API key (only needed for the analysis dashboard)

---

## Setup

Run this once before anything else:

```bash
make setup
source .venv/bin/activate
```

This will create a virtual environment and install all dependencies. It will also create a `.env` file where you need to paste your OpenAI API key:

```
OPENAI_API_KEY=sk-...
```

---

## Running the Planner

The planner takes a problem file and computes the best routes it can find. A window will open showing the routes evolving in real time.

```bash
make plan
```

This runs the default example (`examples/brazil27.toml`). To use a different file:

```bash
make plan INPUT=examples/att48.toml
```

The result is saved automatically to `output/` as a TOML file when the algorithm finishes.

### Included examples

| File | Nodes |
|---|---|
| `examples/estonia9.toml` | 9 |
| `examples/spain15.toml` | 15 |
| `examples/brazil27.toml` | 27 |
| `examples/att48.toml` | 48 |

Start with `estonia9` or `spain15` if you just want to see results quickly.

---

## Running the Analysis Dashboard

Once you have at least one solution in `output/`, launch the dashboard:

```bash
make analysis
```
> Streamlit may ask for your email before the first run, but you don't need to type it, just press enter and the processing will continue

Open `http://localhost:8501` in your browser. You'll find two pages:

- **Driver Instructions** — pick a solution and get turn-by-turn instructions and a map for each vehicle, plus a chat to ask follow-up questions.
- **Weekly Report** — pick multiple solutions to compare and get a consolidated efficiency report.
