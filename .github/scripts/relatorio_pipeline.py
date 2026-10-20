"""Gera o relatório de execução do pipeline e o envia por e-mail.

Executado pelo job "Relatório" do workflow .github/workflows/ci-cd.yml, depois de todos os outros jobs.
Usa apenas a biblioteca padrão do Python.

Variáveis de ambiente:
  GITHUB_*                  Fornecidas pelo GitHub Actions.
  GITHUB_TOKEN              Token do workflow, para ler os jobs e etapas da execução.
  RESULTADOS_JOBS           JSON de toJSON(needs), com o resultado de cada job anterior.
  DIRETORIO_TESTES          Pasta com os arquivos .trx (opcional).
  SMTP_SERVIDOR, SMTP_PORTA, SMTP_USUARIO, SMTP_SENHA, EMAIL_RELATORIO_DESTINO
                            Configuração de envio. Sem ela, o relatório só vai para o resumo da execução.
"""

from __future__ import annotations

import html
import json
import os
import smtplib
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

NOME_JOB_RELATORIO = "Relatório"

ROTULOS = {
    "success": ("Sucesso", "✅", "#1a7f37"),
    "failure": ("Falha", "❌", "#cf222e"),
    "cancelled": ("Cancelado", "⚪", "#6e7781"),
    "skipped": ("Ignorado", "⏭️", "#6e7781"),
    "neutral": ("Neutro", "➖", "#6e7781"),
    "timed_out": ("Tempo esgotado", "⏱️", "#cf222e"),
    "action_required": ("Ação necessária", "⚠️", "#9a6700"),
    None: ("Em andamento", "⏳", "#9a6700"),
}


def rotulo(conclusao: str | None) -> tuple[str, str, str]:
    return ROTULOS.get(conclusao, (str(conclusao), "•", "#6e7781"))


def env(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome, padrao).strip()


