from chatbot import build_system_prompt, get_reply

SYSTEM_PROMPT = build_system_prompt()


def chat() -> None:
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Grace (ECG) assistant ready. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        try:
            reply = get_reply(history)
        except Exception as e:
            print(f"\nGrace: request failed: {e}\n")
            continue

        print(f"\nGrace: {reply}\n")
        history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    chat()
