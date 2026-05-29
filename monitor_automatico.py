"""
monitor_automatico.py
─────────────────────────────────────────────────────────────────
Monitor de processos Python com notificação por e-mail.
Credenciais armazenadas no keyring do sistema operacional.

Primeiro uso — configure as credenciais uma única vez:
    python monitor_automatico.py --setup

Uso normal:
    python monitor_automatico.py              # monitora continuamente
    python monitor_automatico.py --list       # lista processos atuais
    python monitor_automatico.py --reset      # apaga credenciais salvas
    python monitor_automatico.py --help       # ajuda
"""

import os
import sys
import time
import smtplib
import psutil
import keyring
import getpass
from email.message import EmailMessage
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
KEYRING_SERVICE  = "monitor python"   # nome do serviço no cofre do SO
KEYRING_EMAIL    = "email"            # chave para o e-mail
KEYRING_SENHA    = "senha_app"        # chave para a senha de app Gmail
VERIFICAR_INTERVALO = 10              # segundos entre cada varredura

# Processos que devem ser ignorados (para não monitorar o próprio monitor)
IGNORAR_SCRIPTS = {"monitor_automatico.py"}


# ─────────────────────────────────────────────
# CREDENCIAIS — keyring
# ─────────────────────────────────────────────

def salvar_credenciais():
    """Solicita e salva e-mail + senha de app no keyring do SO."""
    print("\n🔐 Configuração de credenciais")
    print("   As credenciais serão salvas no cofre do seu sistema operacional.")
    print("   Use uma Senha de App do Gmail (não sua senha principal).")
    print("   Gere em: Conta Google → Segurança → Senhas de app\n")

    email = input("   E-mail Gmail: ").strip()
    senha = getpass.getpass("   Senha de app (oculta): ").strip()

    keyring.set_password(KEYRING_SERVICE, KEYRING_EMAIL, email)
    keyring.set_password(KEYRING_SERVICE, KEYRING_SENHA, senha)

    print("\n✅ Credenciais salvas com sucesso no keyring!\n")


def carregar_credenciais():
    """
    Lê e-mail e senha do keyring.
    Retorna (email, senha) ou (None, None) se não configurado.
    """
    email = keyring.get_password(KEYRING_SERVICE, KEYRING_EMAIL)
    senha = keyring.get_password(KEYRING_SERVICE, KEYRING_SENHA)
    return email, senha


def apagar_credenciais():
    """Remove as credenciais salvas do keyring."""
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_EMAIL)
        keyring.delete_password(KEYRING_SERVICE, KEYRING_SENHA)
        print("✅ Credenciais removidas do keyring.")
    except keyring.errors.PasswordDeleteError:
        print("⚠️  Nenhuma credencial encontrada para remover.")


def verificar_credenciais():
    """Garante que as credenciais existem antes de iniciar o monitor."""
    email, senha = carregar_credenciais()
    if not email or not senha:
        print("\n⚠️  Credenciais não configuradas.")
        print("   Execute primeiro: python monitor_automatico.py --setup\n")
        sys.exit(1)
    return email, senha


# ─────────────────────────────────────────────
# E-MAIL
# ─────────────────────────────────────────────

def enviar_email(email: str, senha: str, assunto: str, corpo: str):
    """Envia notificação via Gmail SMTP."""
    msg = EmailMessage()
    msg.set_content(corpo)
    msg["Subject"] = assunto
    msg["From"]    = email
    msg["To"]      = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email, senha)
            server.send_message(msg)
        print(f"📧 E-mail enviado: {assunto}")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")


# ─────────────────────────────────────────────
# DESCOBERTA DE PROCESSOS
# ─────────────────────────────────────────────

def descobrir_processos_python() -> dict:
    """
    Varre todos os processos do sistema e retorna apenas os Python,
    excluindo o próprio monitor.

    Retorna: {pid: dict_com_info}
    """
    processos = {}

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time", "username"]):
        try:
            nome    = (proc.info["name"] or "").lower()
            cmdline = proc.info["cmdline"] or []
            cmd_str = " ".join(cmdline)

            eh_python = (
                "python"    in nome or
                "python3"   in nome or
                cmd_str.lower().startswith("python")
            )
            if not eh_python:
                continue

            # Nome do script (segundo argumento da linha de comando)
            script = "terminal interativo"
            if len(cmdline) > 1:
                script = os.path.basename(cmdline[1])

            # Ignora o próprio monitor
            if script in IGNORAR_SCRIPTS:
                continue

            pid = proc.info["pid"]
            processos[pid] = {
                "pid":     pid,
                "nome":    nome,
                "script":  script,
                "inicio":  datetime.fromtimestamp(proc.info["create_time"]),
                "usuario": proc.info["username"] or "desconhecido",
                "cmdline": cmd_str,
            }

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processos


def formatar_duracao(delta) -> str:
    """Converte timedelta em string legível: 1h 23m 45s."""
    total = int(delta.total_seconds())
    h, resto = divmod(total, 3600)
    m, s     = divmod(resto, 60)
    partes = []
    if h: partes.append(f"{h}h")
    if m: partes.append(f"{m}m")
    partes.append(f"{s}s")
    return " ".join(partes)


# ─────────────────────────────────────────────
# MONITOR CONTÍNUO
# ─────────────────────────────────────────────

