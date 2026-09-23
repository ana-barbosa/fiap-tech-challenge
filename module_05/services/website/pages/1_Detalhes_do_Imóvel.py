import streamlit as st

from api_client import CrmUnavailableError, get_property, photo_url
from labels import property_type_label, status_label

st.set_page_config(page_title="Detalhes do imóvel", layout="wide")

listing_id = st.session_state.get("selected_listing_id") or st.query_params.get("listing_id")

if listing_id is None:
    st.info("Selecione um imóvel na página inicial para ver os detalhes.")
    st.stop()

try:
    listing = get_property(listing_id)
except CrmUnavailableError:
    st.error("Não foi possível carregar este imóvel no momento. Tente novamente em instantes.")
    st.stop()

if listing is None:
    st.warning("Este imóvel não está mais disponível.")
    st.stop()

st.title(f"{property_type_label(listing['property_type'])} em {listing['neighborhood']}, {listing['city']}")
st.caption(f"ID do imóvel: {listing['id']}")

if listing["photos"]:
    columns = st.columns(min(3, len(listing["photos"])))
    for index, relative_path in enumerate(listing["photos"]):
        columns[index % len(columns)].image(photo_url(relative_path), width="stretch")

price_label = (
    f"R$ {listing['price']:,.0f}".replace(",", ".")
    if listing["listing_type"] == "sale"
    else f"R$ {listing['price']:,.0f}/mês".replace(",", ".")
)
st.header(price_label)

info_cols = st.columns(4)
info_cols[0].metric("Quartos", listing["rooms"])
info_cols[1].metric("Área", f"{listing['area_sqm']:.0f} m²")
info_cols[2].metric("Tipo", "Venda" if listing["listing_type"] == "sale" else "Aluguel")
info_cols[3].metric("Status", status_label(listing["status"]))

if listing["listing_type"] == "rent":
    rent_cols = st.columns(2)
    rent_cols[0].write(f"**Prazo de locação:** {listing['lease_duration_months']} meses")
    rent_cols[1].write(f"**Disponível a partir de:** {listing['available_from']}")

st.subheader("Descrição")
st.write(listing["description"])

if st.button("Voltar para a busca"):
    st.switch_page("Buscar_Imóveis.py")
