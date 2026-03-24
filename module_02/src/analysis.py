# ruff: noqa: E501
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()

_MODEL = "gpt-4o"
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy .env.example to .env and paste your key there."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def _format_route(route: dict, index: int) -> str:
    lines = [
        f"  Route {index + 1} (Vehicle {route['vehicle_index']}):",
        f"    Total demand : {route['total_demand']}",
        f"    Distance     : {route['total_distance_km']} km",
        f"    Critical stops: {route['critical_stops']}",
        f"    Regular stops : {route['regular_stops']}",
        "    Stops (in order):",
    ]
    for node in route.get("nodes", []):
        lat, lon = node["location"]
        priority_tag = "‼ CRITICAL" if node["priority"] == "critical" else "  regular"
        lines.append(
            f"      Stop {node['stop_number']:>2}: [{lat}, {lon}]"
            f"  demand={node['demand']}  {priority_tag}"
        )
    return "\n".join(lines)


def _solution_summary(solution: dict) -> str:
    depot_lat, depot_lon = solution["depot"]["location"]
    route_blocks = "\n".join(
        _format_route(r, i) for i, r in enumerate(solution["routes"])
    )
    vehicles = solution.get("vehicles", {})
    return (
        f"Depot            : [{depot_lat}, {depot_lon}]\n"
        f"Vehicles used    : {solution['total_vehicles_used']} / {solution['total_vehicles_available']}\n"
        f"Vehicle capacity : {vehicles.get('capacity')} units\n"
        f"Vehicle max range: {vehicles.get('max_range')} km\n"
        f"Demand served    : {solution['total_demand_served']}\n"
        f"Routes           : {len(solution['routes'])}\n"
        f"Best fitness     : {solution['best_fitness']:.4f}\n"
        f"Stopping reason  : {solution['stopping_reason']}\n\n"
        f"Route details:\n{route_blocks}"
    )


def generate_driver_instructions(solution: dict) -> list[str]:
    """
    Call ChatGPT once per route to produce driver instructions for a single VRP
    solution. Each call covers one vehicle, listing stops in order with coordinates,
    demand, priority, and total route distance.

    Parameters:
    - solution (dict): A loaded TOML solution with keys: depot, routes,
                       total_vehicles_used, total_demand_served, best_fitness,
                       stopping_reason.

    Returns:
    list[str]: Markdown-formatted driver instructions, one string per vehicle.
    """
    depot = solution["depot"]
    depot_lat, depot_lon = depot["location"]
    results: list[str] = []

    for route in solution["routes"]:
        route_text = _format_route(route, route["vehicle_index"])

        prompt = f"""You are a logistics coordinator. Fill in the Markdown template below \
for Vehicle {route["vehicle_index"]} using the route data provided.

Rules:
- Replace every <FILL> placeholder with your content. Do not add or remove any headers.
- Under "## Route Summary": one sentence describing the route (number of stops, \
total distance, total demand).
- Under "### Stops": one bullet per stop in delivery order. Each bullet must include \
stop number, coordinates, demand, and priority (mark CRITICAL stops clearly).
- Under "### Priority Notes": call out any CRITICAL stops and advise the driver to \
prioritise them. If there are no critical stops, write "No critical stops on this route."
- Under "### Distance & Load": one line with total distance and total demand.
- Under "### 💡 Suggestions": 2–3 specific improvement ideas based on patterns you \
observe in this route — consider stop ordering, critical stop placement, load balance, \
or long legs between stops. This is your space to reason freely.

Depot: [{depot_lat}, {depot_lon}]

{route_text}

---

## Route Summary
<FILL>

### Stops
<FILL>

### Priority Notes
<FILL>

### Distance & Load
<FILL>

### 💡 Suggestions
<FILL>
"""

        response = _get_client().chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        results.append((response.choices[0].message.content or "").strip())

    return results


