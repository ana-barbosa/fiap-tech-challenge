from datetime import datetime, timedelta

import streamlit as st

import agent_client
import config
import crm_client

st.set_page_config(page_title="Visão Geral", layout="wide")
st.title("Visão Geral da Imobiliária")

try:
    rentals_available = crm_client.list_properties(
        listing_type="rent", status="available", limit=config.CATALOG_FETCH_LIMIT
    )
    sales_available = crm_client.list_properties(
        listing_type="sale", status="available", limit=config.CATALOG_FETCH_LIMIT
    )
    sold = crm_client.list_properties(status="sold", limit=config.CATALOG_FETCH_LIMIT)
    rented = crm_client.list_properties(status="rented", limit=config.CATALOG_FETCH_LIMIT)
    visits = crm_client.list_visits()
    crm_ok = True
except crm_client.CrmUnavailableError:
    crm_ok = False
    st.error("Não foi possível carregar os dados do CRM no momento.")

try:
    lead_stats = agent_client.get_lead_stats()
    agent_ok = True
except agent_client.AgentBackendUnavailableError:
    agent_ok = False
    st.error("Não foi possível carregar os dados de leads no momento.")

if crm_ok and agent_ok:
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    closed_deals = [listing for listing in sold + rented if listing["updated_at"] >= thirty_days_ago]

    top_row = st.columns(3)
    top_row[0].metric("Clientes", lead_stats["total_clients"])
    top_row[1].metric("Imóveis para alugar", len(rentals_available))
    top_row[2].metric("Imóveis para vender", len(sales_available))

    bottom_row = st.columns(3)
    bottom_row[0].metric("Total de visitas agendadas", len(visits))
    bottom_row[1].metric("Negócios fechados (últimos 30 dias)", len(closed_deals))
    bottom_row[2].metric("Leads frios", lead_stats["cold_leads"])
