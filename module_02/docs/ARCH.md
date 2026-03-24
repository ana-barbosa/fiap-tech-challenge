# VRP Solver with Genetic Algorithm

A **Vehicle Routing Problem (VRP) solver** that uses a Genetic Algorithm to compute optimal delivery routes, with a Streamlit-powered analysis dashboard backed by GPT-4o.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Entry Points                              │
│                                                                  │
│   main.py (CLI)                      app.py (Streamlit UI)       │
│   └── plan --input <file.toml>       └── Driver Instructions     │
│                                          └── Weekly Report       │
└───────────────┬──────────────────────────────┬───────────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│       src/plan.py        │    │        src/analysis.py           │
│  GA orchestration loop   │    │  OpenAI GPT-4o integration       │
│  + Pygame visualization  │    │  - answer_question()             │
│  + TOML output writer    │    │  - generate_driver_instructions()│
└──────────┬───────────────┘    │  - generate_map()                │
           │                    │  - generate_weekly_report()      │
           │                    └──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Core GA Modules                              │
│                                                                  │
│  src/genetic_algorithm.py          src/stopping.py               │
│  ├── generate_random_population()  └── StoppingCondition         │
│  ├── calculate_fitness()               (time / convergence /     │
│  ├── split_route_into_vehicles()        fixed generations)       │
│  ├── order_crossover()                                           │
│  └── mutate()                                                    │
│                                                                  │
│  src/models.py (Pydantic)          src/constants.py              │
│  ├── Location / Depot              └── GA hyper-parameters       │
│  ├── DeliveryNode                      display settings          │
│  ├── VehicleConfig                                               │
│  ├── ProblemInput                  src/draw_functions.py         │
│  ├── Route                         └── Pygame rendering          │
│  └── Solution                                                    │
└──────────────────────────────────────────────────────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────┐          ┌───────────────────────┐
│  examples/*.toml │          │   output/*.toml       │
│  (problem input) │          │   (solution output)   │
└──────────────────┘          └───────────────────────┘
```

### Data Flow

```
examples/problem.toml
        │
        ▼
  ProblemInput (validated by Pydantic)
        │
        ▼
  generate_random_population()
        │
        ▼
  ┌─── GA Loop ────────────────────────────────┐
  │  calculate_fitness() → sort_population()   │
  │  order_crossover() + mutate()              │
  │  StoppingCondition.should_stop?            │
  └────────────────────────────────────────────┘
        │
        ▼
  Solution → output/problem.toml
        │
        ▼
  Streamlit app.py + GPT-4o analysis
```

---

## Folder Structure

```
.
├── main.py                           # CLI entry point (plan subcommand)
├── app.py                            # Streamlit dashboard (analysis subcommand)
├── requirements.txt
├── Makefile
├── .env.example                      # Copy to .env and add OPENAI_API_KEY
│
├── docs/
│   ├── ARCH.md                       # Architecture overview and diagrams
│   └── PROD.md                       # Product description and development decisions
│
├── src/
│   ├── models.py                     # Pydantic data models
│   ├── genetic_algorithm.py          # GA operators (crossover, mutation, fitness)
│   ├── plan.py                       # Main GA loop + Pygame visualization
│   ├── analysis.py                   # GPT-4o powered analysis functions
│   ├── stopping.py                   # Stopping condition (time / convergence / fixed)
│   ├── draw_functions.py             # Pygame rendering utilities
│   └── constants.py                  # Hyper-parameters and display settings
│
├── examples/                         # Included TOML problem files (ready to use)
│   ├── estonia9.toml                 # 9 nodes
│   ├── spain15.toml                  # 15 nodes
│   ├── brazil27.toml                 # 27 nodes
│   ├── att48.toml                    # 48 nodes
│   ├── att48_exceeds_capacity.toml   # validation error: node demand > vehicle capacity
│   └── att48_exceeds_range.toml      # validation error: node unreachable within max range
│
├── output/                           # Generated TOML solutions
│   ├── estonia9.toml
│   ├── spain15.toml
│   ├── brazil27.toml
│   ├── brazil27_mon.toml
│   ├── brazil27_tue.toml
│   ├── brazil27_wed.toml
│   ├── brazil27_thu.toml
│   ├── brazil27_fri.toml
│   └── att48.toml
│
└── tests/
    ├── test_models.py
    ├── test_genetic_algorithm.py
    ├── test_plan.py
    ├── test_analysis.py
    ├── test_stopping.py
    └── test_draw_functions.py
```

---

## Getting Started

### 1. Setup

```bash
make setup
source .venv/bin/activate
```

This creates a virtual environment, installs dependencies, and copies `.env.example` → `.env`.

### 2. Add your OpenAI API key

```
# .env
OPENAI_API_KEY=sk-...
```

> The API key is only required for the Streamlit analysis dashboard. The planner runs without it.

### 3. Run the planner

```bash
# Default problem (brazil27)
make plan

# Custom problem file
make plan INPUT=examples/att48.toml

# Fixed generation cap (overrides convergence/time limit)
make plan INPUT=examples/spain15.toml GENERATIONS=500
```

A Pygame window opens showing the evolving routes in real time. The best solution is saved to `output/<filename>.toml` when the algorithm stops.

### 4. Launch the analysis dashboard

```bash
make analysis
```

> Streamlit may ask for your email before the first run, but you don't need to type it, just press enter and the processing will continue

Opens a Streamlit app at `http://localhost:8501` with two views:

- **Driver Instructions**: select a saved solution, generate per-vehicle turn-by-turn instructions and an embedded map, and ask follow-up questions via the Q&A chat.
- **Weekly Report**: select multiple solutions to compare, generate a consolidated efficiency report, and chat with GPT-4o about the results.

---

## Problem Input Format

Problem files are TOML. Example (`examples/estonia9.toml`):

```toml
[depot]
location = [58.5953, 25.0136]

[vehicles]
count = 3
capacity = 100.0
max_range = 500.0

[[deliveries]]
location = [59.437, 24.7536]
demand = 20.0
priority = "critical"

[[deliveries]]
location = [57.7815, 26.0454]
demand = 35.0
priority = "regular"
```

| Field | Description |
|---|---|
| `depot.location` | `[lat, lon]` of the warehouse / depot |
| `vehicles.count` | Number of available vehicles |
| `vehicles.capacity` | Max cargo units per vehicle |
| `vehicles.max_range` | Max distance per vehicle (in coordinate units × 111 km) |
| `deliveries[].demand` | Cargo units required (must be > 0) |
| `deliveries[].priority` | `"critical"` or `"regular"` (critical nodes are weighted ×2 in the fitness function) |

> This file format was chosen so we can add comments to the content, which is not supported by JSON.

---

## Genetic Algorithm

| Parameter | Default | Location |
|---|---|---|
| Population size | 100 | `constants.py` |
| Mutation probability | 0.5 | `constants.py` |
| Critical priority weight | 2.0 | `constants.py` |
| Max runtime | 600 s | `constants.py` |
| Convergence patience | 1000 generations | `constants.py` |

**Stopping conditions** (in priority order):
1. Fixed `--generations` cap (if provided via CLI)
2. Convergence that stop when no improvement over `patience` generations
3. Hard time limit (`MAX_RUNTIME_SECONDS`) to prevent the service to run forever

---

## Development

```bash
make qa      # Format, lint, and typecheck (ruff + mypy)
make test    # Run tests with coverage report
```

---

## Requirements

- Python 3.11
- See `requirements.txt` for full dependency list