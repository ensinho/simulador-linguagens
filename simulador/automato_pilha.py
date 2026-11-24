"""
MÓDULO 4 - AUTÔMATO COM PILHA (AP)
==================================

Definição formal (Sipser, def. 2.13):   P = (Q, Σ, Γ, δ, q0, Z0, F)

* Q  : estados                 * Γ  : alfabeto da pilha
* Σ  : alfabeto de entrada     * Z0 : símbolo inicial da pilha (marca o "fundo")
* δ  : Q × Σ_ε × Γ_ε  ->  P(Q × Γ*)
* q0 : estado inicial          * F  : estados finais

Uma transição  δ(q, a, X) ∋ (p, γ)  significa:
    "no estado q, lendo a (ou ε) com X no topo da pilha (ou ε = não olha o topo),
     vá para p, DESEMPILHE X e EMPILHE γ".
Convenção: γ é escrito com o TOPO À ESQUERDA (γ = "AZ" -> A fica no topo).

O AP é NÃO DETERMINÍSTICO em geral, então a simulação explora a árvore de
configurações (estado, posição na entrada, conteúdo da pilha) com busca em
largura (BFS). Para APs determinísticos (como o de aⁿbⁿ) a árvore é um
caminho único e o custo é Θ(n).

Critérios de aceitação suportados:
    "estado_final" (padrão)  -> entrada toda lida E estado ∈ F
    "pilha_vazia"            -> entrada toda lida E pilha vazia

Formato JSON (ver exemplos/ap_anbn.json):
    {"de": "q0", "le": "a", "desempilha": "Z", "para": "q0", "empilha": "AZ"}
    Use "ε" (ou "") em "le", "desempilha" ou "empilha" para a cadeia vazia.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from . import eh_epsilon

EPS = ""


@dataclass(frozen=True)
class TransicaoAP:
    de: str
    le: str              # "" = ε
    desempilha: str      # "" = ε (não consulta o topo)
    para: str
    empilha: str         # "" = ε (não empilha nada); topo à esquerda

    def __str__(self) -> str:
        return (f"δ({self.de}, {self.le or 'ε'}, {self.desempilha or 'ε'}) = "
                f"({self.para}, {self.empilha or 'ε'})")

    def operacao_pilha(self) -> str:
        """Descreve a operação em termos de EMPILHAR / DESEMPILHAR."""
        X, g = self.desempilha, self.empilha
        if not X and not g:
            return "pilha inalterada"
        if not X:
            return f"empilha {g}"
        if not g:
            return f"desempilha {X}"
        if g == X:
            return f"mantém {X} no topo"
        if g.endswith(X):
            return f"empilha {g[:-len(X)]}"
        return f"desempilha {X}, empilha {g}"


@dataclass(frozen=True)
class Configuracao:
    """Descrição instantânea (estado, entrada restante, pilha)."""
    estado: str
    posicao: int
    pilha: str           # topo = pilha[0]


@dataclass
class PassoAP:
    numero: int
    estado: str
    lido: str
    restante: str
    pilha: str
    operacao: str


@dataclass
class ResultadoAP:
    aceita: bool
    cadeia: str
    passos: list[PassoAP]
    motivo: str
    configuracoes_exploradas: int = 0

    def tabela(self) -> str:
        cab = ["Passo", "Estado", "Leitura", "Entrada restante", "Pilha (topo à esq.)", "Operação"]
        linhas = [[str(p.numero), p.estado, p.lido, p.restante or "ε", p.pilha or "ε", p.operacao]
                  for p in self.passos]
        larg = [max(len(l[i]) for l in [cab] + linhas) for i in range(len(cab))]
        fmt = lambda l: " | ".join(c.ljust(larg[i]) for i, c in enumerate(l))
        return "\n".join([fmt(cab), "-+-".join("-" * x for x in larg)] + [fmt(l) for l in linhas])


@dataclass
class AutomatoPilha:
    estados: set[str]
    alfabeto: set[str]
    alfabeto_pilha: set[str]
    estado_inicial: str
    simbolo_inicial_pilha: str
    estados_finais: set[str]
    transicoes: list[TransicaoAP] = field(default_factory=list)
    aceitacao: str = "estado_final"
    descricao: str = ""

    # ------------------------------------------------------------------ I/O
    @staticmethod
    def de_dict(dados: dict) -> "AutomatoPilha":
        def norm(s):
            return EPS if s is None or eh_epsilon(s) else s

        trans = [TransicaoAP(t["de"], norm(t.get("le")), norm(t.get("desempilha")),
                             t["para"], norm(t.get("empilha")))
                 for t in dados["transicoes"]]
        ap = AutomatoPilha(
            estados=set(dados["estados"]),
            alfabeto=set(dados["alfabeto"]),
            alfabeto_pilha=set(dados["alfabeto_pilha"]),
            estado_inicial=dados["estado_inicial"],
            simbolo_inicial_pilha=dados.get("simbolo_inicial_pilha", "Z"),
            estados_finais=set(dados.get("estados_finais", [])),
            transicoes=trans,
            aceitacao=dados.get("aceitacao", "estado_final"),
            descricao=dados.get("descricao", ""),
        )
        erros = ap.validar()
        if erros:
            raise ValueError("AP inválido:\n  - " + "\n  - ".join(erros))
        return ap

    @staticmethod
    def carregar_json(caminho: str | Path) -> "AutomatoPilha":
        with open(caminho, encoding="utf-8") as f:
            return AutomatoPilha.de_dict(json.load(f))

    def validar(self) -> list[str]:
        erros = []
        if self.estado_inicial not in self.estados:
            erros.append(f"estado inicial '{self.estado_inicial}' ∉ Q")
        if self.simbolo_inicial_pilha not in self.alfabeto_pilha:
            erros.append(f"símbolo inicial da pilha '{self.simbolo_inicial_pilha}' ∉ Γ")
        if self.aceitacao not in ("estado_final", "pilha_vazia"):
            erros.append("aceitacao deve ser 'estado_final' ou 'pilha_vazia'")
        for f in self.estados_finais - self.estados:
            erros.append(f"estado final '{f}' ∉ Q")
        for t in self.transicoes:
            if t.de not in self.estados or t.para not in self.estados:
                erros.append(f"{t}: estado inexistente")
            if t.le and t.le not in self.alfabeto:
                erros.append(f"{t}: '{t.le}' ∉ Σ")
            for s in t.desempilha + t.empilha:
                if s not in self.alfabeto_pilha:
                    erros.append(f"{t}: símbolo de pilha '{s}' ∉ Γ")
        return erros

    def eh_deterministico(self) -> bool:
        """
        APD: para cada (q, a, X) no máximo uma transição aplicável, e se existe
        transição com ε na entrada, não pode haver outra lendo símbolo com o mesmo topo.
        """
        for i, t1 in enumerate(self.transicoes):
            for t2 in self.transicoes[i + 1:]:
                if t1.de != t2.de:
                    continue
                le_conflita = t1.le == t2.le or not t1.le or not t2.le
                topo_conflita = (t1.desempilha == t2.desempilha
                                 or not t1.desempilha or not t2.desempilha)
                if le_conflita and topo_conflita:
                    return False
        return True

    # ------------------------------------------------------------- execução
    def _aceitante(self, c: Configuracao, n: int) -> bool:
        if c.posicao != n:
            return False
        if self.aceitacao == "pilha_vazia":
            return c.pilha == ""
        return c.estado in self.estados_finais

    def _sucessores(self, c: Configuracao, w: str):
        for t in self.transicoes:
            if t.de != c.estado:
                continue
            if t.le:
                if c.posicao >= len(w) or w[c.posicao] != t.le:
                    continue
            if t.desempilha and not c.pilha.startswith(t.desempilha):
                continue
            nova_pilha = t.empilha + c.pilha[len(t.desempilha):]
            yield t, Configuracao(t.para, c.posicao + len(t.le), nova_pilha)

    def executar(self, w: str, max_configuracoes: int = 100_000,
                 max_pilha: int | None = None) -> ResultadoAP:
        """
        BFS na árvore de computações. Limites evitam laços infinitos de
        transições ε que só empilham (a pilha cresceria sem fim).
        """
        for i, a in enumerate(w):
            if a not in self.alfabeto:
                return ResultadoAP(False, w, [], f"símbolo '{a}' (posição {i}) ∉ Σ")

        n = len(w)
        max_pilha = max_pilha if max_pilha is not None else 2 * n + 10
        inicio = Configuracao(self.estado_inicial, 0, self.simbolo_inicial_pilha)
        pai: dict[Configuracao, tuple[Configuracao, TransicaoAP] | None] = {inicio: None}
        fila = deque([inicio])
        melhor = inicio      # configuração que mais avançou (para explicar rejeição)
        exploradas = 0

        while fila:
            c = fila.popleft()
            exploradas += 1
            if self._aceitante(c, n):
                return ResultadoAP(True, w, self._rastro(pai, c, w),
                                   self._motivo_aceite(c), exploradas)
            if (c.posicao, -len(c.pilha)) > (melhor.posicao, -len(melhor.pilha)):
                melhor = c
            if exploradas >= max_configuracoes:
                break
            for t, prox in self._sucessores(c, w):
                if prox not in pai and len(prox.pilha) <= max_pilha:
                    pai[prox] = (c, t)
                    fila.append(prox)

        passos = self._rastro(pai, melhor, w)
        if melhor.posicao < n:
            motivo = (f"nenhuma transição aplicável em ({melhor.estado}, "
                      f"'{w[melhor.posicao]}', topo={melhor.pilha[:1] or 'ε'}) - "
                      f"a computação mais longa leu apenas '{w[:melhor.posicao] or 'ε'}'")
        elif self.aceitacao == "pilha_vazia":
            motivo = f"entrada lida, mas a pilha não esvaziou (pilha = {melhor.pilha or 'ε'})"
        else:
            motivo = f"entrada lida, mas nenhum ramo terminou em estado final (F = {sorted(self.estados_finais)})"
        return ResultadoAP(False, w, passos, motivo, exploradas)

    def aceita(self, w: str) -> bool:
        return self.executar(w).aceita

    def _motivo_aceite(self, c: Configuracao) -> str:
        if self.aceitacao == "pilha_vazia":
            return "entrada consumida e pilha vazia"
        return f"entrada consumida e estado {c.estado} ∈ F"

    def _rastro(self, pai, final: Configuracao, w: str) -> list[PassoAP]:
        cadeia = []
        c = final
        while pai[c] is not None:
            anterior, t = pai[c]
            cadeia.append((c, t))
            c = anterior
        cadeia.reverse()
        passos = [PassoAP(0, c.estado, "-", w, c.pilha, "configuração inicial")]
        for i, (conf, t) in enumerate(cadeia, start=1):
            passos.append(PassoAP(i, conf.estado, t.le or "ε", w[conf.posicao:],
                                  conf.pilha, f"{t.operacao_pilha()}   [{t}]"))
        return passos

    def __str__(self) -> str:
        linhas = [f"AP: {self.descricao}",
                  f"Q = {sorted(self.estados)}   Σ = {sorted(self.alfabeto)}   Γ = {sorted(self.alfabeto_pilha)}",
                  f"q0 = {self.estado_inicial}   Z0 = {self.simbolo_inicial_pilha}   "
                  f"F = {sorted(self.estados_finais)}   aceitação por {self.aceitacao.replace('_', ' ')}",
                  "δ:"]
        linhas += [f"  {t}" for t in self.transicoes]
        return "\n".join(linhas)
