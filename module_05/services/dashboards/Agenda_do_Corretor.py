from datetime import datetime

import streamlit as st

import agent_client
import crm_client
import labels

st.set_page_config(page_title="Agenda do Corretor", layout="wide")
st.title("Agenda do Corretor")

try:
    visits = crm_client.list_visits()
except crm_client.CrmUnavailableError:
    visits = None
    st.error("Não foi possível carregar as visitas agendadas no momento. Tente novamente em instantes.")


def _render_visit(visit: dict) -> None:
    try:
        listing = crm_client.get_property(visit["property_id"])
    except crm_client.CrmUnavailableError:
        listing = None

    label = f"{visit['confirmed_datetime']} - {visit['lead_name']}"
    if listing:
        label += f" - {labels.property_type_label(listing['property_type'])} em {listing['neighborhood']}, {listing['city']}"

    with st.expander(label):
        columns = st.columns([1, 2])
        with columns[0]:
            if listing and listing["photos"]:
                st.image(crm_client.photo_url(listing["photos"][0]), width="stretch")
        with columns[1]:
            if listing:
                price_label = (
                    f"R$ {listing['price']:,.0f}".replace(",", ".")
                    if listing["listing_type"] == "sale"
                    else f"R$ {listing['price']:,.0f}/mês".replace(",", ".")
                )
                st.write(f"**{price_label}** · {listing['rooms']} quartos · {listing['area_sqm']:.0f} m²")
            else:
                st.caption("Imóvel não encontrado.")
            st.write(f"**Cliente:** {visit['lead_name']} ({visit['lead_contact']})")

        st.markdown("**Resumo para o corretor**")
        try:
            st.write(agent_client.get_summary(visit["conversation_id"]))
        except agent_client.AgentBackendUnavailableError:
            st.caption("Não foi possível carregar o resumo no momento.")


if visits is not None:
    if not visits:
        st.info("Nenhuma visita agendada ainda.")

    now = datetime.now().isoformat()
    upcoming = sorted(
        (v for v in visits if v["confirmed_datetime"] >= now), key=lambda v: v["confirmed_datetime"]
    )
    past = sorted(
        (v for v in visits if v["confirmed_datetime"] < now), key=lambda v: v["confirmed_datetime"], reverse=True
    )

    st.subheader("Próximas visitas")
    if not upcoming:
        st.caption("Nenhuma visita futura agendada.")
    for visit in upcoming:
        _render_visit(visit)

    st.subheader("Visitas passadas")
    if not past:
        st.caption("Nenhuma visita passada.")
    for visit in past:
        _render_visit(visit)
