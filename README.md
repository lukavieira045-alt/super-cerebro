# Super Cérebro

Núcleo inicial de inteligência usando exclusivamente o Vireonix como modelo de IA.

## Como funciona

O Super Cérebro envia a conversa para o endpoint compatível da Vireonix usando o modelo `auto`. Segundo a documentação da Vireonix, o `auto` escolhe automaticamente o modelo disponível mais adequado à tarefa.

## Instalação

```bash
pip install -r requirements.txt
python app.py
```

Não é necessária chave da OpenAI.

## Próximas camadas

- memória persistente
- ferramentas
- busca na web
- execução controlada de tarefas
- interface para Android
- testes e monitoramento