def monitorar():
    """Loop principal: detecta novos processos, finalizações e notifica."""
    email, senha = verificar_credenciais()

    print("=" * 60)
    print("🚀 MONITOR AUTOMÁTICO DE PROCESSOS PYTHON")
    print("=" * 60)
    print(f"📊 Verificando a cada {VERIFICAR_INTERVALO} segundos")
    print(f"📧 Notificações para: {email}")
    print("   Ctrl+C para encerrar")
    print("=" * 60)

    processos_anteriores: dict = {}
    notificados: set = set()   # PIDs já notificados como finalizados

    # Aviso de início
    enviar_email(
        email, senha,
        "✅ Monitor Iniciado",
        f"Monitor de processos Python iniciado em {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"Verificando a cada {VERIFICAR_INTERVALO} segundos.",
    )

    try:
        while True:
            agora = datetime.now()
            processos_atuais = descobrir_processos_python()
            pids_atuais      = set(processos_atuais)
            pids_anteriores  = set(processos_anteriores)

            # ── Novos processos detectados ────────────────────────────
            for pid in pids_atuais - pids_anteriores:
                info = processos_atuais[pid]
                print(f"\n🆕 [{agora:%H:%M:%S}] NOVO PROCESSO")
                print(f"   PID {pid} • {info['script']} • {info['usuario']}")

                enviar_email(
                    email, senha,
                    f"🆕 Novo processo Python — {info['script']}",
                    f"Novo processo detectado:\n\n"
                    f"  PID    : {pid}\n"
                    f"  Script : {info['script']}\n"
                    f"  Usuário: {info['usuario']}\n"
                    f"  Início : {info['inicio']:%Y-%m-%d %H:%M:%S}\n"
                    f"  Comando: {info['cmdline']}",
                )

            # ── Processos finalizados ─────────────────────────────────
            for pid in pids_anteriores - pids_atuais:
                if pid in notificados:
                    continue

                info     = processos_anteriores[pid]
                duracao  = formatar_duracao(agora - info["inicio"])
                restantes = len(pids_atuais - notificados)

                print(f"\n✅ [{agora:%H:%M:%S}] PROCESSO FINALIZADO")
                print(f"   PID {pid} • {info['script']} • duração: {duracao}")

                if restantes == 0:
                    # Último processo — todos terminaram
                    print("🎉 TODOS OS PROCESSOS FINALIZARAM!")
                    enviar_email(
                        email, senha,
                        "🏁 CONCLUÍDO — Todos os processos finalizaram",
                        f"Último processo encerrado:\n\n"
                        f"  PID    : {pid}\n"
                        f"  Script : {info['script']}\n"
                        f"  Duração: {duracao}\n\n"
                        f"✅ Todos os processos Python foram concluídos.\n"
                        f"  Encerramento: {agora:%Y-%m-%d %H:%M:%S}",
                    )
                else:
                    enviar_email(
                        email, senha,
                        f"✅ Processo finalizado — {info['script']} (PID {pid})",
                        f"Processo encerrado:\n\n"
                        f"  PID      : {pid}\n"
                        f"  Script   : {info['script']}\n"
                        f"  Duração  : {duracao}\n"
                        f"  Encerrado: {agora:%Y-%m-%d %H:%M:%S}\n\n"
                        f"  Ainda em execução: {restantes} processo(s).",
                    )

                notificados.add(pid)

            # ── Status no terminal ────────────────────────────────────
            ativos = [p for pid, p in processos_atuais.items() if pid not in notificados]
            if ativos:
                print(f"\n📊 [{agora:%H:%M:%S}] {len(ativos)} processo(s) em execução:")
                for p in ativos:
                    duracao = formatar_duracao(agora - p["inicio"])
                    print(f"   • PID {p['pid']}: {p['script']}  [{duracao}]")
            else:
                print(f"\n⏳ [{agora:%H:%M:%S}] Nenhum processo Python em execução.")

            print(f"   🔄 Próxima verificação em {VERIFICAR_INTERVALO}s...")
            print("-" * 60)

            processos_anteriores = processos_atuais
            time.sleep(VERIFICAR_INTERVALO)

    except KeyboardInterrupt:
        print("\n\n👋 Monitor encerrado pelo usuário.")
        enviar_email(
            email, senha,
            "⏹️ Monitor Encerrado",
            f"Monitor encerrado manualmente em {datetime.now():%Y-%m-%d %H:%M:%S}.",
        )


# ─────────────────────────────────────────────
# LISTAR PROCESSOS (modo --list)
# ─────────────────────────────────────────────

def listar_processos():
    processos = descobrir_processos_python()
    agora = datetime.now()

    if processos:
        print(f"\n🔍 {len(processos)} processo(s) Python em execução:\n")
        print(f"{'PID':<8} {'Script':<30} {'Duração':<12} {'Usuário'}")
        print("-" * 65)
        for p in processos.values():
            duracao = formatar_duracao(agora - p["inicio"])
            print(f"{p['pid']:<8} {p['script']:<30} {duracao:<12} {p['usuario']}")
    else:
        print("\n⏳ Nenhum processo Python encontrado.\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

AJUDA = """
Uso:
  python monitor_automatico.py            Inicia monitoramento contínuo
  python monitor_automatico.py --setup    Configura e-mail e senha (primeira vez)
  python monitor_automatico.py --list     Lista processos Python ativos agora
  python monitor_automatico.py --reset    Remove credenciais salvas no keyring
  python monitor_automatico.py --help     Mostra esta ajuda

Dependências:
  pip install psutil keyring
"""

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "--setup":
        salvar_credenciais()
    elif arg == "--list":
        listar_processos()
    elif arg == "--reset":
        apagar_credenciais()
    elif arg in ("--help", "-h"):
        print(AJUDA)
    else:
        monitorar()
