"""
MÓDULO 2 - AUTÔMATOS FINITOS (AFD, AFN e AFN-ε)
================================================

Definição formal (Sipser, def. 1.5 / 1.37):

    AFD  M = (Q, Σ, δ, q0, F)      δ : Q × Σ      -> Q
    AFN  N = (Q, Σ, δ, q0, F)      δ : Q × Σ_ε    -> P(Q)   (P = conjunto das partes)

* Q  : conjunto finito de estados
* Σ  : alfabeto de entrada
* δ  : função de transição
* q0 : estado inicial (q0 ∈ Q)
* F  : conjunto de estados finais (F ⊆ Q)

Algoritmos implementados
------------------------
1. Simulação de AFD ............ percorre a cadeia uma vez:            Θ(n)
2. Simulação de AFN/AFN-ε ...... mantém o CONJUNTO de estados ativos
                                 (simulação "em paralelo") + fecho-ε:  O(n · |Q|²)
3. Construção de subconjuntos .. AFN -> AFD equivalente:               O(2^|Q| · |Σ| · |Q|²)

Formato JSON aceito (exemplos em /exemplos):

    {
      "tipo": "AFD",                       # ou "AFN"
      "alfabeto": ["a", "b"],
      "estados": ["q0", "q1", "q2"],
      "estado_inicial": "q0",
      "estados_finais": ["q2"],
      "transicoes": [
        {"de": "q0", "simbolo": "a", "para": "q1"},
        {"de": "q1", "simbolo": "b", "para": ["q2"]},   # lista é aceita (AFN)
        {"de": "q1", "simbolo": "ε", "para": "q0"}       # ε só em AFN
      ]
    }
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import eh_epsilon

EPS = ""  # representação interna de ε


def _fmt_conjunto(estados: Iterable[str]) -> str:
    estados = sorted(estados)
    return "{" + ", ".join(estados) + "}" if estados else "∅"


@dataclass
class ResultadoAF:
    """Resultado de uma execução: aceita/rejeita + rastro passo a passo."""

    aceita: bool
    cadeia: str
    caminho: list[str]                 # sequência de estados (AFD) ou conjuntos (AFN)
    passos: list[str]                  # descrição textual de cada transição
    motivo: str = ""
    contador_operacoes: int = 0        # usado no Módulo 6 (medição empírica)

    def resumo(self) -> str:
        return " -> ".join(self.caminho) + "\n" + ("ACEITA" if self.aceita else "REJEITA")


@dataclass
class AutomatoFinito:
    estados: set[str]
    alfabeto: set[str]
    estado_inicial: str
    estados_finais: set[str]
    # δ(q, a) = conjunto de destinos. Para AFD cada conjunto tem 1 elemento.
    transicoes: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    tipo: str = "AFD"
    descricao: str = ""

    # ------------------------------------------------------------------ I/O
    @staticmethod
    def de_dict(dados: dict) -> "AutomatoFinito":
        transicoes: dict[tuple[str, str], set[str]] = {}
        for t in dados.get("transicoes", []):
            simbolo = EPS if eh_epsilon(t.get("simbolo", "")) else t["simbolo"]
            destinos = t["para"] if isinstance(t["para"], list) else [t["para"]]
            transicoes.setdefault((t["de"], simbolo), set()).update(destinos)

        af = AutomatoFinito(
            estados=set(dados["estados"]),
            alfabeto=set(dados["alfabeto"]),
            estado_inicial=dados["estado_inicial"],
            estados_finais=set(dados["estados_finais"]),
            transicoes=transicoes,
            tipo=dados.get("tipo", "AFD").upper(),
            descricao=dados.get("descricao", ""),
        )
        erros = af.validar()
        if erros:
            raise ValueError("Autômato inválido:\n  - " + "\n  - ".join(erros))
        return af

    @staticmethod
    def carregar_json(caminho: str | Path) -> "AutomatoFinito":
        with open(caminho, encoding="utf-8") as f:
            return AutomatoFinito.de_dict(json.load(f))

    def para_dict(self) -> dict:
        trans = []
        for (q, a), destinos in sorted(self.transicoes.items()):
            para = sorted(destinos)
            trans.append({"de": q, "simbolo": a or "ε",
                          "para": para[0] if self.tipo == "AFD" else para})
        return {
            "tipo": self.tipo, "descricao": self.descricao,
            "alfabeto": sorted(self.alfabeto), "estados": sorted(self.estados),
            "estado_inicial": self.estado_inicial,
            "estados_finais": sorted(self.estados_finais), "transicoes": trans,
        }

    # ------------------------------------------------------------ validação
    def validar(self) -> list[str]:
        """Confere se a 5-upla é consistente com a definição formal."""
        erros = []
        if self.estado_inicial not in self.estados:
            erros.append(f"estado inicial '{self.estado_inicial}' não pertence a Q")
        for f in self.estados_finais - self.estados:
            erros.append(f"estado final '{f}' não pertence a Q")
        for (q, a), destinos in self.transicoes.items():
            if q not in self.estados:
                erros.append(f"δ({q}, {a or 'ε'}): estado de origem '{q}' não pertence a Q")
            if a != EPS and a not in self.alfabeto:
                erros.append(f"δ({q}, {a}): símbolo '{a}' não pertence a Σ")
            for d in destinos - self.estados:
                erros.append(f"δ({q}, {a or 'ε'}): destino '{d}' não pertence a Q")
        if self.tipo == "AFD":
            for (q, a), destinos in self.transicoes.items():
                if a == EPS:
                    erros.append(f"AFD não pode ter transição ε (δ({q}, ε))")
                elif len(destinos) > 1:
                    erros.append(f"AFD não pode ter mais de um destino em δ({q}, {a}) = "
                                 f"{_fmt_conjunto(destinos)}")
        return erros

    def eh_deterministico(self) -> bool:
        return all(a != EPS and len(d) == 1 for (_, a), d in self.transicoes.items())

    def eh_completo(self) -> bool:
        """AFD completo: δ definida para todo par (q, a) ∈ Q × Σ."""
        return all((q, a) in self.transicoes for q in self.estados for a in self.alfabeto)

    # ------------------------------------------------------------- fecho-ε
    def fecho_epsilon(self, estados: Iterable[str]) -> frozenset[str]:
        """
        E(S) = estados alcançáveis a partir de S usando apenas transições ε.
        Busca em profundidade/largura no grafo de transições ε: O(|Q| + |δ|).
        """
        fecho = set(estados)
        pilha = list(estados)
        while pilha:
            q = pilha.pop()
            for r in self.transicoes.get((q, EPS), ()):
                if r not in fecho:
                    fecho.add(r)
                    pilha.append(r)
        return frozenset(fecho)

    def mover(self, estados: Iterable[str], simbolo: str) -> frozenset[str]:
        destino = set()
        for q in estados:
            destino |= self.transicoes.get((q, simbolo), set())
        return frozenset(destino)

    # ------------------------------------------------------------- execução
    def executar(self, w: str, registrar: bool = True) -> ResultadoAF:
        """
        Executa a cadeia w. Com registrar=False o rastro textual não é montado
        (usado no Módulo 6 para medir apenas o custo do algoritmo).
        """
        if self.tipo == "AFD":
            return self._executar_afd(w, registrar)
        return self._executar_afn(w, registrar)

    def _executar_afd(self, w: str, registrar: bool = True) -> ResultadoAF:
        """Simulação de AFD: um único estado corrente.  Θ(n), n = |w|."""
        atual = self.estado_inicial
        caminho = [atual]
        passos = [f"Início: estado {atual}, entrada '{w or 'ε'}'"]
        ops = 0
        for i, a in enumerate(w):
            ops += 1
            if a not in self.alfabeto:
                return ResultadoAF(False, w, caminho, passos,
                                   f"símbolo '{a}' (posição {i}) não pertence a Σ", ops)
            destinos = self.transicoes.get((atual, a))
            if not destinos:
                passos.append(f"Passo {i + 1}: δ({atual}, {a}) indefinida -> a máquina TRAVA")
                return ResultadoAF(False, w, caminho, passos,
                                   f"transição δ({atual}, {a}) não definida", ops)
            proximo = next(iter(destinos))
            if registrar:
                passos.append(f"Passo {i + 1}: δ({atual}, {a}) = {proximo}    "
                              f"[lido: {w[:i + 1]} | resta: {w[i + 1:] or 'ε'}]")
            atual = proximo
            if registrar:
                caminho.append(atual)

        aceita = atual in self.estados_finais
        motivo = (f"terminou em {atual} ∈ F" if aceita
                  else f"terminou em {atual} ∉ F = {_fmt_conjunto(self.estados_finais)}")
        return ResultadoAF(aceita, w, caminho, passos, motivo, ops)

    def _executar_afn(self, w: str, registrar: bool = True) -> ResultadoAF:
        """
        Simulação de AFN-ε pelo método dos conjuntos de estados ativos:
            S0 = E({q0});   S_{i+1} = E( ∪_{q ∈ S_i} δ(q, a_i) )
        Aceita se S_n ∩ F ≠ ∅.
        """
        atuais = self.fecho_epsilon({self.estado_inicial})
        caminho = [_fmt_conjunto(atuais)]
        passos = [f"Início: E({{{self.estado_inicial}}}) = {_fmt_conjunto(atuais)}"]
        ops = len(atuais)
        for i, a in enumerate(w):
            if a not in self.alfabeto:
                return ResultadoAF(False, w, caminho, passos,
                                   f"símbolo '{a}' (posição {i}) não pertence a Σ", ops)
            movidos = self.mover(atuais, a)
            proximos = self.fecho_epsilon(movidos)
            ops += len(atuais) + len(proximos)
            if registrar:
                passos.append(
                    f"Passo {i + 1}: lê '{a}': δ({_fmt_conjunto(atuais)}, {a}) = "
                    f"{_fmt_conjunto(movidos)}  ->  fecho-ε = {_fmt_conjunto(proximos)}"
                )
            atuais = proximos
            if registrar:
                caminho.append(_fmt_conjunto(atuais))
            if not atuais:
                passos.append("Conjunto de estados ativos vazio: todos os ramos morreram.")
                return ResultadoAF(False, w, caminho, passos,
                                   "nenhum ramo de computação sobreviveu", ops)

        finais_ativos = atuais & self.estados_finais
        aceita = bool(finais_ativos)
        motivo = (f"estados ativos ∩ F = {_fmt_conjunto(finais_ativos)} ≠ ∅" if aceita
                  else f"estados ativos {_fmt_conjunto(atuais)} ∩ F = ∅")
        return ResultadoAF(aceita, w, caminho, passos, motivo, ops)

    def aceita(self, w: str) -> bool:
        return self.executar(w).aceita

    # ------------------------------------------- AFN -> AFD (subconjuntos)
    def para_afd(self) -> "AutomatoFinito":
        """
        Construção de subconjuntos (Rabin-Scott). Cada estado do AFD é um
        conjunto de estados do AFN. Só os subconjuntos ALCANÇÁVEIS são gerados.
        Pior caso: 2^|Q| estados.
        """
        def nome(conj: frozenset[str]) -> str:
            return _fmt_conjunto(conj)

        inicio = self.fecho_epsilon({self.estado_inicial})
        fila = deque([inicio])
        visitados = {inicio}
        transicoes: dict[tuple[str, str], set[str]] = {}
        simbolos = sorted(self.alfabeto)
        while fila:
            S = fila.popleft()
            for a in simbolos:
                T = self.fecho_epsilon(self.mover(S, a))
                transicoes[(nome(S), a)] = {nome(T)}
                if T not in visitados:
                    visitados.add(T)
                    fila.append(T)

        return AutomatoFinito(
            estados={nome(S) for S in visitados},
            alfabeto=set(self.alfabeto),
            estado_inicial=nome(inicio),
            estados_finais={nome(S) for S in visitados if S & self.estados_finais},
            transicoes=transicoes,
            tipo="AFD",
            descricao=f"AFD equivalente (construção de subconjuntos) de: {self.descricao}",
        )

    # ------------------------------------------------------------ exibição
    def tabela_transicoes(self) -> str:
        """Tabela de transição no formato visto em sala ( -> inicial, * final )."""
        simbolos = sorted(self.alfabeto)
        if any(a == EPS for (_, a) in self.transicoes):
            simbolos.append(EPS)
        cab = ["δ"] + [s or "ε" for s in simbolos]
        linhas = []
        for q in sorted(self.estados, key=lambda s: (s != self.estado_inicial, s)):
            marca = ("->" if q == self.estado_inicial else "  ") + ("*" if q in self.estados_finais else " ")
            celulas = [f"{marca}{q}"]
            for a in simbolos:
                d = self.transicoes.get((q, a))
                if not d:
                    celulas.append("-")
                elif self.tipo == "AFD":
                    celulas.append(next(iter(d)))
                else:
                    celulas.append(_fmt_conjunto(d))
            linhas.append(celulas)
        larguras = [max(len(str(l[i])) for l in [cab] + linhas) for i in range(len(cab))]
        fmt = lambda cel: " | ".join(str(c).ljust(larguras[i]) for i, c in enumerate(cel))
        sep = "-+-".join("-" * w for w in larguras)
        return "\n".join([fmt(cab), sep] + [fmt(l) for l in linhas])

    def __str__(self) -> str:
        return (f"{self.tipo}: {self.descricao}\n"
                f"Q  = {_fmt_conjunto(self.estados)}\n"
                f"Σ  = {_fmt_conjunto(self.alfabeto)}\n"
                f"q0 = {self.estado_inicial}\n"
                f"F  = {_fmt_conjunto(self.estados_finais)}\n"
                f"{self.tabela_transicoes()}")
