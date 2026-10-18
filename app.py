import streamlit as st

from chatbot import build_system_prompt, get_reply
from rag_chat import answer

DOMAINS = {"ECG": "⚡", "Judicial": "⚖️"}


def reset_messages() -> None:
    st.session_state.messages = []


def render_stream(role: str, content: str, sources: list[dict] | None = None) -> None:
    with st.chat_message(role):
        st.markdown(content)
        for s in sources or []:
            st.caption(f"📄 {s['section']} · {s['source']}")


def main() -> None:
    st.set_page_config(page_title="Grace AI", page_icon="⚡", layout="centered")

    st.title("⚡/⚖️ Grace AI — Multi-Domain Assistant")
    st.caption(
        "**ECG**: electricity billing & customer service · "
        "**Judicial**: Ghana judicial system (RAG over ChromaDB)."
    )

    domain = st.sidebar.selectbox("Domain", list(DOMAINS), format_func=lambda d: f"{DOMAINS[d]} {d}")
    st.sidebar.button("Clear conversation", on_click=reset_messages)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    placeholder = (
        "How can I help with your ECG account?"
        if domain == "ECG"
        else "Ask about the Ghana judicial system..."
    )

    for msg in st.session_state.messages:
        if msg["domain"] != domain:
            continue
        render_stream(msg["role"], msg["content"], msg.get("sources"))

    if prompt := st.chat_input(placeholder):
        user_msg = {"domain": domain, "role": "user", "content": prompt}
        st.session_state.messages.append(user_msg)
        render_stream("user", prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    if domain == "ECG":
                        history = [{"role": "system", "content": build_system_prompt()}]
                        for m in st.session_state.messages:
                            if m["domain"] == domain and m["role"] in {"user", "assistant"}:
                                history.append({"role": m["role"], "content": m["content"]})
                        reply = get_reply(history)
                        sources = []
                    else:
                        reply, sources = answer(prompt)
                except Exception as e:
                    reply, sources = f"⚠️ Request failed: {e}", []
        render_stream("assistant", reply, sources)

        st.session_state.messages.append(
            {"domain": domain, "role": "assistant", "content": reply, "sources": sources}
        )


if __name__ == "__main__":
    main()