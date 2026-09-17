"""Command-line interface for Super Cérebro."""

from agent.brain import build_agent


def main() -> None:
    brain = build_agent()
    print("Super Cérebro iniciado com Vireonix Auto.")
    print("Digite 'sair' para encerrar.")

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

        try:
            answer = brain.ask(user_input)
            print("\nSuper Cérebro:", answer)
        except RuntimeError as exc:
            print(f"\nErro: {exc}")


if __name__ == "__main__":
    main()
