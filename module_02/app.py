from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import tomllib
from dotenv import load_dotenv

from src.analysis import (
    answer_question,
    generate_driver_instructions,
    generate_map,
    generate_weekly_report,
)

load_dotenv()

OUTPUT_DIR = Path("output")
CHAT_HISTORY_CAP = 20
MAP_HEIGHT = 400  # pixels per embedded map


def _discover_solutions() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(OUTPUT_DIR.glob("*.toml"))


def _load_solution(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _render_chat(chat_key: str, context: dict | list[dict]) -> None:
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    st.markdown("#### 💬 Q&A")

    with st.container(height=350):
        if not st.session_state[chat_key]:
            st.caption("No messages yet. Ask a question below.")
        for message in st.session_state[chat_key]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    user_input = st.chat_input("Ask a question...", key=f"{chat_key}_input")
    if user_input:
        st.session_state[chat_key].append({"role": "user", "content": user_input})

        # Pass history excluding the message we just appended
        history_to_send = st.session_state[chat_key][:-1]

        try:
            reply = answer_question(user_input, context, history_to_send)
        except Exception as exc:
            reply = f"⚠️ Error contacting ChatGPT: {exc}"

        st.session_state[chat_key].append({"role": "assistant", "content": reply})

        if len(st.session_state[chat_key]) > CHAT_HISTORY_CAP:
            st.session_state[chat_key] = st.session_state[chat_key][-CHAT_HISTORY_CAP:]

        st.rerun()


def _render_driver_instructions_tab(solutions: list[Path]) -> None:
    if not solutions:
        st.warning("No solutions found in output/. Run `make plan` first.")
        return

    selected = st.selectbox(
        "Select a solution",
        options=solutions,
        format_func=lambda p: p.name,
        key="di_selectbox",
    )

    solution = _load_solution(selected)

    col1, col2, col3 = st.columns(3)
    col1.metric("Vehicles used", solution["total_vehicles_used"])
    col2.metric("Total demand served", solution["total_demand_served"])
    col3.metric("Routes", len(solution["routes"]))

    # Clear stored results when the selected solution changes
    if st.session_state.get("di_last_selected") != str(selected):
        st.session_state.pop("di_instructions", None)
        st.session_state.pop("di_maps", None)
        st.session_state["di_last_selected"] = str(selected)

    if st.button("Generate Instructions", key="di_generate", type="primary"):
        n_routes = len(solution["routes"])
        with st.spinner(
            f"Generating driver instructions and {n_routes} map(s) "
            f"— this may take a moment…"
        ):
            # One instruction string + one map per route, interleaved
            instructions: list[str] = []
            maps: list[str] = []
            depot = solution["depot"]

            try:
                instructions = generate_driver_instructions(solution)
            except Exception as exc:
                instructions = [f"⚠️ Error generating instructions: {exc}"] * n_routes

            for route in solution["routes"]:
                try:
                    maps.append(generate_map(route, depot))
                except Exception as exc:
                    maps.append(f"<p>⚠️ Error generating map: {exc}</p>")

            st.session_state["di_instructions"] = instructions
            st.session_state["di_maps"] = maps

    st.divider()

    report_col, chat_col = st.columns([0.65, 0.35])

    with report_col:
        instructions = st.session_state.get("di_instructions", [])
        stored_maps: list[str] = st.session_state.get("di_maps", [])

        if not instructions:
            st.info("Driver instructions will appear here.")
        else:
            for route, instruction, html in zip(
                solution["routes"], instructions, stored_maps
            ):
                st.markdown(f"### 🚛 Vehicle {route['vehicle_index']}")
                st.markdown(instruction)
                components.html(html, height=MAP_HEIGHT, scrolling=False)
                st.divider()

    with chat_col:
        _render_chat("di_chat", context=solution)


def _render_weekly_report_tab(solutions: list[Path]) -> None:
    if not solutions:
        st.warning("No solutions found in output/. Run `make plan` first.")
        return

    selected = st.multiselect(
        "Select solutions to compare",
        options=solutions,
        format_func=lambda p: p.name,
        key="wr_multiselect",
    )

    col1, col2 = st.columns(2)
    col1.metric("Solutions selected", len(selected))
    col2.metric("Total files available", len(solutions))

    if st.button("Generate Report", key="wr_generate", type="primary"):
        if not selected:
            st.warning("Select at least one solution before generating a report.")
        else:
            with st.spinner("Generating weekly report…"):
                loaded = [_load_solution(p) for p in selected]
                try:
                    st.session_state["wr_report"] = generate_weekly_report(loaded)
                except Exception as exc:
                    st.session_state["wr_report"] = f"⚠️ Error contacting ChatGPT: {exc}"
                st.rerun()

    st.divider()

    report_col, chat_col = st.columns([0.65, 0.35])

    with report_col:
        report_text = st.session_state.get("wr_report")
        if report_text:
            st.markdown(report_text)
        elif not selected:
            st.info("Select one or more solutions above to generate a weekly report.")
        else:
            st.info("Weekly efficiency report will appear here.")

    with chat_col:
        loaded_for_chat = [_load_solution(p) for p in selected] if selected else []
        _render_chat("wr_chat", context=loaded_for_chat)


def main() -> None:
    st.set_page_config(page_title="VRP Analysis", layout="wide")

    st.sidebar.title("VRP Analysis")
    page = st.sidebar.radio(
        "Navigation",
        ["Driver Instructions", "Weekly Report"],
        label_visibility="collapsed",
    )

    solutions = _discover_solutions()

    if page == "Driver Instructions":
        st.title("🚚 Driver Instructions")
        _render_driver_instructions_tab(solutions)
    elif page == "Weekly Report":
        st.title("📊 Weekly Report")
        _render_weekly_report_tab(solutions)


if __name__ == "__main__":
    main()
