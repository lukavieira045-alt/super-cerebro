"""Command-line entry point for Super Cérebro."""

from agent.brain import build_agent


def main() -> None:
    agent = build_agent()
    print("Super Cérebro iniciado. Digite 'sair' para encerrar.")

    while True:
        try:
            user_input = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break

        if user_input.lower() in {"sair", "exit", "quit"}:
            print("Até mais!")
            break
        if not user_input:
            continue

        result = agent.invoke({"messages": [("user", user_input)]})
        print("\nSuper Cérebro:", result["messages"][-1].content)


if __name__ == "__main__":
    main()
