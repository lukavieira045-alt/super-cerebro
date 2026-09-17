"""Command-line interface for Super Cérebro."""

from agent.brain import build_agent
from agent.health import run_health_checks


def main() -> None:
    brain = build_agent()
    print("Super Cérebro iniciado com Vireonix Auto.")
    print("Digite 'saude' para diagnóstico local ou 'sair' para encerrar.")

    while True:
        try:
            user_input = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            break

        command = user_input.lower()
        if command in {"sair", "exit", "quit"}:
            print("Até mais!")
            break
        if not user_input:
            continue

        if command in {"saude", "saúde", "health", "diagnostico", "diagnóstico"}:
            try:
                print("\n" + run_health_checks().text())
            except Exception as exc:
                print(f"\nErro no diagnóstico: {exc}")
            continue

        try:
            answer = brain.ask(user_input)
            print("\nSuper Cérebro:", answer)
        except RuntimeError as exc:
            print(f"\nErro: {exc}")


if __name__ == "__main__":
    main()
