"""
MÓDULO 6 - COMPLEXIDADE COMPUTACIONAL
=====================================

Notação assintótica (Cormen; Toscani & Veloso):

* O(g)  - limite SUPERIOR:  f(n) ≤ c·g(n) para n ≥ n0
* Ω(g)  - limite INFERIOR:  f(n) ≥ c·g(n) para n ≥ n0
* Θ(g)  - limite JUSTO:     f ∈ O(g) e f ∈ Ω(g)

Este módulo tem duas partes:
  1. TABELA TEÓRICA com melhor, médio e pior caso de cada algoritmo usado.
  2. MEDIÇÃO EMPÍRICA: cada simulador conta suas operações elementares
     (passos da MT, configurações do AP, células do CYK...). Rodamos com
     entradas de tamanho crescente e calculamos  operações / f(n).
     Se a razão se estabiliza numa constante c, isso é evidência
     experimental de que o custo é Θ(f(n)).

Em todas as linhas, n = |w| (tamanho da cadeia de entrada).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .automato_finito import AutomatoFinito
from .automato_pilha import AutomatoPilha
from .glc import Gramatica
from .maquina_turing import MaquinaTuring

EXEMPLOS = Path(__file__).resolve().parent.parent / "exemplos"


@dataclass(frozen=True)
class AnaliseAlgoritmo:
    modulo: str
    algoritmo: str
    melhor: str
    medio: str
    pior: str
    justificativa: str


TABELA: list[AnaliseAlgoritmo] = [
    AnaliseAlgoritmo(
        "1 - Linguagens", "Validar w ∈ Σ* (busca em conjunto hash)",
        "Θ(1)", "Θ(n)", "Θ(n)",
        "Para no 1º símbolo inválido (melhor caso). Cadeia válida exige ler os n símbolos; "
        "cada consulta ao conjunto Σ custa O(1) amortizado."),
    AnaliseAlgoritmo(
        "1 - Linguagens", "Tamanho |w| e concatenação u·v",
        "Θ(n)", "Θ(n)", "Θ(n)",
        "Contar/copiar símbolos é linear (|uv| = |u|+|v|). Em Python, len() é O(1) porque o "
        "tamanho fica armazenado, mas o custo teórico de contar é Θ(n)."),
    AnaliseAlgoritmo(
        "1 - Linguagens", "Enumerar Σ* / Σ+ até tamanho k",
        "Θ(k·|Σ|ᵏ)", "Θ(k·|Σ|ᵏ)", "Θ(k·|Σ|ᵏ)",
        "Gera Σ_{i≤k} |Σ|ⁱ cadeias de até k símbolos: custo exponencial em k, "
        "proporcional ao tamanho da saída (não há como ser melhor)."),
    AnaliseAlgoritmo(
        "1 - Linguagens", "Pertinência em L* (programação dinâmica)",
        "Θ(n²)", "Θ(n²)", "O(n²·T(n))",
        "Tabela alcancavel[0..n]; para cada j testa todos os cortes i<j. T(n) = custo de testar "
        "w[i:j] ∈ L (O(n) para L finita com hash)."),
    AnaliseAlgoritmo(
        "2 - Autômatos", "Simulação de AFD",
        "Θ(1)", "Θ(n)", "Θ(n)",
        "Uma transição por símbolo, cada uma O(1) (dicionário). Melhor caso: AFD parcial "
        "trava no 1º símbolo. AFD completo é sempre Θ(n)."),
    AnaliseAlgoritmo(
        "2 - Autômatos", "Simulação de AFN-ε (conjunto de estados ativos)",
        "Θ(1)", "Θ(n·k)", "O(n·|Q|²)",
        "Por símbolo, cada um dos até |Q| estados ativos gera até |Q| destinos, e o fecho-ε "
        "visita O(|Q|²) arestas. k = média de estados ativos. Melhor caso: todos os ramos morrem cedo."),
    AnaliseAlgoritmo(
        "2 - Autômatos", "Construção de subconjuntos (AFN -> AFD)",
        "Θ(|Σ|·|Q|)", "-", "O(2^|Q|·|Σ|·|Q|²)",
        "Cada estado do AFD é um subconjunto de Q: até 2^|Q| estados (explosão exponencial, "
        "ex.: 'n-ésimo símbolo a partir do fim é a'). Só os alcançáveis são gerados."),
    AnaliseAlgoritmo(
        "3 - GLC", "Conversão para FNC",
        "Θ(|G|)", "O(|G|²)", "O(2^m·|G|²)",
        "UNIT pode gerar O(|V|²) regras; DEL gera até 2^m variantes de um corpo com m "
        "anuláveis (m = maior corpo). BIN/TERM são lineares."),
    AnaliseAlgoritmo(
        "3 - GLC", "CYK (decisão de pertinência)",
        "Θ(n³·|R|)", "Θ(n³·|R|)", "Θ(n³·|R|)",
        "Três laços aninhados (tamanho, início, corte) sempre completos × regras binárias |R|. "
        "Mesmo custo em qualquer caso: Θ."),
    AnaliseAlgoritmo(
        "3 - GLC", "Derivação mais à esquerda (BFS com podas)",
        "Θ(n²)", "exponencial", "O(bᵈ·n)",
        "b = nº máx. de produções por variável, d = nº de passos da derivação. Em gramáticas "
        "como S->aSb|λ a poda deixa 1 forma viável por nível: Θ(n) formas × O(n) cada = Θ(n²). "
        "Em gramáticas ambíguas a árvore de busca cresce exponencialmente."),
    AnaliseAlgoritmo(
        "4 - AP", "Simulação de AP determinístico (aⁿbⁿ)",
        "Θ(1)", "Θ(n)", "Θ(n)",
        "Cada símbolo dispara exatamente 1 transição com push/pop O(1). Melhor caso: começa com 'b' "
        "e trava imediatamente."),
    AnaliseAlgoritmo(
        "4 - AP", "Simulação de AP não determinístico (BFS de configurações)",
        "Θ(n)", "-", "O(|Q|·n·|Γ|^h)",
        "Número de configurações (estado, posição, pilha) com pilha de altura ≤ h. Para wwᴿ "
        "há n+1 'chutes' do meio, cada um com até n passos: Θ(n²). O limite h evita laços ε infinitos."),
    AnaliseAlgoritmo(
        "5 - MT", "MT para w#w (zigue-zague)",
        "Θ(n)", "Θ(n²)", "Θ(n²)",
        "Para cada um dos |w| ≈ n/2 símbolos a cabeça vai e volta atravessando ~n células: Θ(n²). "
        "Melhor caso: divergência no 1º par, só uma travessia Θ(n). (Média sobre cadeias de L: Θ(n²).)"),
    AnaliseAlgoritmo(
        "5 - MT", "MT de soma unária (0ᵃ10ᵇ -> 0ᵃ⁺ᵇ)",
        "Θ(n)", "Θ(n)", "Θ(n)",
        "Uma passada para a direita (n+1 passos) e 2 passos para apagar o último 0: exatamente "
        "n+2 passos em qualquer caso."),
]


# ---------------------------------------------------------------------------
# Medição empírica
# ---------------------------------------------------------------------------
@dataclass
class Medicao:
    n: int
    operacoes: int
    razao: float
    tempo_ms: float


@dataclass
class Experimento:
    nome: str
    funcao_ref: str                         # texto: "n", "n²", "n³"
    f: Callable[[int], float]               # f(n) para normalizar
    gerar_e_medir: Callable[[int], tuple[int, int]]   # tamanho -> (n real, operações)
    tamanhos: list[int]


def _experimentos() -> list[Experimento]:
    afd = AutomatoFinito.carregar_json(EXEMPLOS / "afd_numero_par_de_a.json")
    afn = AutomatoFinito.carregar_json(EXEMPLOS / "afn_termina_em_ab.json")
    glc = Gramatica.carregar_json(EXEMPLOS / "glc_anbn.json")
    fnc = glc.para_fnc()
    ap = AutomatoPilha.carregar_json(EXEMPLOS / "ap_anbn.json")
    apn = AutomatoPilha.carregar_json(EXEMPLOS / "ap_wwr.json")
    mt_a = MaquinaTuring.carregar_json(EXEMPLOS / "mt_w_sharp_w.json")
    mt_b = MaquinaTuring.carregar_json(EXEMPLOS / "mt_soma_unaria.json")
    rnd = random.Random(42)

    def aleatoria(k, sigma="ab"):
        return "".join(rnd.choice(sigma) for _ in range(k))

    def m_afd(k):
        w = aleatoria(k)
        return len(w), afd.executar(w, registrar=False).contador_operacoes

    def m_afn(k):
        w = aleatoria(k)
        return len(w), afn.executar(w, registrar=False).contador_operacoes

    def m_cyk(k):
        w = "a" * (k // 2) + "b" * (k // 2)
        return len(w), glc.cyk(w, fnc)[1]

    def m_ap(k):
        w = "a" * (k // 2) + "b" * (k // 2)
        return len(w), ap.executar(w).configuracoes_exploradas

    def m_apn(k):
        # PIOR caso: w = aⁿ. Todo "chute" do meio sobrevive por min(i, n-i)
        # passos, gerando ~n²/4 configurações. (Com cadeias aleatórias os
        # ramos errados morrem cedo e o custo observado fica perto de linear.)
        w = "a" * k
        return len(w), apn.executar(w, max_configuracoes=10**7).configuracoes_exploradas

    def m_mt_a(k):
        u = aleatoria(k // 2, "01")
        w = u + "#" + u
        return len(w), mt_a.executar(w, max_passos=10**7, registrar=False).numero_passos

    def m_mt_b(k):
        w = "0" * (k // 2) + "1" + "0" * (k - k // 2)
        return len(w), mt_b.executar(w, max_passos=10**7, registrar=False).numero_passos

    return [
        Experimento("AFD (nº par de a's)", "n", lambda n: n, m_afd, [100, 1000, 10000, 100000]),
        Experimento("AFN (termina em ab)", "n", lambda n: n, m_afn, [100, 1000, 10000, 100000]),
        Experimento("CYK (aⁿbⁿ)", "n³", lambda n: n ** 3, m_cyk, [8, 16, 32, 64]),
        Experimento("AP determinístico (aⁿbⁿ)", "n", lambda n: n, m_ap, [10, 100, 1000, 5000]),
        Experimento("AP não determ. (wwᴿ, pior caso aⁿ)", "n²", lambda n: n ** 2, m_apn, [10, 20, 40, 80, 160]),
        Experimento("MT w#w", "n²", lambda n: n ** 2, m_mt_a, [10, 50, 100, 200, 400]),
        Experimento("MT soma unária", "n", lambda n: n, m_mt_b, [10, 100, 1000, 10000]),
    ]


def medir(exp: Experimento) -> list[Medicao]:
    resultado = []
    for k in exp.tamanhos:
        t0 = time.perf_counter()
        n, ops = exp.gerar_e_medir(k)
        dt = (time.perf_counter() - t0) * 1000
        resultado.append(Medicao(n, ops, ops / exp.f(n), dt))
    return resultado


def relatorio_teorico() -> str:
    linhas = []
    modulo_atual = None
    for a in TABELA:
        if a.modulo != modulo_atual:
            modulo_atual = a.modulo
            linhas.append(f"\n=== Módulo {a.modulo} ===")
        linhas.append(f"• {a.algoritmo}")
        linhas.append(f"    melhor: {a.melhor:<14} médio: {a.medio:<14} pior: {a.pior}")
        linhas.append(f"    {a.justificativa}")
    return "\n".join(linhas)


def relatorio_empirico() -> str:
    linhas = ["Razão = operações / f(n). Se a razão tende a uma constante, o custo é Θ(f(n)).\n"]
    for exp in _experimentos():
        linhas.append(f"--- {exp.nome}   [esperado Θ({exp.funcao_ref})]")
        linhas.append(f"{'n':>8} | {'operações':>12} | {'razão':>10} | {'tempo (ms)':>10}")
        for m in medir(exp):
            linhas.append(f"{m.n:>8} | {m.operacoes:>12} | {m.razao:>10.4f} | {m.tempo_ms:>10.2f}")
        linhas.append("")
    return "\n".join(linhas)