def api_github(caminho: str) -> dict:
    requisicao = urllib.request.Request(
        f"{env('GITHUB_API_URL', 'https://api.github.com')}{caminho}",
        headers={
            "Authorization": f"Bearer {env('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        return json.load(resposta)


def data(valor: str | None) -> datetime | None:
    return datetime.fromisoformat(valor.replace("Z", "+00:00")) if valor else None


def duracao(inicio: str | None, fim: str | None) -> str:
    a, b = data(inicio), data(fim)
    if not a or not b:
        return "—"
    segundos = int((b - a).total_seconds())
    return f"{segundos // 60}min {segundos % 60:02d}s" if segundos >= 60 else f"{segundos}s"


def ler_jobs() -> list[dict]:
    repo, run_id, tentativa = env("GITHUB_REPOSITORY"), env("GITHUB_RUN_ID"), env("GITHUB_RUN_ATTEMPT", "1")
    jobs = api_github(f"/repos/{repo}/actions/runs/{run_id}/attempts/{tentativa}/jobs?per_page=100")["jobs"]
    return [j for j in jobs if j["name"] != NOME_JOB_RELATORIO]


def ler_testes(diretorio: str) -> dict | None:
    """Soma os contadores de todos os arquivos .trx encontrados."""
    arquivos = list(Path(diretorio).glob("**/*.trx")) if diretorio and Path(diretorio).exists() else []
    if not arquivos:
        return None
    totais = {"total": 0, "executados": 0, "aprovados": 0, "falharam": 0, "ignorados": 0}
    falhas: list[str] = []
    ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
    for arquivo in arquivos:
        raiz = ET.parse(arquivo).getroot()
        contadores = raiz.find("t:ResultSummary/t:Counters", ns)
        if contadores is not None:
            totais["total"] += int(contadores.get("total", 0))
            totais["executados"] += int(contadores.get("executed", 0))
            totais["aprovados"] += int(contadores.get("passed", 0))
            totais["falharam"] += int(contadores.get("failed", 0))
            totais["ignorados"] += int(contadores.get("notExecuted", 0))
        for resultado in raiz.iterfind("t:Results/t:UnitTestResult", ns):
            if resultado.get("outcome") == "Failed":
                falhas.append(resultado.get("testName", "?"))
    totais["lista_falhas"] = falhas
    return totais


def ler_commit() -> dict:
    evento = {}
    caminho = env("GITHUB_EVENT_PATH")
    if caminho and Path(caminho).exists():
        evento = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if "pull_request" in evento:
        pr = evento["pull_request"]
        return {
            "sha": pr["head"]["sha"],
            "mensagem": f"PR #{pr['number']}: {pr['title']}",
            "autor": pr["user"]["login"],
        }
    head = evento.get("head_commit") or {}
    return {
        "sha": head.get("id", env("GITHUB_SHA")),
        "mensagem": head.get("message", "").splitlines()[0] if head.get("message") else "—",
        "autor": (head.get("author") or {}).get("name", env("GITHUB_ACTOR")),
    }


def status_geral(resultados: dict[str, str]) -> str:
    valores = set(resultados.values())
    if valores & {"failure", "timed_out"}:
        return "failure"
    if "cancelled" in valores:
        return "cancelled"
    return "success"


def montar_relatorio() -> dict:
    # Formato de toJSON(needs): {"build": {"result": "success", "outputs": {}}, ...}
    resultados = {job: dados.get("result") for job, dados in json.loads(env("RESULTADOS_JOBS", "{}")).items()}
    repo = env("GITHUB_REPOSITORY")
    run_url = f"{env('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{env('GITHUB_RUN_ID')}"
    jobs = ler_jobs()
    inicios = [data(j["started_at"]) for j in jobs if j.get("started_at")]
    fins = [data(j["completed_at"]) for j in jobs if j.get("completed_at")]
    return {
        "status": status_geral(resultados),
        "repo": repo,
        "workflow": env("GITHUB_WORKFLOW"),
        "numero": env("GITHUB_RUN_NUMBER"),
        "tentativa": env("GITHUB_RUN_ATTEMPT", "1"),
        "evento": env("GITHUB_EVENT_NAME"),
        "ref": env("GITHUB_HEAD_REF") or env("GITHUB_REF_NAME"),
        "ator": env("GITHUB_ACTOR"),
        "commit": ler_commit(),
        "url": run_url,
        "inicio": min(inicios).strftime("%d/%m/%Y %H:%M:%S UTC") if inicios else "—",
        "duracao_total": duracao(min(inicios).isoformat(), max(fins).isoformat()) if inicios and fins else "—",
        "jobs": jobs,
        "testes": ler_testes(env("DIRETORIO_TESTES")),
    }


def html_relatorio(r: dict) -> str:
    texto, icone, cor = rotulo(r["status"])
    e = html.escape
    linhas_jobs = []
    for job in r["jobs"]:
        jt, ji, jc = rotulo(job["conclusion"])
        linhas_jobs.append(
            f"<tr><td colspan='3' style='padding:10px 8px 4px;font-weight:600;border-top:1px solid #d0d7de'>"
            f"{ji} {e(job['name'])} — <span style='color:{jc}'>{jt}</span> "
            f"<span style='color:#6e7781;font-weight:400'>({duracao(job['started_at'], job['completed_at'])})</span></td></tr>"
        )
        for etapa in job.get("steps", []):
            et, ei, ec = rotulo(etapa["conclusion"])
            linhas_jobs.append(
                f"<tr><td style='padding:2px 8px 2px 28px'>{e(etapa['name'])}</td>"
                f"<td style='padding:2px 8px;color:{ec}'>{ei} {et}</td>"
                f"<td style='padding:2px 8px;color:#6e7781'>{duracao(etapa.get('started_at'), etapa.get('completed_at'))}</td></tr>"
            )

    t = r["testes"]
    if t is None:
        bloco_testes = "<p>Nenhum resultado de teste disponível (o job de testes não gerou relatório).</p>"
    else:
        aviso = "<p style='color:#9a6700'>Nenhum teste foi encontrado na solution.</p>" if t["total"] == 0 else ""
        falhas = "".join(f"<li>{e(n)}</li>" for n in t["lista_falhas"][:20])
        bloco_testes = (
            f"<table style='border-collapse:collapse'>"
            f"<tr><td style='padding:2px 12px 2px 0'>Total</td><td><b>{t['total']}</b></td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0'>Aprovados</td><td style='color:#1a7f37'><b>{t['aprovados']}</b></td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0'>Falharam</td><td style='color:#cf222e'><b>{t['falharam']}</b></td></tr>"
            f"<tr><td style='padding:2px 12px 2px 0'>Não executados</td><td><b>{t['ignorados']}</b></td></tr>"
            f"</table>{aviso}"
            + (f"<p><b>Testes com falha:</b></p><ul>{falhas}</ul>" if falhas else "")
        )

    c = r["commit"]
    return f"""<!doctype html>
<html lang="pt-BR"><body style="font-family:Segoe UI,Arial,sans-serif;color:#1f2328;max-width:760px">
<h2 style="margin:0 0 4px">{icone} Pipeline {e(r['workflow'])} — <span style="color:{cor}">{texto}</span></h2>
<p style="margin:0 0 16px;color:#6e7781">{e(r['repo'])} · execução #{e(r['numero'])} (tentativa {e(r['tentativa'])})</p>

<h3>Resumo</h3>
<table style="border-collapse:collapse">
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Resultado</td><td style="color:{cor}"><b>{texto}</b></td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Evento</td><td>{e(r['evento'])}</td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Branch</td><td>{e(r['ref'])}</td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Commit</td><td><code>{e(c['sha'][:7])}</code> {e(c['mensagem'])}</td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Autor</td><td>{e(c['autor'])} (disparado por {e(r['ator'])})</td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Início</td><td>{e(r['inicio'])}</td></tr>
<tr><td style="padding:2px 12px 2px 0;color:#6e7781">Duração</td><td>{e(r['duracao_total'])}</td></tr>
</table>

<h3>Jobs e etapas executadas</h3>
<table style="border-collapse:collapse;width:100%;font-size:14px">{''.join(linhas_jobs)}</table>

<h3>Testes</h3>
{bloco_testes}

<p style="margin-top:24px"><a href="{e(r['url'])}">Abrir a execução no GitHub Actions</a></p>
<p style="color:#6e7781;font-size:12px">Relatório gerado automaticamente pelo job "{NOME_JOB_RELATORIO}" do workflow.</p>
</body></html>"""


def texto_relatorio(r: dict) -> str:
    """Versão em Markdown: corpo alternativo do e-mail e resumo da execução no GitHub."""
    texto, icone, _ = rotulo(r["status"])
    c = r["commit"]
    linhas = [
        f"## {icone} Pipeline {r['workflow']} — {texto}",
        "",
        f"- **Repositório:** {r['repo']} (execução #{r['numero']}, tentativa {r['tentativa']})",
        f"- **Evento:** {r['evento']} · **Branch:** {r['ref']}",
        f"- **Commit:** `{c['sha'][:7]}` {c['mensagem']} — {c['autor']}",
        f"- **Início:** {r['inicio']} · **Duração:** {r['duracao_total']}",
        "",
        "### Jobs e etapas",
        "",
    ]
    for job in r["jobs"]:
        jt, ji, _ = rotulo(job["conclusion"])
        linhas.append(f"- {ji} **{job['name']}** — {jt} ({duracao(job['started_at'], job['completed_at'])})")
        for etapa in job.get("steps", []):
            et, ei, _ = rotulo(etapa["conclusion"])
            linhas.append(f"  - {ei} {etapa['name']} — {et}")
    t = r["testes"]
    linhas += ["", "### Testes", ""]
    if t is None:
        linhas.append("Nenhum resultado de teste disponível.")
    else:
        linhas.append(
            f"Total: {t['total']} · Aprovados: {t['aprovados']} · Falharam: {t['falharam']} · Não executados: {t['ignorados']}"
        )
        linhas += [f"- ❌ {n}" for n in t["lista_falhas"][:20]]
    linhas += ["", f"[Abrir a execução no GitHub Actions]({r['url']})"]
    return "\n".join(linhas) + "\n"


def enviar_email(r: dict, corpo_html: str, corpo_texto: str) -> None:
    servidor, usuario, senha, destino = (
        env("SMTP_SERVIDOR"), env("SMTP_USUARIO"), env("SMTP_SENHA"), env("EMAIL_RELATORIO_DESTINO"),
    )
    if not all([servidor, usuario, senha, destino]):
        print("::warning title=Relatório por e-mail::E-mail não enviado: configure os secrets "
              "SMTP_SERVIDOR, SMTP_USUARIO, SMTP_SENHA e EMAIL_RELATORIO_DESTINO.")
        return

    porta = int(env("SMTP_PORTA") or "465")
    texto, icone, _ = rotulo(r["status"])
    mensagem = EmailMessage()
    mensagem["Subject"] = f"{icone} [{r['repo']}] Pipeline #{r['numero']} — {texto} ({r['ref']})"
    mensagem["From"] = usuario
    mensagem["To"] = destino
    mensagem.set_content(corpo_texto)
    mensagem.add_alternative(corpo_html, subtype="html")

    contexto = ssl.create_default_context()
    if porta == 465:
        with smtplib.SMTP_SSL(servidor, porta, context=contexto, timeout=30) as smtp:
            smtp.login(usuario, senha)
            smtp.send_message(mensagem)
    else:
        with smtplib.SMTP(servidor, porta, timeout=30) as smtp:
            smtp.starttls(context=contexto)
            smtp.login(usuario, senha)
            smtp.send_message(mensagem)
    print("Relatório enviado por e-mail.")


def main() -> int:
    relatorio = montar_relatorio()
    corpo_texto = texto_relatorio(relatorio)

    resumo = env("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as arquivo:
            arquivo.write(corpo_texto)
    print(corpo_texto)

    try:
        enviar_email(relatorio, html_relatorio(relatorio), corpo_texto)
    except (smtplib.SMTPException, OSError) as erro:
        # A mensagem não inclui credenciais: smtplib não as repete nas exceções.
        print(f"::error title=Relatório por e-mail::Falha ao enviar o e-mail: {type(erro).__name__}: {erro}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