def generate_weekly_report(solutions: list[dict]) -> str:
    """
    Call ChatGPT once to produce a comparative weekly efficiency report across
    multiple VRP solutions. The report includes an executive summary, per-solution
    breakdown, comparative analysis, critical-stop overview, and recommendations.

    Parameters:
    - solutions (list[dict]): Loaded TOML solution dicts, one per day or run.

    Returns:
    str: Markdown-formatted weekly report.
    """
    if not solutions:
        return "No solutions provided."

    blocks = []
    for i, sol in enumerate(solutions):
        blocks.append(f"--- Solution {i + 1} ---\n{_solution_summary(sol)}")
    combined = "\n\n".join(blocks)

    prompt = f"""You are a logistics analyst. You have been given {len(solutions)} \
VRP solution(s) from the past week. Write a professional weekly efficiency report.

The report must include:
1. **Executive Summary** — one paragraph highlighting overall performance.
2. **Per-Solution Breakdown** — key metrics (vehicles used, total demand, total \
distance, fitness score, stopping reason) for each solution.
3. **Comparative Analysis** — compare solutions on efficiency (demand per km, \
vehicles utilisation). Identify the best and worst performing runs.
4. **Critical Stops Overview** — total critical stops across all solutions and \
whether any routes carry a high critical-stop load.
5. **Recommendations** — 2–4 actionable suggestions to improve future routes.

Format the entire report in Markdown with clear headers.

VRP Solutions
=============
{combined}
"""

    response = _get_client().chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def generate_map(route: dict, depot: dict) -> str:
    """
    Ask ChatGPT to fill in a strict Leaflet.js HTML template for one vehicle route.
    The template fixes the legend, marker style, polyline, and layout so that every
    map is rendered consistently regardless of which vehicle is being shown.

    Parameters:
    - route (dict): A single route entry from the solution with keys: vehicle_index,
                    nodes, total_distance_km, total_demand.
    - depot (dict): The depot dict from the solution with key: location → [lat, lon].

    Returns:
    str: A self-contained HTML string renderable via st.components.v1.html().
    """
    depot_lat, depot_lon = depot["location"]

    stop_lines = []
    for node in route.get("nodes", []):
        lat, lon = node["location"]
        stop_lines.append(
            f"  Stop {node['stop_number']}: lat={lat} lon={lon} "
            f"priority={node['priority']} demand={node['demand']}"
        )
    stops_text = "\n".join(stop_lines)

    prompt = f"""You are a web developer. Complete the HTML template below by replacing
every <FILL> placeholder with the correct JavaScript values derived from the route data.
Return ONLY the completed HTML — no markdown fences, no explanation, no extra text.

Rules:
- Do not change any HTML, CSS, or JS outside the <FILL> placeholders.
- DEPOT_LAT, DEPOT_LON: floating-point numbers for the depot coordinates.
- STOPS_ARRAY: a JavaScript array of objects, one per stop, in delivery order.
  Each object must have exactly these keys:
    lat, lon, stopNumber, priority ("critical" or "regular"), demand
- VEHICLE_INDEX: integer vehicle index.
- TOTAL_DISTANCE: total route distance in km (number, not string).

Route data
==========
Vehicle index : {route["vehicle_index"]}
Total distance: {route["total_distance_km"]} km
Total demand  : {route["total_demand"]}
Depot         : lat={depot_lat} lon={depot_lon}

Stops (in delivery order):
{stops_text}

HTML template
=============
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {{ margin:0; padding:0; width:100%; height:100%; }}
  .legend {{ background:white; padding:8px 12px; border-radius:6px;
             box-shadow:0 1px 5px rgba(0,0,0,.3); font:13px/1.5 sans-serif; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; margin-bottom:4px; }}
  .dot {{ width:14px; height:14px; border-radius:50%; display:inline-block; }}
  .star {{ font-size:16px; line-height:1; }}
</style>
</head>
<body>
<div id="map"></div>
<script>
  var map = L.map('map');
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors'
  }}).addTo(map);

  var depotLat = <FILL:DEPOT_LAT>;
  var depotLon = <FILL:DEPOT_LON>;
  var stops    = <FILL:STOPS_ARRAY>;
  var vehicleIndex   = <FILL:VEHICLE_INDEX>;
  var totalDistance  = <FILL:TOTAL_DISTANCE>;

  // Depot marker
  var depotIcon = L.divIcon({{
    html: '<span style="font-size:22px;line-height:1;">⭐</span>',
    className: '', iconAnchor: [11, 11]
  }});
  L.marker([depotLat, depotLon], {{icon: depotIcon}})
   .bindPopup('<b>Depot</b> (Vehicle ' + vehicleIndex + ')')
   .addTo(map);

  // Stop markers + polyline coords
  var coords = [[depotLat, depotLon]];
  stops.forEach(function(s) {{
    var color  = s.priority === 'critical' ? '#e63946' : '#1d6fa4';
    var icon   = L.divIcon({{
      html: '<div style="background:' + color + ';color:#fff;border-radius:50%;' +
            'width:26px;height:26px;display:flex;align-items:center;' +
            'justify-content:center;font:bold 12px sans-serif;' +
            'border:2px solid rgba(0,0,0,.25);">' + s.stopNumber + '</div>',
      className: '', iconSize: [26, 26], iconAnchor: [13, 13]
    }});
    L.marker([s.lat, s.lon], {{icon: icon}})
     .bindPopup('<b>Stop ' + s.stopNumber + '</b><br>Priority: ' + s.priority +
                '<br>Demand: ' + s.demand)
     .addTo(map);
    coords.push([s.lat, s.lon]);
  }});
  coords.push([depotLat, depotLon]);

  // Route polyline
  L.polyline(coords, {{color: '#333', weight: 2, opacity: 0.8}}).addTo(map);

  // Fit bounds
  map.fitBounds(L.polyline(coords).getBounds(), {{padding: [24, 24]}});

  // Legend
  var legend = L.control({{position: 'topright'}});
  legend.onAdd = function() {{
    var d = L.DomUtil.create('div', 'legend');
    d.innerHTML =
      '<div class="legend-item"><span class="star">⭐</span> Depot</div>' +
      '<div class="legend-item"><span class="dot" style="background:#e63946"></span> Critical stop</div>' +
      '<div class="legend-item"><span class="dot" style="background:#1d6fa4"></span> Regular stop</div>' +
      '<div style="margin-top:4px;font-size:11px;color:#555;">Vehicle ' + vehicleIndex +
      ' · ' + totalDistance + ' km</div>';
    return d;
  }};
  legend.addTo(map);
</script>
</body>
</html>
"""

    response = _get_client().chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    html = response.choices[0].message.content or ""
    # Strip markdown fences if the model wraps the output anyway
    html = html.strip()
    if html.startswith("```"):
        lines = html.splitlines()
        html = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return html


