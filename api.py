"""
Servidor HTTP leve (biblioteca padrão Python, zero dependências externas)
que expõe os simuladores reais de `simulador/` para a interface gráfica React.

Uso:
    python api.py                # inicia em http://127.0.0.1:8000
    python api.py --port 8000    # porta customizada

Se `web/dist` existir (após `npm run build` dentro de `web/`), este servidor
também serve a interface React pronta no mesmo endereço.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from simulador.automato_finito import EPS as AF_EPS, AutomatoFinito
from simulador.automato_pilha import AutomatoPilha
from simulador.maquina_turing import MaquinaTuring, decodificar_unario

RAIZ = Path(__file__).resolve().parent
EXEMPLOS_DIR = RAIZ / "exemplos"
WEB_DIST_DIR = RAIZ / "web" / "dist"

SUGESTOES_CADEIAS: dict[str, list[dict[str, str | bool]]] = {
    "afd_enunciado.json": [
        {"cadeia": "ab", "esperado": True, "rotulo": "ab (aceita)"},
        {"cadeia": "aba", "esperado": False, "rotulo": "aba (trava)"},
        {"cadeia": "", "esperado": False, "rotulo": "ε (rejeita)"},
    ],
    "afd_numero_par_de_a.json": [
        {"cadeia": "aabba", "esperado": False, "rotulo": "aabba (3 a's)"},
        {"cadeia": "ababa", "esperado": False, "rotulo": "ababa (3 a's)"},
        {"cadeia": "aabbaa", "esperado": True, "rotulo": "aabbaa (4 a's)"},
        {"cadeia": "", "esperado": True, "rotulo": "ε (0 a's)"},
    ],
    "afd_binario_multiplo_3.json": [
        {"cadeia": "110", "esperado": True, "rotulo": "110 (6 = 3×2)"},
        {"cadeia": "1001", "esperado": True, "rotulo": "1001 (9 = 3×3)"},
        {"cadeia": "101", "esperado": False, "rotulo": "101 (5)"},
    ],
    "afn_termina_em_ab.json": [
        {"cadeia": "abab", "esperado": True, "rotulo": "abab (termina em ab)"},
        {"cadeia": "aaab", "esperado": True, "rotulo": "aaab (termina em ab)"},
        {"cadeia": "aba", "esperado": False, "rotulo": "aba (rejeita)"},
    ],
    "afne_a_estrela_ou_b_estrela.json": [
        {"cadeia": "aaa", "esperado": True, "rotulo": "aaa (a*)"},
        {"cadeia": "bbb", "esperado": True, "rotulo": "bbb (b*)"},
        {"cadeia": "", "esperado": True, "rotulo": "ε (ambos)"},
        {"cadeia": "ab", "esperado": False, "rotulo": "ab (rejeita)"},
    ],
    "ap_anbn.json": [
        {"cadeia": "aaabbb", "esperado": True, "rotulo": "aaabbb (a³b³)"},
        {"cadeia": "ab", "esperado": True, "rotulo": "ab (a¹b¹)"},
        {"cadeia": "aabbb", "esperado": False, "rotulo": "aabbb (desbalanceada)"},
        {"cadeia": "ba", "esperado": False, "rotulo": "ba (trava no início)"},
    ],
    "ap_wwr.json": [
        {"cadeia": "abba", "esperado": True, "rotulo": "abba (w=ab)"},
        {"cadeia": "aabbbaa", "esperado": False, "rotulo": "aabbbaa (ímpar)"},
        {"cadeia": "aabbaa", "esperado": True, "rotulo": "aabbaa (w=aab)"},
        {"cadeia": "", "esperado": True, "rotulo": "ε (w=ε)"},
    ],
    "mt_w_sharp_w.json": [
        {"cadeia": "01#01", "esperado": True, "rotulo": "01#01 (aceita)"},
        {"cadeia": "101#101", "esperado": True, "rotulo": "101#101 (aceita)"},
        {"cadeia": "01#10", "esperado": False, "rotulo": "01#10 (rejeita)"},
        {"cadeia": "#", "esperado": True, "rotulo": "# (w=ε)"},
    ],
    "mt_soma_unaria.json": [
        {"cadeia": "000100", "esperado": True, "rotulo": "000100 (3 + 2 = 5)"},
        {"cadeia": "0010", "esperado": True, "rotulo": "0010 (2 + 1 = 3)"},
        {"cadeia": "1000", "esperado": True, "rotulo": "1000 (0 + 3 = 3)"},
    ],
}

TRANSICAO_AP_RE = re.compile(r"δ\(([^,]+),\s*([^,]+),\s*([^)]+)\)\s*=\s*\(([^,]+),\s*([^)]+)\)")


def _normalizar_cadeia(cadeia: str | None) -> str:
    if cadeia is None:
        return ""
    if cadeia in ("ε", "λ"):
        return ""
    return cadeia


def _listar_exemplos() -> dict[str, list[dict]]:
    grupos: dict[str, list[dict]] = {"af": [], "ap": [], "mt": []}
    for caminho in sorted(EXEMPLOS_DIR.glob("*.json")):
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        nome = caminho.name
        tipo = str(dados.get("tipo", "")).upper()
        if nome.startswith(("afd_", "afn_", "afne_")) or tipo in ("AFD", "AFN", "AFN-Ε", "AFN-ε"):
            categoria = "af"
        elif nome.startswith("ap_") or tipo == "AP":
            categoria = "ap"
        elif nome.startswith("mt_") or tipo == "MT":
            categoria = "mt"
        else:
            continue

        grupos[categoria].append(
            {
                "id": nome,
                "nome": nome.replace(".json", ""),
                "descricao": dados.get("descricao", ""),
                "modelo": dados,
                "sugestoes": SUGESTOES_CADEIAS.get(nome, []),
            }
        )
    return grupos


def _simular_af(dados_modelo: dict, cadeia_raw: str, converter_afd: bool = False) -> dict:
    cadeia = _normalizar_cadeia(cadeia_raw)
    af = AutomatoFinito.de_dict(dados_modelo)
    if converter_afd and af.tipo != "AFD":
        af = af.para_afd()

    res_oficial = af.executar(cadeia)
    modelo_dict = af.para_dict()

    # Lista de arestas para renderização e tabela de transição
    simbolos_tabela = sorted(af.alfabeto)
    if any(a == AF_EPS for (_, a) in af.transicoes):
        simbolos_tabela.append(AF_EPS)

    estados_ordenados = sorted(af.estados, key=lambda s: (s != af.estado_inicial, s))
    tabela_transicoes = []
    for q in estados_ordenados:
        celulas = {}
        for a in simbolos_tabela:
            destinos = sorted(af.transicoes.get((q, a), set()))
            celulas[a or "ε"] = destinos
        tabela_transicoes.append(
            {
                "estado": q,
                "inicial": q == af.estado_inicial,
                "final": q in af.estados_finais,
                "celulas": celulas,
            }
        )

    passos: list[dict] = []

    if af.tipo == "AFD":
        atual = af.estado_inicial
        passos.append(
            {
                "numero": 0,
                "estadosAnterior": [],
                "estadosAtivos": [atual],
                "simboloLido": None,
                "posEntrada": 0,
                "transicoesUsadas": [],
                "descricao": f"Início no estado inicial {atual}.",
                "travou": False,
            }
        )
        for i, a in enumerate(cadeia):
            if a not in af.alfabeto:
                passos.append(
                    {
                        "numero": i + 1,
                        "estadosAnterior": [atual],
                        "estadosAtivos": [atual],
                        "simboloLido": a,
                        "posEntrada": i,
                        "transicoesUsadas": [],
                        "descricao": f"Símbolo '{a}' na posição {i} não pertence a Σ.",
                        "travou": True,
                    }
                )
                break
            destinos = af.transicoes.get((atual, a))
            if not destinos:
                passos.append(
                    {
                        "numero": i + 1,
                        "estadosAnterior": [atual],
                        "estadosAtivos": [atual],
                        "simboloLido": a,
                        "posEntrada": i + 1,
                        "transicoesUsadas": [],
                        "descricao": f"δ({atual}, {a}) indefinida — o autômato trava e rejeita.",
                        "travou": True,
                    }
                )
                break
            proximo = next(iter(destinos))
            passos.append(
                {
                    "numero": i + 1,
                    "estadosAnterior": [atual],
                    "estadosAtivos": [proximo],
                    "simboloLido": a,
                    "posEntrada": i + 1,
                    "transicoesUsadas": [{"de": atual, "simbolo": a, "para": proximo}],
                    "descricao": f"Lê '{a}': δ({atual}, {a}) = {proximo}",
                    "travou": False,
                }
            )
            atual = proximo
    else:
        # AFN / AFN-ε: registra transições diretas e de fecho-ε
        def _fecho_com_arestas(origem: set[str]) -> tuple[set[str], list[dict]]:
            fecho = set(origem)
            pilha = list(origem)
            arestas = []
            while pilha:
                q = pilha.pop()
                for r in sorted(af.transicoes.get((q, AF_EPS), set())):
                    arestas.append({"de": q, "simbolo": "ε", "para": r})
                    if r not in fecho:
                        fecho.add(r)
                        pilha.append(r)
            return fecho, arestas

        atuais, eps_iniciais = _fecho_com_arestas({af.estado_inicial})
        passos.append(
            {
                "numero": 0,
                "estadosAnterior": [],
                "estadosAtivos": sorted(atuais),
                "simboloLido": None,
                "posEntrada": 0,
                "transicoesUsadas": eps_iniciais,
                "descricao": (
                    f"Início: E({{{af.estado_inicial}}}) = {{{', '.join(sorted(atuais))}}}"
                ),
                "travou": False,
            }
        )
        for i, a in enumerate(cadeia):
            if a not in af.alfabeto:
                passos.append(
                    {
                        "numero": i + 1,
                        "estadosAnterior": sorted(atuais),
                        "estadosAtivos": [],
                        "simboloLido": a,
                        "posEntrada": i,
                        "transicoesUsadas": [],
                        "descricao": f"Símbolo '{a}' na posição {i} não pertence a Σ.",
                        "travou": True,
                    }
                )
                break
            movidos: set[str] = set()
            usadas: list[dict] = []
            for q in sorted(atuais):
                for d in sorted(af.transicoes.get((q, a), set())):
                    movidos.add(d)
                    usadas.append({"de": q, "simbolo": a, "para": d})
            proximos, eps_arestas = _fecho_com_arestas(movidos)
            usadas.extend(eps_arestas)
            travou = len(proximos) == 0
            mov_txt = "{" + ", ".join(sorted(movidos)) + "}" if movidos else "∅"
            prox_txt = "{" + ", ".join(sorted(proximos)) + "}" if proximos else "∅"
            ant_txt = "{" + ", ".join(sorted(atuais)) + "}" if atuais else "∅"
            desc = f"Lê '{a}': δ({ant_txt}, {a}) = {mov_txt}"
            if eps_arestas:
                desc += f" → fecho-ε = {prox_txt}"
            if travou:
                desc += " — todos os ramos morreram."
            passos.append(
                {
                    "numero": i + 1,
                    "estadosAnterior": sorted(atuais),
                    "estadosAtivos": sorted(proximos),
                    "simboloLido": a,
                    "posEntrada": i + 1,
                    "transicoesUsadas": usadas,
                    "descricao": desc,
                    "travou": travou,
                }
            )
            atuais = proximos
            if travou:
                break

    return {
        "aceita": res_oficial.aceita,
        "motivo": res_oficial.motivo,
        "cadeia": cadeia,
        "operacoes": res_oficial.contador_operacoes,
        "tipo": af.tipo,
        "ehDeterministico": af.eh_deterministico(),
        "ehCompleto": af.eh_completo(),
        "modelo": modelo_dict,
        "simbolosTabela": [s or "ε" for s in simbolos_tabela],
        "tabela": tabela_transicoes,
        "passos": passos,
    }


def _simular_ap(dados_modelo: dict, cadeia_raw: str) -> dict:
    cadeia = _normalizar_cadeia(cadeia_raw)
    ap = AutomatoPilha.de_dict(dados_modelo)
    res = ap.executar(cadeia)

    passos_json: list[dict] = []
    estado_anterior: str | None = None

    for p in res.passos:
        pos_entrada = len(cadeia) - len(p.restante)
        transicao_obj = None
        op_resumo = p.operacao
        tipo_op = "inicio"

        if p.numero > 0:
            partes = p.operacao.split("   [", 1)
            op_resumo = partes[0].strip()
            m = TRANSICAO_AP_RE.search(p.operacao)
            if m:
                de, le, desemp, para, emp = [x.strip() for x in m.groups()]
                transicao_obj = {
                    "de": de,
                    "le": le,
                    "desempilha": desemp,
                    "para": para,
                    "empilha": emp,
                }
                des_vazio = desemp == "ε"
                emp_vazio = emp == "ε"
                if des_vazio and emp_vazio:
                    tipo_op = "keep"
                elif emp_vazio:
                    tipo_op = "pop"
                elif des_vazio or (emp != desemp and emp.endswith(desemp)):
                    tipo_op = "push"
                elif emp == desemp:
                    tipo_op = "keep"
                else:
                    tipo_op = "replace"

        passos_json.append(
            {
                "numero": p.numero,
                "estado": p.estado,
                "estadoAnterior": estado_anterior,
                "lido": p.lido,
                "posEntrada": pos_entrada,
                "restante": p.restante,
                "pilha": list(p.pilha),  # topo em índice 0
                "pilhaTexto": p.pilha or "ε",
                "operacao": op_resumo,
                "operacaoCompleta": p.operacao,
                "tipoOperacao": tipo_op,
                "transicao": transicao_obj,
            }
        )
        estado_anterior = p.estado

    if not passos_json:
        passos_json.append(
            {
                "numero": 0,
                "estado": ap.estado_inicial,
                "estadoAnterior": None,
                "lido": "-",
                "posEntrada": 0,
                "restante": cadeia,
                "pilha": [ap.simbolo_inicial_pilha],
                "pilhaTexto": ap.simbolo_inicial_pilha,
                "operacao": res.motivo,
                "operacaoCompleta": res.motivo,
                "tipoOperacao": "erro",
                "transicao": None,
            }
        )

    return {
        "aceita": res.aceita,
        "motivo": res.motivo,
        "cadeia": cadeia,
        "configuracoesExploradas": res.configuracoes_exploradas,
        "ehDeterministico": ap.eh_deterministico(),
        "aceitacao": ap.aceitacao,
        "modelo": {
            "tipo": "AP",
            "descricao": ap.descricao,
            "alfabeto": sorted(ap.alfabeto),
            "alfabeto_pilha": sorted(ap.alfabeto_pilha),
            "estados": sorted(ap.estados, key=lambda s: (s != ap.estado_inicial, s)),
            "estado_inicial": ap.estado_inicial,
            "simbolo_inicial_pilha": ap.simbolo_inicial_pilha,
            "estados_finais": sorted(ap.estados_finais),
            "aceitacao": ap.aceitacao,
            "transicoes": [
                {
                    "de": t.de,
                    "le": t.le or "ε",
                    "desempilha": t.desempilha or "ε",
                    "para": t.para,
                    "empilha": t.empilha or "ε",
                }
                for t in ap.transicoes
            ],
        },
        "passos": passos_json,
    }


def _simular_mt(dados_modelo: dict, cadeia_raw: str, max_passos: int = 2000) -> dict:
    cadeia = _normalizar_cadeia(cadeia_raw)
    max_passos = max(1, min(int(max_passos), 10_000))
    mt = MaquinaTuring.de_dict(dados_modelo)

    # Execução espelhada exatamente em MaquinaTuring.executar, preservando os índices da fita
    for i, a in enumerate(cadeia):
        if a not in mt.alfabeto:
            return {
                "aceita": False,
                "parou": True,
                "cadeia": cadeia,
                "motivo": f"símbolo '{a}' (posição {i}) ∉ Σ",
                "modo": mt.modo,
                "fitaFinal": cadeia,
                "saida": cadeia,
                "saidaUnaria": None,
                "numeroPassos": 0,
                "celulasUsadas": 0,
                "branco": mt.branco,
                "modelo": _mt_para_dict(mt),
                "passos": [
                    {
                        "numero": 0,
                        "estado": mt.estado_inicial,
                        "estadoAnterior": None,
                        "cabeca": 0,
                        "celulas": {str(idx): ch for idx, ch in enumerate(cadeia)},
                        "celulaEscrita": None,
                        "transicao": None,
                        "descricao": f"Erro: símbolo '{a}' na posição {i} não pertence a Σ.",
                    }
                ],
            }

    fita: dict[int, str] = {i: a for i, a in enumerate(cadeia)}
    cabeca = 0
    estado = mt.estado_inicial
    visitadas = {0}

    def _snapshot(num: int, est: str, est_ant: str | None, cab: int, cel_escrita: int | None, tr: dict | None, desc: str) -> dict:
        return {
            "numero": num,
            "estado": est,
            "estadoAnterior": est_ant,
            "cabeca": cab,
            "celulas": {str(k): v for k, v in sorted(fita.items())},
            "celulaEscrita": cel_escrita,
            "transicao": tr,
            "descricao": desc,
        }

    passos: list[dict] = [
        _snapshot(0, estado, None, cabeca, None, None, f"Configuração inicial: estado {estado}, cabeçote na posição 0.")
    ]

    aceita = False
    parou = False
    motivo = ""
    num_passos = 0

    for n in range(1, max_passos + 1):
        if estado in mt.estados_aceitacao:
            aceita, parou = True, True
            motivo = f"atingiu o estado de aceitação {estado}"
            num_passos = n - 1
            break
        if estado == mt.estado_rejeicao:
            aceita, parou = False, True
            motivo = f"atingiu o estado de rejeição {estado}"
            num_passos = n - 1
            break

        simbolo = fita.get(cabeca, mt.branco)
        t = mt.transicoes.get((estado, simbolo))
        if t is None:
            aceita, parou = False, True
            motivo = f"δ({estado}, {simbolo}) indefinida -> para e REJEITA"
            num_passos = n - 1
            break

        cel_escrita = cabeca
        estado_ant = estado
        if t.escreve == mt.branco:
            fita.pop(cabeca, None)
        else:
            fita[cabeca] = t.escreve

        cabeca += {"L": -1, "R": 1, "S": 0}[t.move]
        visitadas.add(cabeca)
        estado = t.para
        tr_dict = {
            "de": t.de,
            "le": t.le,
            "para": t.para,
            "escreve": t.escreve,
            "move": t.move,
        }
        passos.append(
            _snapshot(
                n,
                estado,
                estado_ant,
                cabeca,
                cel_escrita,
                tr_dict,
                f"δ({t.de}, {t.le}) = ({t.para}, {t.escreve}, {t.move})",
            )
        )
        num_passos = n
    else:
        if estado in mt.estados_aceitacao:
            aceita, parou = True, True
            motivo = f"atingiu o estado de aceitação {estado}"
        elif estado == mt.estado_rejeicao:
            aceita, parou = False, True
            motivo = f"atingiu o estado de rejeição {estado}"
        else:
            aceita, parou = False, False
            motivo = (
                f"NÃO PAROU em {max_passos} passos (limite). Pelo problema da parada, "
                "não é possível decidir em geral se ela pararia."
            )

    # Fita final sem colchetes (idêntico a MaquinaTuring._fita_str(..., marcar=False))
    if fita:
        ini = min(min(fita), cabeca)
        fim = max(max(fita), cabeca)
    else:
        ini = fim = cabeca
    fita_final = "".join(fita.get(i, mt.branco) for i in range(ini, fim + 1))
    saida = fita_final.strip(mt.branco)
    saida_unaria = decodificar_unario(saida) if (mt.modo == "transdutor" and set(saida) <= {"0"}) else None

    return {
        "aceita": aceita,
        "parou": parou,
        "cadeia": cadeia,
        "motivo": motivo,
        "modo": mt.modo,
        "fitaFinal": fita_final,
        "saida": saida,
        "saidaUnaria": saida_unaria,
        "numeroPassos": num_passos,
        "celulasUsadas": len(visitadas),
        "branco": mt.branco,
        "modelo": _mt_para_dict(mt),
        "passos": passos,
    }


def _mt_para_dict(mt: MaquinaTuring) -> dict:
    return {
        "tipo": "MT",
        "modo": mt.modo,
        "descricao": mt.descricao,
        "estados": sorted(mt.estados, key=lambda s: (s != mt.estado_inicial, s)),
        "alfabeto": sorted(mt.alfabeto),
        "alfabeto_fita": sorted(mt.alfabeto_fita),
        "branco": mt.branco,
        "estado_inicial": mt.estado_inicial,
        "estados_aceitacao": sorted(mt.estados_aceitacao),
        "estado_rejeicao": mt.estado_rejeicao,
        "transicoes": [
            {
                "de": t.de,
                "le": t.le,
                "para": t.para,
                "escreve": t.escreve,
                "move": t.move,
            }
            for t in mt.transicoes.values()
        ],
    }


class SimuladorHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[API] {self.address_string()} - {format % args}")

    def _send_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", "0"))
        bruto = self.rfile.read(tamanho) if tamanho > 0 else b"{}"
        return json.loads(bruto.decode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path == "/api/exemplos":
            self._send_json(_listar_exemplos())
            return

        # Serve frontend buildado (web/dist) se disponível
        if WEB_DIST_DIR.exists():
            rel = path.lstrip("/") or "index.html"
            alvo = (WEB_DIST_DIR / rel).resolve()
            if not str(alvo).startswith(str(WEB_DIST_DIR.resolve())) or not alvo.is_file():
                alvo = WEB_DIST_DIR / "index.html"
            if alvo.is_file():
                conteudo = alvo.read_bytes()
                mime, _ = mimetypes.guess_type(str(alvo))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.send_header("Content-Length", str(len(conteudo)))
                self.end_headers()
                self.wfile.write(conteudo)
                return

        self._send_json({"erro": f"Rota não encontrada: {path}"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/simular/af":
                res = _simular_af(
                    body["modelo"],
                    body.get("cadeia", ""),
                    bool(body.get("converterAfd", False)),
                )
                self._send_json(res)
                return
            if path == "/api/simular/ap":
                res = _simular_ap(body["modelo"], body.get("cadeia", ""))
                self._send_json(res)
                return
            if path == "/api/simular/mt":
                res = _simular_mt(
                    body["modelo"],
                    body.get("cadeia", ""),
                    body.get("maxPassos", 2000),
                )
                self._send_json(res)
                return
            self._send_json({"erro": f"Rota não encontrada: {path}"}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._send_json({"erro": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"erro": f"Erro interno: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor API do Simulador de Linguagens Formais")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    servidor = ThreadingHTTPServer((args.host, args.port), SimuladorHandler)
    print(f"Simulador API rodando em http://{args.host}:{args.port}")
    if WEB_DIST_DIR.exists():
        print(f"Interface React pronta em http://{args.host}:{args.port}")
    else:
        print("Para o frontend em desenvolvimento, rode: cd web && npm run dev")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        servidor.server_close()


if __name__ == "__main__":
    main()
