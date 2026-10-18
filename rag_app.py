import streamlit as st

from rag_chat import answer

st.set_page_config(page_title="Grace RAG", page_icon="⚖️", layout="centered")

st.title("⚖️ Grace — Ghana Judicial System Assistant")
st.caption("Answers grounded in the Ghana judicial knowledge base (RAG over ChromaDB).")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for s in msg.get("sources", []):
            st.caption(f"📄 {s['section']} · {s['source']}")

if prompt := st.chat_input("Ask about the Ghana judicial system..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving & thinking..."):
            try:
                reply, sources = answer(prompt)
            except Exception as e:
                reply, sources = f"⚠️ Request failed: {e}", []
        st.markdown(reply)
        for s in sources:
            st.caption(f"📄 {s['section']} · {s['source']}")

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "sources": sources}
    )

with st.sidebar:
    st.header("Grace RAG")
    st.write("Querying the **ghana_judicial** ChromaDB collection.")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()