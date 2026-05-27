# Monitor Automático de Processos Python

Monitora processos Python em execução e envia notificações por e-mail quando cada um termina — e um aviso final quando todos concluem.

## O que faz

- Detecta automaticamente todos os processos Python rodando no sistema
- Envia um e-mail ao iniciar o monitoramento
- Notifica por e-mail quando cada processo finaliza (com duração)
- Envia um e-mail final quando **todos** os processos terminaram
- Credenciais armazenadas com segurança no cofre do sistema operacional (keyring)

## Instalação

```bash
python -m pip install git+https://github.com/rafa-rod/monitor-automatico.git
```

## Configuração (primeira vez)

Você precisará de uma **Senha de App** do Gmail — não use sua senha normal.

Gere em: **Conta Google → Segurança → Verificação em duas etapas → Senhas de app**

Depois configure:

```bash
python monitor_automatico.py --setup
```

As credenciais ficam salvas no cofre do SO (Windows Credential Manager / macOS Keychain / Linux Secret Service). Não são armazenadas em nenhum arquivo.

## Uso

```bash
# Inicia o monitoramento contínuo
python monitor_automatico.py

# Lista processos Python ativos no momento
python monitor_automatico.py --list

# Remove credenciais salvas (para reconfigurar)
python monitor_automatico.py --reset

# Ajuda
python monitor_automatico.py --help
```

## E-mails enviados

| Momento | E-mail |
|---|---|
| Monitor iniciado | ✅ Aviso de início com hora |
| Processo finaliza | ✅ Nome do script, duração, quantos restam |
| Último processo finaliza | 🏁 Aviso de conclusão total |

Novos processos detectados aparecem apenas no terminal, sem e-mail.

## Dependências

- `psutil` — leitura de processos do sistema
- `keyring` — armazenamento seguro de credenciais
