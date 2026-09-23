import streamlit as st

import config
from api_client import CrmUnavailableError, list_properties, photo_url
from cities import CITIES

st.set_page_config(page_title="Imobiliária Vale do Paraíba", layout="wide")
st.title("Encontre seu imóvel no Vale do Paraíba")

st.markdown(
    """
    <style>
    .listing-description {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "offset" not in st.session_state:
    st.session_state["offset"] = 0

if "filter_reset_nonce" not in st.session_state:
    st.session_state["filter_reset_nonce"] = 0


def clear_filters():
    st.session_state["filter_reset_nonce"] += 1
    st.session_state["offset"] = 0


with st.sidebar:
    st.header("Filtros")
    nonce = st.session_state["filter_reset_nonce"]
    listing_type_label = st.radio(
        "Quero", ["Comprar", "Alugar"], horizontal=True, key=f"filter_listing_type_{nonce}"
    )
    listing_type = "sale" if listing_type_label == "Comprar" else "rent"

    city = st.selectbox("Cidade", ["Todas"] + sorted(CITIES.keys()), key=f"filter_city_{nonce}")
    property_type_label = st.selectbox(
        "Tipo", ["Todos", "Apartamento", "Casa"], key=f"filter_property_type_{nonce}"
    )
    property_type = {"Todos": None, "Apartamento": "apartment", "Casa": "house"}[property_type_label]

    price_max_default = 1_500_000 if listing_type == "sale" else 15_000
    price_range = st.slider(
        "Faixa de preço (R$)",
        0,
        price_max_default,
        (0, price_max_default),
        key=f"filter_price_range_{nonce}",
    )

    rooms_label = st.selectbox(
        "Quartos", ["Qualquer", "1+", "2+", "3+", "4+"], key=f"filter_rooms_{nonce}"
    )
    rooms = None if rooms_label == "Qualquer" else int(rooms_label.rstrip("+"))

    sort_label = st.selectbox(
        "Ordenar por", ["Mais recentes", "Menor preço", "Maior preço"], key=f"filter_sort_{nonce}"
    )
    sort_by, order = {
        "Mais recentes": ("created_at", "desc"),
        "Menor preço": ("price", "asc"),
        "Maior preço": ("price", "desc"),
    }[sort_label]

    st.button("Buscar", type="primary", width="stretch")
    st.button("Limpar", width="stretch", on_click=clear_filters)

filters_signature = (listing_type, city, property_type, price_range, rooms, sort_by, order)
if st.session_state.get("last_filters") != filters_signature:
    st.session_state["offset"] = 0
st.session_state["last_filters"] = filters_signature

try:
    listings = list_properties(
        listing_type=listing_type,
        city=None if city == "Todas" else city,
        property_type=property_type,
        min_price=price_range[0],
        max_price=price_range[1],
        rooms=rooms,
        sort_by=sort_by,
        order=order,
        offset=st.session_state["offset"],
        limit=config.PAGE_SIZE,
    )
except CrmUnavailableError:
    listings = None
    st.error("Não foi possível carregar os imóveis no momento. Tente novamente em instantes.")

if listings is not None:
    if not listings:
        st.info("Nenhum imóvel encontrado para os filtros selecionados.")

    columns = st.columns(3)
    for index, listing in enumerate(listings):
        with columns[index % 3]:
            if listing["photos"]:
                st.image(photo_url(listing["photos"][0]), width="stretch")
            price_label = (
                f"R$ {listing['price']:,.0f}".replace(",", ".")
                if listing["listing_type"] == "sale"
                else f"R$ {listing['price']:,.0f}/mês".replace(",", ".")
            )
            st.subheader(price_label)
            st.write(f"{listing['neighborhood']}, {listing['city']}")
            st.caption(f"{listing['rooms']} quartos · {listing['area_sqm']:.0f} m²")
            st.markdown(
                f'<div class="listing-description">{listing["description"]}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Ver detalhes", key=f"details_{listing['id']}", width="stretch"):
                st.session_state["selected_listing_id"] = listing["id"]
                st.switch_page("pages/1_Detalhes_do_Imóvel.py")

    pagination_cols = st.columns([3, 1, 1, 3])
    with pagination_cols[1]:
        if st.button("Anterior", disabled=st.session_state["offset"] == 0, width="stretch"):
            st.session_state["offset"] = max(0, st.session_state["offset"] - config.PAGE_SIZE)
            st.rerun()
    with pagination_cols[2]:
        if st.button("Próxima", disabled=len(listings) < config.PAGE_SIZE, width="stretch"):
            st.session_state["offset"] += config.PAGE_SIZE
            st.rerun()
