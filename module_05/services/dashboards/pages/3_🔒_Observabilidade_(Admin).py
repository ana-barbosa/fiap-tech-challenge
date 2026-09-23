import streamlit as st

import agent_client

st.set_page_config(page_title="Observabilidade (Admin)", page_icon="🔒", layout="wide")

# Visual cue only, not access control - DECISIONS.md's Security section explicitly excludes
# dashboard access control from scope. This page shows internal engineering metrics (latency,
# token cost, raw LLM call counts), a different audience than the company/broker pages
# elsewhere in this app, hence the distinct 🔒 sidebar icon (filename-driven) and this banner.
st.warning(
    "🔒 Área administrativa - métricas técnicas internas de engenharia (latência, custo de "
    "tokens, chamadas de LLM). Não é uma página voltada a corretores ou clientes. Sem "
    "controle de acesso nesta versão (POC)."
)

st.title("Observabilidade (Admin)")

try:
    observability_stats = agent_client.get_observability_stats()
    agent_ok = True
except agent_client.AgentBackendUnavailableError:
    agent_ok = False
    st.error("Não foi possível carregar as métricas de observabilidade no momento.")

if agent_ok:
    total_tokens = observability_stats["total_input_tokens"] + observability_stats["total_output_tokens"]

    top_row = st.columns(3)
    top_row[0].metric("Chamadas de LLM", observability_stats["call_count"])
    top_row[1].metric("Latência média", f"{observability_stats['avg_latency_ms']:.0f} ms")
    top_row[2].metric("Latência p95", f"{observability_stats['p95_latency_ms']:.0f} ms")

    bottom_row = st.columns(3)
    bottom_row[0].metric("Tokens consumidos", f"{total_tokens:,}".replace(",", "."))
    bottom_row[1].metric("Taxa de erro", f"{observability_stats['error_rate'] * 100:.1f}%")
    bottom_row[2].metric("Injeção de prompt suspeita", observability_stats["injection_suspected_count"])

    st.subheader("Chamadas recentes")
    recent_calls = observability_stats["recent_calls"]
    if not recent_calls:
        st.info("Nenhuma chamada de LLM registrada ainda.")
    else:
        st.dataframe(recent_calls, width="stretch")
