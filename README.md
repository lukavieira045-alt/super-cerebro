# 🧠 Super Cérebro

Agente de IA modular em Python, criado para evoluir por etapas com raciocínio, ferramentas, memória e integrações externas.

## Estrutura

```text
super-cerebro/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── agent/
    ├── __init__.py
    ├── brain.py
    └── tools.py
```

## Rodar localmente

1. Crie um ambiente virtual:

```bash
python -m venv .venv
```

2. Ative o ambiente e instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie `.env` baseado em `.env.example` e coloque sua `OPENAI_API_KEY`.

4. Execute:

```bash
python app.py
```

A chave fica apenas no `.env`, que está protegido pelo `.gitignore`.

## Próximas etapas

- memória persistente;
- busca web real;
- sistema de planejamento e verificação;
- permissões para ferramentas;
- suporte multimodal;
- interface web;
- testes automatizados;
- observabilidade e limites de segurança.

> O projeto será desenvolvido por módulos, evitando colocar segredos no código e evitando execução arbitrária de comandos.
