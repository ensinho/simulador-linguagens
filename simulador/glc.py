"""
MÓDULO 3 - GRAMÁTICAS LIVRES DE CONTEXTO (GLC)
===============================================

Definição formal (Sipser, def. 2.2):   G = (V, Σ, R, S)

* V : conjunto finito de VARIÁVEIS (não terminais)
* Σ : conjunto finito de TERMINAIS (V ∩ Σ = ∅)
* R : conjunto de PRODUÇÕES (regras) da forma  A -> α,  com A ∈ V e α ∈ (V ∪ Σ)*
* S : símbolo inicial (S ∈ V)

L(G) = { w ∈ Σ* | S ⇒* w }

Algoritmos implementados
------------------------
1. Anuláveis e tamanho mínimo derivável .... ponto fixo:            O(|V| · |G|)
2. Forma Normal de Chomsky (FNC) ........... START, DEL, UNIT,
                                             TERM, BIN (Sipser 2.9)
3. CYK (Cocke-Younger-Kasami) .............. decide w ∈ L(G):        Θ(n³ · |G|)
4. Derivação mais à esquerda passo a passo . busca em largura (BFS)
                                             sobre formas sentenciais com PODA.
                                             Exponencial no pior caso.
5. Árvore de derivação ..................... reconstruída a partir dos passos.

Estratégia: primeiro o CYK DECIDE a pertinência (sempre termina, polinomial);
só se a cadeia for aceita é que a BFS procura a derivação para mostrá-la ao
usuário. Assim a BFS nunca roda "para sempre" atrás de uma derivação que não
existe.

Formato JSON:
    {
      "variaveis": ["S"],
      "terminais": ["a", "b"],
      "simbolo_inicial": "S",
      "producoes": { "S": ["aSb", "λ"] }
    }
Cada corpo de produção é lido caractere a caractere ("aSb" = a, S, b).
Use espaços para símbolos com mais de um caractere ("S1 a S1").
λ, ε ou "" representam a cadeia vazia.

Formato texto (modo interativo):
    S -> aSb | λ
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from . import eh_epsilon

Corpo = tuple[str, ...]           # lado direito de uma produção ( () = λ )
LAMBDA = "λ"
INF = float("inf")


def _corpo_str(corpo: Corpo) -> str:
    if not corpo:
        return LAMBDA
    if all(len(s) == 1 for s in corpo):
        return "".join(corpo)
    return " ".join(corpo)


def _parse_corpo(texto: str) -> Corpo:
    texto = texto.strip()
    if eh_epsilon(texto):
        return ()
    if " " in texto:
        return tuple(p for p in texto.split() if not eh_epsilon(p))
    return tuple(c for c in texto if not eh_epsilon(c))


# ---------------------------------------------------------------------------
# Estruturas auxiliares
# ---------------------------------------------------------------------------
@dataclass
class PassoDerivacao:
    forma_antes: Corpo
    posicao: int                 # índice da variável substituída
    variavel: str
    corpo: Corpo                 # produção aplicada
    forma_depois: Corpo


@dataclass
class No:
    """Nó da árvore de derivação."""
    simbolo: str
    filhos: list["No"] = field(default_factory=list)

    def desenhar(self, prefixo: str = "", ultimo: bool = True, raiz: bool = True) -> list[str]:
        linhas = [self.simbolo] if raiz else [prefixo + ("└── " if ultimo else "├── ") + self.simbolo]
        novo_prefixo = "" if raiz else prefixo + ("    " if ultimo else "│   ")
        for i, f in enumerate(self.filhos):
            linhas += f.desenhar(novo_prefixo, i == len(self.filhos) - 1, False)
        return linhas

    def fronteira(self) -> str:
        """Concatenação das folhas (deve ser igual à cadeia derivada)."""
        if not self.filhos:
            return "" if self.simbolo == LAMBDA else self.simbolo
        return "".join(f.fronteira() for f in self.filhos)


@dataclass
class ResultadoGLC:
    aceita: bool
    cadeia: str
    passos: list[PassoDerivacao]
    arvore: No | None
    motivo: str
    formas_exploradas: int = 0
    operacoes_cyk: int = 0

    def derivacao_texto(self) -> str:
        if not self.passos:
            return ""
        partes = [_corpo_str(self.passos[0].forma_antes)]
        for p in self.passos:
            partes.append(_corpo_str(p.forma_depois))
        return " ⇒ ".join(partes)


# ---------------------------------------------------------------------------
# Gramática
# ---------------------------------------------------------------------------
@dataclass
class Gramatica:
    variaveis: set[str]
    terminais: set[str]
    producoes: dict[str, list[Corpo]]
    inicial: str
    descricao: str = ""

    # ------------------------------------------------------------------ I/O
    @staticmethod
    def de_dict(dados: dict) -> "Gramatica":
        prods: dict[str, list[Corpo]] = {}
        for A, corpos in dados["producoes"].items():
            if isinstance(corpos, str):
                corpos = corpos.split("|")
            for c in corpos:
                corpo = tuple(c) if isinstance(c, list) else _parse_corpo(c)
                prods.setdefault(A, [])
                if corpo not in prods[A]:
                    prods[A].append(corpo)
        g = Gramatica(
            variaveis=set(dados.get("variaveis") or prods.keys()),
            terminais=set(dados["terminais"]),
            producoes=prods,
            inicial=dados.get("simbolo_inicial") or dados.get("inicial"),
            descricao=dados.get("descricao", ""),
        )
        erros = g.validar()
        if erros:
            raise ValueError("Gramática inválida:\n  - " + "\n  - ".join(erros))
        return g

    @staticmethod
    def carregar_json(caminho: str | Path) -> "Gramatica":
        with open(caminho, encoding="utf-8") as f:
            return Gramatica.de_dict(json.load(f))

    @staticmethod
    def de_texto(texto: str, descricao: str = "") -> "Gramatica":
        """
        Lê produções no formato   S -> aSb | λ   (uma variável por linha).
        A variável da primeira linha é o símbolo inicial. Todo símbolo que
        aparece do lado esquerdo é variável; os demais são terminais.
        """
        prods: dict[str, list[Corpo]] = {}
        ordem: list[str] = []
        for linha in texto.strip().splitlines():
            if not linha.strip():
                continue
            seta = "->" if "->" in linha else "→"
            if seta not in linha:
                raise ValueError(f"Linha sem '->': {linha}")
            A, direita = linha.split(seta, 1)
            A = A.strip()
            ordem.append(A)
            for c in direita.split("|"):
                prods.setdefault(A, []).append(_parse_corpo(c))
        variaveis = set(prods)
        terminais = {s for corpos in prods.values() for c in corpos for s in c} - variaveis
        g = Gramatica(variaveis, terminais, prods, ordem[0], descricao)
        erros = g.validar()
        if erros:
            raise ValueError("Gramática inválida:\n  - " + "\n  - ".join(erros))
        return g

    def validar(self) -> list[str]:
        erros = []
        if self.inicial not in self.variaveis:
            erros.append(f"símbolo inicial '{self.inicial}' não está em V")
        if self.variaveis & self.terminais:
            erros.append(f"V e Σ não são disjuntos: {self.variaveis & self.terminais}")
        for t in self.terminais:
            if len(t) != 1:
                erros.append(f"terminal '{t}' deve ter 1 caractere")
        for A, corpos in self.producoes.items():
            if A not in self.variaveis:
                erros.append(f"lado esquerdo '{A}' não é variável (GLC exige A ∈ V)")
            for c in corpos:
                for s in c:
                    if s not in self.variaveis and s not in self.terminais:
                        erros.append(f"símbolo '{s}' em {A} -> {_corpo_str(c)} não está em V ∪ Σ")
        return erros

    # -------------------------------------------------------- propriedades
    def anulaveis(self) -> set[str]:
        """Variáveis A tais que A ⇒* λ (ponto fixo)."""
        anul: set[str] = set()
        mudou = True
        while mudou:
            mudou = False
            for A, corpos in self.producoes.items():
                if A not in anul and any(all(s in anul for s in c) for c in corpos):
                    anul.add(A)
                    mudou = True
        return anul

    def tamanho_minimo(self) -> dict[str, float]:
        """
        min[A] = tamanho da menor cadeia de terminais derivável de A
        (∞ se A não gera cadeia alguma). Usado para PODAR a busca.
        """
        minimo = {A: INF for A in self.variaveis}
        mudou = True
        while mudou:
            mudou = False
            for A, corpos in self.producoes.items():
                for c in corpos:
                    custo = sum(minimo.get(s, INF) if s in self.variaveis else 1 for s in c)
                    if custo < minimo[A]:
                        minimo[A] = custo
                        mudou = True
        return minimo

    # ----------------------------------------------------------------- FNC
    def _novo_nome(self, base: str, usados: set[str]) -> str:
        if base not in usados:
            return base
        i = 1
        while f"{base}{i}" in usados:
            i += 1
        return f"{base}{i}"

    def para_fnc(self) -> "Gramatica":
        """
        Converte para a Forma Normal de Chomsky: toda produção é
            A -> BC    ou    A -> a    (e, opcionalmente, S0 -> λ).
        Passos (Sipser, teorema 2.9):
          1. START: novo símbolo inicial S0 -> S
          2. DEL  : remove produções-λ
          3. UNIT : remove produções unitárias A -> B
          4. Remove símbolos inúteis
          5. TERM : terminais em corpos longos viram variáveis X_a -> a
          6. BIN  : quebra corpos com 3+ símbolos em cadeias de pares
        """
        usados = set(self.variaveis) | set(self.terminais)
        prods = {A: [tuple(c) for c in cs] for A, cs in self.producoes.items()}

        # 1. START
        S0 = self._novo_nome(self.inicial + "0", usados)
        usados.add(S0)
        prods[S0] = [(self.inicial,)]

        # 2. DEL
        anul = Gramatica(set(prods), self.terminais, prods, S0).anulaveis()
        novas: dict[str, set[Corpo]] = {}
        for A, corpos in prods.items():
            for c in corpos:
                posicoes = [i for i, s in enumerate(c) if s in anul]
                # todas as combinações de remover / manter cada anulável
                for mascara in range(1 << len(posicoes)):
                    remover = {posicoes[k] for k in range(len(posicoes)) if mascara >> k & 1}
                    novo = tuple(s for i, s in enumerate(c) if i not in remover)
                    if novo or A == S0:
                        novas.setdefault(A, set()).add(novo)
        prods = {A: sorted(cs) for A, cs in novas.items()}

        # 3. UNIT  (fecho unitário: B ∈ unit(A) se A ⇒* B só com regras unitárias)
        variaveis = set(prods)
        resultado: dict[str, set[Corpo]] = {}
        for A in variaveis:
            fecho, pilha = {A}, [A]
            while pilha:
                X = pilha.pop()
                for c in prods.get(X, []):
                    if len(c) == 1 and c[0] in variaveis and c[0] not in fecho:
                        fecho.add(c[0])
                        pilha.append(c[0])
            for B in fecho:
                for c in prods.get(B, []):
                    if not (len(c) == 1 and c[0] in variaveis):
                        resultado.setdefault(A, set()).add(c)
        prods = {A: sorted(cs) for A, cs in resultado.items()}

        # 4. Inúteis: geradores e alcançáveis
        geradores: set[str] = set()
        mudou = True
        while mudou:
            mudou = False
            for A, cs in prods.items():
                if A not in geradores and any(all(s in self.terminais or s in geradores for s in c) for c in cs):
                    geradores.add(A)
                    mudou = True
        prods = {A: [c for c in cs if all(s in self.terminais or s in geradores for s in c)]
                 for A, cs in prods.items() if A in geradores}
        alcancaveis, pilha = {S0}, [S0]
        while pilha:
            X = pilha.pop()
            for c in prods.get(X, []):
                for s in c:
                    if s in prods and s not in alcancaveis:
                        alcancaveis.add(s)
                        pilha.append(s)
        prods = {A: cs for A, cs in prods.items() if A in alcancaveis}
        if S0 not in prods:
            prods[S0] = []           # linguagem vazia

        # 5. TERM
        var_terminal: dict[str, str] = {}
        def var_de(a: str) -> str:
            if a not in var_terminal:
                nome = self._novo_nome(f"X_{a}", usados)
                usados.add(nome)
                var_terminal[a] = nome
            return var_terminal[a]

        prods2: dict[str, list[Corpo]] = {}
        for A, cs in prods.items():
            for c in cs:
                if len(c) >= 2:
                    c = tuple(var_de(s) if s in self.terminais else s for s in c)
                prods2.setdefault(A, []).append(c)
        for a, T in var_terminal.items():
            prods2[T] = [(a,)]

        # 6. BIN
        final: dict[str, list[Corpo]] = {}
        contador: dict[str, int] = {}
        for A, cs in prods2.items():
            for c in cs:
                atual = A
                while len(c) > 2:
                    contador[A] = contador.get(A, 0) + 1
                    novo = self._novo_nome(f"{A}_{contador[A]}", usados)
                    usados.add(novo)
                    final.setdefault(atual, []).append((c[0], novo))
                    atual, c = novo, c[1:]
                final.setdefault(atual, []).append(c)
        for A in final:
            final[A] = list(dict.fromkeys(final[A]))

        return Gramatica(set(final), set(self.terminais), final, S0,
                         f"FNC de: {self.descricao}")

    def esta_na_fnc(self) -> bool:
        for A, cs in self.producoes.items():
            for c in cs:
                ok = ((len(c) == 2 and all(s in self.variaveis for s in c))
                      or (len(c) == 1 and c[0] in self.terminais)
                      or (len(c) == 0 and A == self.inicial))
                if not ok:
                    return False
        return True

    # ----------------------------------------------------------------- CYK
    def cyk(self, w: str, fnc: "Gramatica | None" = None) -> tuple[bool, int]:
        """
        Algoritmo CYK (programação dinâmica) sobre a gramática em FNC.
        tabela[i][l] = variáveis que geram w[i : i+l].   Θ(n³ · |R|).
        Retorna (aceita, número de operações elementares).
        """
        g = fnc or self.para_fnc()
        n = len(w)
        if n == 0:
            return (() in g.producoes.get(g.inicial, [])), 1

        unitarias = [(A, c[0]) for A, cs in g.producoes.items() for c in cs if len(c) == 1]
        binarias = [(A, c[0], c[1]) for A, cs in g.producoes.items() for c in cs if len(c) == 2]
        ops = 0
        tabela = [[set() for _ in range(n + 1)] for _ in range(n)]
        for i, a in enumerate(w):
            for A, t in unitarias:
                ops += 1
                if t == a:
                    tabela[i][1].add(A)
        for l in range(2, n + 1):              # tamanho do trecho
            for i in range(0, n - l + 1):      # início do trecho
                for k in range(1, l):          # ponto de divisão
                    esq, dir_ = tabela[i][k], tabela[i + k][l - k]
                    for A, B, C in binarias:
                        ops += 1
                        if B in esq and C in dir_:
                            tabela[i][l].add(A)
        return g.inicial in tabela[0][n], ops

    # ----------------------------------------------- derivação + árvore
    def derivar(self, w: str, limite_formas: int = 200_000) -> ResultadoGLC:
        for i, c in enumerate(w):
            if c not in self.terminais:
                return ResultadoGLC(False, w, [], None,
                                    f"símbolo '{c}' (posição {i}) não é terminal da gramática")

        aceita, ops_cyk = self.cyk(w)
        if not aceita:
            return ResultadoGLC(False, w, [], None,
                                "CYK: a cadeia NÃO é gerada pela gramática (não existe S ⇒* w)",
                                0, ops_cyk)

        passos, exploradas = self._bfs_mais_a_esquerda(w, limite_formas)
        if passos is None:
            return ResultadoGLC(True, w, [], None,
                                "CYK aceitou, mas o limite de busca da derivação foi atingido",
                                exploradas, ops_cyk)
        arvore = self._construir_arvore(passos)
        return ResultadoGLC(True, w, passos, arvore,
                            f"derivação mais à esquerda encontrada em {len(passos)} passo(s)",
                            exploradas, ops_cyk)

    def _bfs_mais_a_esquerda(self, w: str, limite: int):
        """
        BFS sobre formas sentenciais, sempre expandindo a variável MAIS À
        ESQUERDA. Podas (todas seguras, isto é, nunca descartam uma forma que
        poderia derivar w):
          (a) o prefixo de terminais antes da 1ª variável deve ser prefixo de w;
          (b) o sufixo de terminais após a última variável deve ser sufixo de w;
          (c) Σ tamanho_mínimo(símbolos) ≤ |w|.
        """
        n = len(w)
        minimo = self.tamanho_minimo()
        inicio: Corpo = (self.inicial,)
        pai: dict[Corpo, tuple[Corpo, int, Corpo] | None] = {inicio: None}
        fila = deque([inicio])
        exploradas = 0

        while fila:
            forma = fila.popleft()
            exploradas += 1
            if exploradas > limite:
                return None, exploradas
            pos = next((i for i, s in enumerate(forma) if s in self.variaveis), None)
            if pos is None:
                if "".join(forma) == w:
                    return self._reconstruir(pai, forma), exploradas
                continue
            A = forma[pos]
            for corpo in self.producoes.get(A, []):
                nova = forma[:pos] + corpo + forma[pos + 1:]
                if nova in pai or not self._viavel(nova, w, n, minimo):
                    continue
                pai[nova] = (forma, pos, corpo)
                fila.append(nova)
        return None, exploradas

    def _viavel(self, forma: Corpo, w: str, n: int, minimo: dict[str, float]) -> bool:
        if sum(minimo.get(s, INF) if s in self.variaveis else 1 for s in forma) > n:
            return False
        i = 0
        while i < len(forma) and forma[i] not in self.variaveis:
            i += 1
        prefixo = "".join(forma[:i])
        if not w.startswith(prefixo):
            return False
        if i == len(forma):
            return prefixo == w
        j = len(forma)
        while forma[j - 1] not in self.variaveis:
            j -= 1
        sufixo = "".join(forma[j:])
        return w.endswith(sufixo) and len(prefixo) + len(sufixo) <= n

    @staticmethod
    def _reconstruir(pai, final: Corpo) -> list[PassoDerivacao]:
        passos = []
        forma = final
        while pai[forma] is not None:
            anterior, pos, corpo = pai[forma]
            passos.append(PassoDerivacao(anterior, pos, anterior[pos], corpo, forma))
            forma = anterior
        return list(reversed(passos))

    def _construir_arvore(self, passos: list[PassoDerivacao]) -> No:
        """Repete os passos: cada um expande a folha-variável mais à esquerda."""
        raiz = No(self.inicial)
        folhas = [raiz]                         # folhas na ordem da forma sentencial
        for p in passos:
            no = folhas[p.posicao]
            no.filhos = [No(s) for s in p.corpo] if p.corpo else [No(LAMBDA)]
            novas = [f for f in no.filhos if f.simbolo != LAMBDA]
            folhas = folhas[:p.posicao] + novas + folhas[p.posicao + 1:]
        return raiz

    # ------------------------------------------------------------ exibição
    def __str__(self) -> str:
        linhas = [f"GLC: {self.descricao}" if self.descricao else "GLC",
                  f"V = {{{', '.join(sorted(self.variaveis))}}}",
                  f"Σ = {{{', '.join(sorted(self.terminais))}}}",
                  f"S = {self.inicial}",
                  "R:"]
        ordem = [self.inicial] + sorted(A for A in self.producoes if A != self.inicial)
        for A in ordem:
            if A in self.producoes:
                linhas.append(f"  {A} -> " + " | ".join(_corpo_str(c) for c in self.producoes[A]))
        return "\n".join(linhas)


def descrever_passo(p: PassoDerivacao) -> str:
    return (f"{_corpo_str(p.forma_antes):<20} ⇒ {_corpo_str(p.forma_depois):<20} "
            f"[aplicando {p.variavel} -> {_corpo_str(p.corpo)}]")
