# Product Design of VRP Solver

## 1. Genetic Algorithm Implementation

The solver treats the VRP as a single-objective optimization problem: minimize total weighted travel distance across all routes.

**Representation.** Each individual in the population is a flat ordered list of all delivery nodes. Vehicle splitting is not encoded in the chromosome, it is derived deterministically at evaluation time via `split_route_into_vehicles()`. This keeps the search space manageable and avoids invalid chromosomes.

**Initialization.** The population seeds one individual using a Nearest Neighbor heuristic to provide a strong starting point, then fills the remainder with random permutations to preserve diversity.

**Selection.** Parents are chosen via fitness-proportionate selection (roulette wheel), where each individual's selection probability is inversely proportional to its fitness score. This naturally favors shorter routes while still allowing weaker individuals to contribute genetic material.

**Crossover.** Order Crossover (OX) is used: a random segment is copied from parent 1, and the remaining nodes are filled in the order they appear in parent 2. OX preserves relative node ordering, which is critical for route quality.

**Mutation.** With probability 0.5, a random contiguous segment of the route (up to 20% of its length) is reversed. This inversion operator makes small, local improvements without disrupting the rest of the route.

**Elitism.** The best individual from each generation is carried forward unchanged, ensuring fitness never regresses.

---

## 2. Constraint Handling

### Delivery Priority
Nodes are tagged as `critical` or `regular`. The fitness function applies a weight of ×2 to legs leading into critical nodes. This penalizes solutions that place critical stops far from the depot or at the end of long routes, naturally pushing the GA to visit them earlier and group them together, without imposing hard ordering constraints.

### Load Capacity
`split_route_into_vehicles()` greedily opens a new vehicle sub-route whenever adding the next node would exceed the vehicle's capacity. The total demand across all deliveries is validated at load time against the fleet's aggregate capacity, rejecting infeasible problems before the GA runs.

### Vehicle Range
The same splitting function also tracks cumulative distance and ensures every vehicle can always return to the depot within its maximum range. Each potential leg is evaluated together with the return distance before the node is assigned. Problems where any single node is unreachable on a round trip are rejected at validation time.

### Multiple Vehicles
The fleet is homogeneous (all vehicles share the same capacity and range). The chromosome remains a single flat permutation, and the number of vehicles actually used emerges from the splitting step, the GA is free to find solutions that use fewer vehicles than available if that produces a shorter total distance.

### Depot as Start and End Point (extra restriction)
Every vehicle sub-route must begin and end at the depot. This is enforced at two levels: `split_route_into_vehicles()` always resets the current position back to the depot when opening a new sub-route, and `Route.compute_route_stats()` always includes the final return leg to the depot when calculating total distance. As a result, the fitness function naturally penalizes solutions where vehicles end up far from the depot, and all saved solutions carry accurate round-trip distances.

---

## 3. LLM Integration

Once the GA produces a solution and saves it to `output/*.toml`, the Streamlit dashboard exposes two GPT-4o powered workflows.

**Driver Instructions.** For each vehicle sub-route, the solution is serialized into a structured text summary (depot coordinates, ordered stops with demand and priority tags, total distance) and sent to GPT-4o with a prompt requesting concise, human-readable turn-by-turn instructions. An interactive Folium map is generated in parallel and embedded alongside the instructions.

**Weekly Report.** Multiple solution files can be selected and compared. Their summaries are batched into a single prompt asking GPT-4o to produce a consolidated efficiency report covering vehicle utilization, demand served, distance totals, and operational recommendations.

**Conversational Q&A.** Both views expose a chat interface where the loaded solution (or set of solutions) is injected as context into every message, allowing users to ask follow-up questions. Conversation history is maintained in session state and capped at 20 messages to stay within the model's context window.

---

## 4. Performance Comparison

Rather than comparing against external solvers, this section discusses the GA design choices made at each stage of the algorithm and the alternatives that were considered.

### Initialization
The population is seeded with one Nearest Neighbor (NN) solution and the remainder filled with random permutations. A common alternative is the **Convex Hull heuristic**, which builds an initial route by ordering nodes along the outer boundary of the delivery area and inserting interior nodes. This tends to produce better starting routes than NN for classic TSP. However, the depot-as-start-and-end constraint complicated the hull construction: the depot is not necessarily on the convex hull, so anchoring the route correctly required additional logic that was not straightforward to implement reliably. The NN + random hybrid was chosen instead, as it still provides one strong seed while preserving population diversity.

### Selection
Fitness-proportionate selection (roulette wheel) was used, where selection probability is inversely proportional to fitness. The main alternative is **tournament selection**, where a small subset of individuals compete and the best is selected. Tournament selection is less sensitive to fitness scaling issues and tends to maintain diversity better in later generations. Roulette wheel was preferred here for its simplicity and because the fitness values (total weighted distance) are naturally positive and well-scaled, which avoids the degenerate cases where roulette wheel underperforms.

### Crossover
Order Crossover (OX) was chosen because it preserves the relative ordering of nodes, which is semantically meaningful for routing problems. The main alternative is **Partially Mapped Crossover (PMX)**, which preserves absolute position rather than relative order. For VRP, relative order tends to matter more than absolute position, a good route is defined by the sequence of visits, not where each node sits in the array, making OX the more natural fit.

### Mutation
A segment inversion (2-opt style reversal) was used: a random contiguous segment of the route is reversed. The alternative most commonly used alongside OX is **swap mutation**, which exchanges two randomly chosen nodes. Inversion was preferred because reversing a segment is equivalent to removing two crossing edges in the route graph, which is a well-known local improvement operation in routing. Swap mutation makes more disruptive, less structured changes and tends to perform worse in combination with OX.