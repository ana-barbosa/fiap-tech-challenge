from collections import Counter

import streamlit as st

import agent_client
import crm_client
import labels

st.set_page_config(page_title="Propriedades e Demanda", layout="wide")
st.title("Propriedades e Demanda")

try:
    visits = crm_client.list_visits()
    crm_ok = True
except crm_client.CrmUnavailableError:
    visits = []
    crm_ok = False
    st.error("Não foi possível carregar as visitas no momento.")

try:
    lead_stats = agent_client.get_lead_stats()
    agent_ok = True
except agent_client.AgentBackendUnavailableError:
    agent_ok = False
    st.error("Não foi possível carregar os dados de leads no momento.")

if crm_ok:
    st.subheader("Imóveis mais e menos procurados")
    st.caption("Ranking entre os imóveis que já têm ao menos uma visita agendada.")

    if not visits:
        st.info("Nenhuma visita agendada ainda para calcular este ranking.")
    else:
        counts = Counter(v["property_id"] for v in visits)
        most_sought_id, most_count = counts.most_common(1)[0]
        least_sought_id, least_count = counts.most_common()[-1]

        columns = st.columns(2)
        for column, label, property_id, count in (
            (columns[0], "Mais procurado", most_sought_id, most_count),
            (columns[1], "Menos procurado", least_sought_id, least_count),
        ):
            with column:
                st.metric(label, f"Imóvel #{property_id}", f"{count} visita(s)")
                try:
                    listing = crm_client.get_property(property_id)
                except crm_client.CrmUnavailableError:
                    listing = None
                if listing:
                    st.write(f"{labels.property_type_label(listing['property_type'])} em {listing['neighborhood']}, {listing['city']}")

if agent_ok:
    st.subheader("Leads por intenção")
    st.bar_chart(lead_stats["intent_breakdown"])