def answer_question(
    question: str,
    context: dict | list[dict],
    history: list[ChatCompletionMessageParam],
) -> str:
    """
    Answer a follow-up question about one or more VRP solutions, maintaining
    conversation history. The solution data is injected via the system prompt
    to keep it out of the conversation history token budget.

    Parameters:
    - question (str): The user's latest question.
    - context (dict | list[dict]): One solution dict for the Driver Instructions tab,
                                   or a list of solution dicts for the Weekly Report.
    - history (list[ChatCompletionMessageParam]): Prior chat messages in
                            {"role": ..., "content": ...} format.
                            The caller is responsible for capping this list.

    Returns:
    str: The assistant's reply.
    """
    if isinstance(context, dict):
        context_text = _solution_summary(context)
        context_description = "a single VRP solution"
    else:
        if not context:
            context_text = "No solutions loaded yet."
            context_description = "no solutions"
        else:
            parts = [
                f"Solution {i + 1}:\n{_solution_summary(s)}"
                for i, s in enumerate(context)
            ]
            context_text = "\n\n".join(parts)
            context_description = f"{len(context)} VRP solution(s)"

    system_prompt = (
        f"You are a logistics expert assistant. The user is asking questions about "
        f"{context_description}. Answer concisely and accurately based solely on the "
        f"data provided. If the answer cannot be determined from the data, say so.\n\n"
        f"VRP Context\n===========\n{context_text}"
    )

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = _get_client().chat.completions.create(
        model=_MODEL,
        messages=messages,
    )
    return response.choices[0].message.content or ""
