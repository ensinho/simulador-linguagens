"""
MÓDULO 1 - LINGUAGENS FORMAIS
=============================

Conceitos (Menezes, cap. 2; Sipser, cap. 0):

* Alfabeto (Σ): conjunto finito e não vazio de símbolos.
* Cadeia (palavra) sobre Σ: sequência finita de símbolos de Σ.
  A cadeia vazia é denotada por ε (ou λ) e tem tamanho 0.
* Σ*  : conjunto de TODAS as cadeias sobre Σ, incluindo ε  (fecho de Kleene).
* Σ+  : Σ* - {ε}                                           (fecho positivo).
* Σⁿ  : cadeias de tamanho exatamente n.
* Linguagem L sobre Σ: qualquer subconjunto de Σ*  (L ⊆ Σ*).

Como Σ* e Σ+ são conjuntos INFINITOS (sempre que Σ ≠ ∅), o programa não
consegue "calcular" o conjunto inteiro. O que fazemos é ENUMERÁ-LOS em
ordem canônica (primeiro por tamanho, depois lexicográfica) até um tamanho
máximo informado pelo usuário. Isso mostra que Σ* é enumerável.

Simplificação adotada: cada símbolo do alfabeto é um único caractere
(ex.: Σ = {a, b}, Σ = {0, 1, #}). Assim a cadeia "abba" é lida caractere a
caractere.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator

from . import eh_epsilon

EPSILON = "ε"


def formatar_cadeia(w: str) -> str:
    """Mostra ε no lugar da cadeia vazia."""
    return w if w else EPSILON


# ---------------------------------------------------------------------------
# Alfabeto
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Alfabeto:
    """Σ - conjunto finito e não vazio de símbolos (1 caractere cada)."""

    simbolos: frozenset[str]

    @staticmethod
    def de_texto(texto: str) -> "Alfabeto":
        """
        Constrói Σ a partir de um texto como "a,b", "{a, b}" ou "a b".
        """
        limpo = texto.strip().strip("{}")
        partes = [p.strip() for p in re.split(r"[,\s]+", limpo) if p.strip()]
        return Alfabeto.de_lista(partes)

    @staticmethod
    def de_lista(simbolos: Iterable[str]) -> "Alfabeto":
        simbolos = list(simbolos)
        if not simbolos:
            raise ValueError("Um alfabeto deve ser NÃO vazio.")
        for s in simbolos:
            if len(s) != 1:
                raise ValueError(
                    f"Símbolo inválido '{s}': cada símbolo deve ter exatamente 1 caractere."
                )
            if eh_epsilon(s) or s == EPSILON:
                raise ValueError("ε não pode ser símbolo do alfabeto (é a cadeia vazia).")
        return Alfabeto(frozenset(simbolos))

    # -- operações básicas -------------------------------------------------
    def ordenado(self) -> list[str]:
        return sorted(self.simbolos)

    def __contains__(self, simbolo: str) -> bool:
        return simbolo in self.simbolos

    def __len__(self) -> int:
        return len(self.simbolos)

    def __str__(self) -> str:
        return "{" + ", ".join(self.ordenado()) + "}"

    def validar_cadeia(self, w: str) -> tuple[bool, list[tuple[int, str]]]:
        """
        Verifica se w ∈ Σ*. Retorna (valida, lista_de_simbolos_invalidos),
        onde cada inválido é (posição, símbolo).   Custo: Θ(|w|).
        """
        invalidos = [(i, c) for i, c in enumerate(w) if c not in self.simbolos]
        return (not invalidos, invalidos)

    def pertence(self, w: str) -> bool:
        """
        w ∈ Σ* ?  Para no PRIMEIRO símbolo inválido (curto-circuito):
        melhor caso Θ(1), pior caso Θ(|w|).
        """
        return all(c in self.simbolos for c in w)

    # -- Σⁿ, Σ*, Σ+ ---------------------------------------------------------
    def sigma_n(self, n: int) -> Iterator[str]:
        """Σⁿ: todas as cadeias de tamanho exatamente n.  |Σⁿ| = |Σ|ⁿ."""
        for tupla in itertools.product(self.ordenado(), repeat=n):
            yield "".join(tupla)

    def sigma_estrela(self, tamanho_max: int) -> Iterator[str]:
        """Σ* = Σ⁰ ∪ Σ¹ ∪ Σ² ∪ ...   (enumerado até tamanho_max)."""
        for n in range(0, tamanho_max + 1):
            yield from self.sigma_n(n)

    def sigma_mais(self, tamanho_max: int) -> Iterator[str]:
        """Σ+ = Σ¹ ∪ Σ² ∪ ...   = Σ* - {ε}  (enumerado até tamanho_max)."""
        for n in range(1, tamanho_max + 1):
            yield from self.sigma_n(n)

    def quantidade_sigma_estrela(self, tamanho_max: int) -> int:
        """|Σ⁰ ∪ ... ∪ Σᵏ| = Σ_{n=0..k} |Σ|ⁿ  (série geométrica)."""
        return sum(len(self) ** n for n in range(tamanho_max + 1))


# ---------------------------------------------------------------------------
# Operações sobre cadeias
# ---------------------------------------------------------------------------
def tamanho(w: str) -> int:
    """|w| - número de símbolos da cadeia.  |ε| = 0."""
    return len(w)


def concatenar(u: str, v: str) -> str:
    """u·v - concatenação. Propriedades: |uv| = |u|+|v|, εw = wε = w."""
    return u + v


def potencia(w: str, n: int) -> str:
    """wⁿ = w·w·...·w (n vezes); w⁰ = ε."""
    if n < 0:
        raise ValueError("Expoente deve ser ≥ 0.")
    return w * n


def reverso(w: str) -> str:
    """wᴿ - cadeia reversa."""
    return w[::-1]


def prefixos(w: str) -> list[str]:
    return [w[:i] for i in range(len(w) + 1)]


def sufixos(w: str) -> list[str]:
    return [w[i:] for i in range(len(w) + 1)]


def subcadeias(w: str) -> list[str]:
    """Todas as subcadeias distintas (inclui ε)."""
    vistas = {""}
    for i in range(len(w)):
        for j in range(i + 1, len(w) + 1):
            vistas.add(w[i:j])
    return sorted(vistas, key=lambda s: (len(s), s))


# ---------------------------------------------------------------------------
# Linguagem
# ---------------------------------------------------------------------------
@dataclass
class Linguagem:
    """
    Uma linguagem L ⊆ Σ*.

    Pode ser definida de duas formas:
      1. Por ENUMERAÇÃO (linguagem finita):   L = {ab, ba, aabb}
      2. Por um PREDICADO de pertinência (linguagem possivelmente infinita),
         por exemplo uma expressão regular ou uma função Python.
    """

    alfabeto: Alfabeto
    nome: str = "L"
    descricao: str = ""
    palavras: frozenset[str] | None = None          # linguagem finita
    predicado: Callable[[str], bool] | None = field(default=None, repr=False)

    # -- construtores -------------------------------------------------------
    @staticmethod
    def finita(alfabeto: Alfabeto, palavras: Iterable[str], nome: str = "L") -> "Linguagem":
        conjunto = set()
        for p in palavras:
            p = "" if eh_epsilon(p) else p
            ok, inval = alfabeto.validar_cadeia(p)
            if not ok:
                raise ValueError(
                    f"A palavra '{p}' usa símbolos fora de Σ: {[s for _, s in inval]}"
                )
            conjunto.add(p)
        return Linguagem(alfabeto, nome, "{" + ", ".join(
            formatar_cadeia(p) for p in sorted(conjunto, key=lambda s: (len(s), s))) + "}",
            palavras=frozenset(conjunto))

    @staticmethod
    def por_regex(alfabeto: Alfabeto, regex: str, nome: str = "L") -> "Linguagem":
        """Define L pela expressão regular (sintaxe do Python: (a|b)*abb, a*b+ ...)."""
        padrao = re.compile(regex)
        return Linguagem(alfabeto, nome, f"ER: {regex}",
                         predicado=lambda w: padrao.fullmatch(w) is not None)

    @staticmethod
    def por_predicado(alfabeto: Alfabeto, predicado: Callable[[str], bool],
                      descricao: str, nome: str = "L") -> "Linguagem":
        return Linguagem(alfabeto, nome, descricao, predicado=predicado)

    # -- pertinência -------------------------------------------------------
    def pertence(self, w: str) -> bool:
        """w ∈ L ?  (exige também w ∈ Σ*)."""
        if not self.alfabeto.pertence(w):
            return False
        if self.palavras is not None:
            return w in self.palavras
        return bool(self.predicado and self.predicado(w))

    def eh_finita(self) -> bool:
        return self.palavras is not None

    def enumerar(self, tamanho_max: int) -> list[str]:
        """Palavras de L com |w| ≤ tamanho_max, em ordem canônica."""
        if self.palavras is not None:
            return sorted((p for p in self.palavras if len(p) <= tamanho_max),
                          key=lambda s: (len(s), s))
        return [w for w in self.alfabeto.sigma_estrela(tamanho_max) if self.pertence(w)]

    # -- operações sobre linguagens ---------------------------------------
    def uniao(self, outra: "Linguagem") -> "Linguagem":
        sigma = Alfabeto(self.alfabeto.simbolos | outra.alfabeto.simbolos)
        if self.eh_finita() and outra.eh_finita():
            return Linguagem.finita(sigma, self.palavras | outra.palavras,
                                    f"{self.nome}∪{outra.nome}")
        return Linguagem.por_predicado(
            sigma, lambda w: self.pertence(w) or outra.pertence(w),
            f"{self.nome} ∪ {outra.nome}", f"{self.nome}∪{outra.nome}")

    def concatenacao(self, outra: "Linguagem") -> "Linguagem":
        """L1·L2 = { uv | u ∈ L1 e v ∈ L2 }."""
        sigma = Alfabeto(self.alfabeto.simbolos | outra.alfabeto.simbolos)
        if self.eh_finita() and outra.eh_finita():
            return Linguagem.finita(sigma, {u + v for u in self.palavras for v in outra.palavras},
                                    f"{self.nome}{outra.nome}")
        # Pertinência: existe um ponto de corte i tal que w[:i] ∈ L1 e w[i:] ∈ L2.
        return Linguagem.por_predicado(
            sigma,
            lambda w: any(self.pertence(w[:i]) and outra.pertence(w[i:]) for i in range(len(w) + 1)),
            f"{self.nome}·{outra.nome}", f"{self.nome}{outra.nome}")

    def fecho_kleene(self) -> "Linguagem":
        """L* = {ε} ∪ L ∪ LL ∪ LLL ...  (pertinência por programação dinâmica)."""
        def pertence_estrela(w: str) -> bool:
            # alcancavel[i] = True se w[:i] ∈ L*
            alcancavel = [False] * (len(w) + 1)
            alcancavel[0] = True
            for j in range(1, len(w) + 1):
                alcancavel[j] = any(alcancavel[i] and self.pertence(w[i:j]) for i in range(j))
            return alcancavel[len(w)]

        return Linguagem.por_predicado(self.alfabeto, pertence_estrela,
                                       f"({self.nome})*", f"{self.nome}*")

    def __str__(self) -> str:
        return f"{self.nome} = {self.descricao} sobre Σ = {self.alfabeto}"
