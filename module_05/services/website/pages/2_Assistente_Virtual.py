import uuid

import streamlit as st

from agent_client import AgentUnavailableError, send_message

SPECIALIST_AVATARS = {"mortgage_advisor": "🏦", "real_estate": "🏠"}

st.set_page_config(page_title="Assistente Virtual", layout="wide")
st.title("Converse com nossa assistente virtual")
st.caption("Compra, aluguel, investimento e agendamento de visitas - tudo por aqui.")

if "conversation_id" not in st.session_state:
    st.session_state["conversation_id"] = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "specialist" not in st.session_state:
    st.session_state["specialist"] = "real_estate"

for turn in st.session_state["chat_history"]:
    avatar = SPECIALIST_AVATARS.get(turn["specialist"]) if turn["role"] == "assistant" else None
    with st.chat_message(turn["role"], avatar=avatar):
        st.write(turn["content"])

user_input = st.chat_input("Digite sua mensagem...")
if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.spinner("Digitando..."):
        try:
            result = send_message(st.session_state["conversation_id"], user_input)
            reply = result["reply"]
            st.session_state["specialist"] = result["specialist"]
        except AgentUnavailableError:
            reply = "Não foi possível falar com a assistente virtual no momento. Tente novamente em instantes."

    with st.chat_message("assistant", avatar=SPECIALIST_AVATARS.get(st.session_state["specialist"])):
        st.write(reply)
    st.session_state["chat_history"].append(
        {"role": "assistant", "content": reply, "specialist": st.session_state["specialist"]}
    )
