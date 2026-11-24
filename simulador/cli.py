"""
Interface de linha de comando (console).

Dois modos de uso:
  * MENU INTERATIVO:      python main.py
  * COMANDOS DIRETOS:     python main.py af exemplos/afd_enunciado.json ab
                          (úteis para scripts, testes e para a apresentação)

Execute  python main.py --help  para ver todos os comandos.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import linguagens as lf
from .automato_finito import AutomatoFinito
from .automato_pilha import AutomatoPilha
from .complexidade import relatorio_empirico, relatorio_teorico
from .glc import Gramatica, descrever_passo
from .maquina_turing import MaquinaTuring, codificar_soma_unaria, decodificar_unario

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = RAIZ / "exemplos"
LIMITE_PASSOS_EXIBIDOS = 200


# ---------------------------------------------------------------------------
# Utilidades de exibição
# ---------------------------------------------------------------------------
def titulo(texto: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {texto}")
    print("=" * 72)


def veredito(aceita: bool) -> str:
    return "ACEITA ✔" if aceita else "REJEITA ✘"


def ler_cadeia(texto: str) -> str:
    """Permite digitar ε, λ ou 'vazia' para a cadeia vazia."""
    t = texto.strip()
    return "" if t.lower() in {"ε", "λ", "eps", "vazia", "''", '""'} else t


# ---------------------------------------------------------------------------
# Módulo 1 - Linguagens formais
# ---------------------------------------------------------------------------
def mostrar_linguagem(alfabeto: lf.Alfabeto, w: str, concatenar_com: str | None = None,
                      k_estrela: int | None = None) -> None:
    titulo("MÓDULO 1 - LINGUAGENS FORMAIS")
    print(f"Σ = {alfabeto}")
    print(f"Entrada: {lf.formatar_cadeia(w)}\n")
    ok, invalidos = alfabeto.validar_cadeia(w)
    if ok:
        print("Cadeia válida para Σ  (w ∈ Σ*)")
    else:
        desc = ", ".join(f"'{s}' na posição {i}" for i, s in invalidos)
        print(f"Cadeia INVÁLIDA para Σ  (w ∉ Σ*): símbolo(s) {desc}")
    print(f"Tamanho = {lf.tamanho(w)}")
    print(f"Reverso wᴿ = {lf.formatar_cadeia(lf.reverso(w))}")
    print(f"w ∈ Σ+ ? {'sim' if ok and w else 'não'}  (Σ+ = Σ* - {{ε}})")
    if concatenar_com is not None:
        r = lf.concatenar(w, concatenar_com)
        print(f"Concatenação: {lf.formatar_cadeia(w)} · {lf.formatar_cadeia(concatenar_com)} = "
              f"{lf.formatar_cadeia(r)}   (|uv| = {len(w)} + {len(concatenar_com)} = {len(r)})")
    if k_estrela is not None:
        mostrar_sigma(alfabeto, k_estrela)


def mostrar_sigma(alfabeto: lf.Alfabeto, k: int, limite: int = 60) -> None:
    def amostra(gerador):
        itens = []
        for i, w in enumerate(gerador):
            if i >= limite:
                itens.append("...")
                break
            itens.append(lf.formatar_cadeia(w))
        return "{" + ", ".join(itens) + "}"

    print(f"\nΣ* (até tamanho {k}) = {amostra(alfabeto.sigma_estrela(k))}")
    print(f"   |Σ⁰ ∪ ... ∪ Σ^{k}| = {alfabeto.quantidade_sigma_estrela(k)} cadeias "
          f"(Σ* completo é INFINITO, mas enumerável)")
    print(f"Σ+ (até tamanho {k}) = {amostra(alfabeto.sigma_mais(k))}")
    print(f"   |Σ¹ ∪ ... ∪ Σ^{k}| = {alfabeto.quantidade_sigma_estrela(k) - 1} cadeias")


def mostrar_pertinencia_linguagem(L: lf.Linguagem, cadeias: list[str], k: int = 4) -> None:
    print(f"\n{L}")
    print(f"Palavras de {L.nome} com tamanho ≤ {k}: "
          f"{{{', '.join(lf.formatar_cadeia(p) for p in L.enumerar(k))}}}")
    for w in cadeias:
        print(f"  '{lf.formatar_cadeia(w)}' ∈ {L.nome}? {'SIM' if L.pertence(w) else 'NÃO'}")


# ---------------------------------------------------------------------------
# Módulo 2 - Autômato finito
# ---------------------------------------------------------------------------
def mostrar_af(af: AutomatoFinito, cadeias: list[str], converter: bool = False) -> None:
    titulo(f"MÓDULO 2 - AUTÔMATO FINITO ({af.tipo})")
    print(af)
    if converter and af.tipo == "AFN":
        print("\n>> Construção de subconjuntos (AFN -> AFD):")
        print(af.para_afd())
    for w in cadeias:
        r = af.executar(w)
        print(f"\nEntrada: {lf.formatar_cadeia(w)}")
        for p in r.passos[:LIMITE_PASSOS_EXIBIDOS]:
            print("  " + p)
        print("Saída:")
        print("  " + " -> ".join(r.caminho))
        print(f"  {'ACEITA' if r.aceita else 'REJEITA'}   ({r.motivo})")


# ---------------------------------------------------------------------------
# Módulo 3 - GLC
# ---------------------------------------------------------------------------
def mostrar_glc(g: Gramatica, cadeias: list[str], fnc: bool = False) -> None:
    titulo("MÓDULO 3 - GRAMÁTICA LIVRE DE CONTEXTO")
    print(g)
    if fnc:
        print("\n>> Forma Normal de Chomsky:")
        print(g.para_fnc())
    for w in cadeias:
        print(f"\nEntrada: {lf.formatar_cadeia(w)}")
        r = g.derivar(w)
        if r.passos:
            print("Derivação mais à esquerda passo a passo:")
            for i, p in enumerate(r.passos, 1):
                print(f"  {i:>2}. {descrever_passo(p)}")
            print(f"\n  {r.derivacao_texto()}")
            print("\nÁrvore de derivação (simplificada):")
            for linha in r.arvore.desenhar():
                print("  " + linha)
            print(f"  fronteira (folhas) = {lf.formatar_cadeia(r.arvore.fronteira())}")
        print(f"Saída: {'Aceita' if r.aceita else 'Rejeita'}   ({r.motivo})")
        print(f"  [CYK: {r.operacoes_cyk} operações | BFS: {r.formas_exploradas} formas sentenciais exploradas]")


# ---------------------------------------------------------------------------
# Módulo 4 - AP
# ---------------------------------------------------------------------------
def mostrar_ap(ap: AutomatoPilha, cadeias: list[str]) -> None:
    titulo("MÓDULO 4 - AUTÔMATO COM PILHA")
    print(ap)
    print(f"Determinístico? {'sim' if ap.eh_deterministico() else 'não'}")
    for w in cadeias:
        r = ap.executar(w)
        print(f"\nEntrada: {lf.formatar_cadeia(w)}")
        if r.passos:
            if not r.aceita:
                print("(computação que mais avançou antes de travar)")
            print(r.tabela())
        print(f"Saída: {veredito(r.aceita)}   ({r.motivo})")
        print(f"  [{r.configuracoes_exploradas} configuração(ões) exploradas]")


# ---------------------------------------------------------------------------
# Módulo 5 - MT
# ---------------------------------------------------------------------------
def mostrar_mt(mt: MaquinaTuring, cadeias: list[str], max_passos: int = 10_000,
               mostrar_passos: bool = True) -> None:
    titulo("MÓDULO 5 - MÁQUINA DE TURING")
    print(mt)
    for w in cadeias:
        r = mt.executar(w, max_passos=max_passos, registrar=mostrar_passos)
        print(f"\nEntrada: {lf.formatar_cadeia(w)}")
        if mostrar_passos:
            print(f"{'Passo':>5} | {'Estado':<9} | Fita ([x] = cabeçote)        | Transição aplicada")
            for p in r.passos[:LIMITE_PASSOS_EXIBIDOS]:
                print(f"{p.numero:>5} | {p.estado:<9} | {p.fita:<28} | {p.transicao}")
            if len(r.passos) > LIMITE_PASSOS_EXIBIDOS:
                print(f"  ... ({len(r.passos) - LIMITE_PASSOS_EXIBIDOS} passos omitidos)")
        print(f"Total de passos: {r.numero_passos}   células visitadas: {r.celulas_usadas}")
        if mt.modo == "transdutor":
            if r.aceita:
                saida = r.saida(mt.branco)
                print(f"Resultado: {lf.formatar_cadeia(saida)}   (= {decodificar_unario(saida)} em unário)")
            else:
                print(f"Entrada mal formada: {r.motivo}")
        else:
            print(f"Saída: {veredito(r.aceita)}   ({r.motivo})")


# ---------------------------------------------------------------------------
# Demonstração com os exemplos do enunciado
# ---------------------------------------------------------------------------
def demonstracao() -> None:
    mostrar_linguagem(lf.Alfabeto.de_texto("a,b"), "abba", concatenar_com="ba", k_estrela=2)
    sigma = lf.Alfabeto.de_texto("a,b")
    mostrar_pertinencia_linguagem(lf.Linguagem.finita(sigma, ["ab", "ba", "aabb"], "L1"),
                                  ["ab", "abba"])
    mostrar_pertinencia_linguagem(lf.Linguagem.por_regex(sigma, "a*b*", "L2"), ["aabbb", "aba"])

    mostrar_af(AutomatoFinito.carregar_json(EXEMPLOS / "afd_enunciado.json"), ["ab", "aba"])
    mostrar_af(AutomatoFinito.carregar_json(EXEMPLOS / "afn_termina_em_ab.json"), ["abab"],
               converter=True)
    mostrar_glc(Gramatica.carregar_json(EXEMPLOS / "glc_anbn.json"), ["aaabbb", "aab"])
    mostrar_ap(AutomatoPilha.carregar_json(EXEMPLOS / "ap_anbn.json"), ["aaabbb", "aabbb"])
    mostrar_mt(MaquinaTuring.carregar_json(EXEMPLOS / "mt_w_sharp_w.json"), ["01#01", "01#10"])
    mostrar_mt(MaquinaTuring.carregar_json(EXEMPLOS / "mt_soma_unaria.json"), ["000100"])
    titulo("MÓDULO 6 - COMPLEXIDADE (resumo teórico)")
    print(relatorio_teorico())


# ---------------------------------------------------------------------------
# Menu interativo
# ---------------------------------------------------------------------------
def _perguntar(msg: str) -> str:
    try:
        return input(msg)
    except EOFError:
        print()
        raise SystemExit(0)


def _escolher_arquivo(prefixos: tuple[str, ...]) -> Path | None:
    arquivos = sorted(p for p in EXEMPLOS.glob("*.json") if p.name.startswith(prefixos))
    print("\nExemplos disponíveis:")
    for i, p in enumerate(arquivos, 1):
        print(f"  {i}. {p.name}")
    print("  (ou digite o caminho de um arquivo JSON seu)")
    resp = _perguntar("Escolha: ").strip()
    if not resp:
        return None
    if resp.isdigit() and 1 <= int(resp) <= len(arquivos):
        return arquivos[int(resp) - 1]
    caminho = Path(resp)
    if not caminho.exists():
        print(f"Arquivo '{resp}' não encontrado.")
        return None
    return caminho


def _loop_cadeias(executar) -> None:
    print("Digite cadeias para testar (ε para cadeia vazia, ENTER em branco para voltar).")
    while True:
        bruto = _perguntar("\ncadeia> ")
        if bruto.strip() == "":
            return
        executar(ler_cadeia(bruto))


def _menu_linguagens() -> None:
    try:
        sigma = lf.Alfabeto.de_texto(_perguntar("Defina o alfabeto Σ (ex.: a,b): "))
    except ValueError as e:
        print(f"Erro: {e}")
        return
    L: lf.Linguagem | None = None
    while True:
        print(f"\nΣ = {sigma}" + (f"    {L}" if L else ""))
        print("  1. Validar cadeia / tamanho / reverso")
        print("  2. Concatenação de duas cadeias")
        print("  3. Enumerar Σ* e Σ+ até um tamanho k")
        print("  4. Definir linguagem L (finita ou por expressão regular)")
        print("  5. Testar w ∈ L")
        print("  6. Prefixos, sufixos e subcadeias de w")
        print("  0. Voltar")
        op = _perguntar("> ").strip()
        try:
            if op == "1":
                mostrar_linguagem(sigma, ler_cadeia(_perguntar("w = ")))
            elif op == "2":
                u = ler_cadeia(_perguntar("u = "))
                v = ler_cadeia(_perguntar("v = "))
                mostrar_linguagem(sigma, u, concatenar_com=v)
            elif op == "3":
                mostrar_sigma(sigma, int(_perguntar("k = ")))
            elif op == "4":
                tipo = _perguntar("(1) finita  (2) expressão regular: ").strip()
                if tipo == "1":
                    palavras = _perguntar("Palavras separadas por vírgula (use ε para vazia): ")
                    L = lf.Linguagem.finita(sigma, [p.strip() for p in palavras.split(",")])
                else:
                    L = lf.Linguagem.por_regex(sigma, _perguntar("ER (ex.: a*b+ ou (a|b)*abb): ").strip())
                mostrar_pertinencia_linguagem(L, [])
            elif op == "5":
                if L is None:
                    print("Defina L primeiro (opção 4).")
                else:
                    mostrar_pertinencia_linguagem(L, [ler_cadeia(_perguntar("w = "))])
            elif op == "6":
                w = ler_cadeia(_perguntar("w = "))
                fmt = lambda xs: "{" + ", ".join(lf.formatar_cadeia(x) for x in xs) + "}"
                print(f"Prefixos:    {fmt(lf.prefixos(w))}")
                print(f"Sufixos:     {fmt(lf.sufixos(w))}")
                print(f"Subcadeias:  {fmt(lf.subcadeias(w))}")
            elif op == "0":
                return
        except (ValueError, re.error) as e:   # erro amigável (ex.: ER mal formada)
            print(f"Erro: {e}")


def _menu_glc() -> None:
    modo = _perguntar("(1) carregar JSON  (2) digitar produções: ").strip()
    try:
        if modo == "2":
            print("Digite as produções, uma variável por linha (ex.: S -> aSb | λ). Linha vazia termina.")
            linhas = []
            while True:
                l = _perguntar("  ")
                if not l.strip():
                    break
                linhas.append(l)
            g = Gramatica.de_texto("\n".join(linhas), "definida pelo usuário")
        else:
            arq = _escolher_arquivo(("glc",))
            if not arq:
                return
            g = Gramatica.carregar_json(arq)
    except ValueError as e:
        print(f"Erro: {e}")
        return
    mostrar_glc(g, [], fnc=_perguntar("Mostrar a Forma Normal de Chomsky? (s/N) ").lower() == "s")
    _loop_cadeias(lambda w: mostrar_glc_cadeia(g, w))


def mostrar_glc_cadeia(g: Gramatica, w: str) -> None:
    # reaproveita a exibição sem repetir o cabeçalho da gramática
    r = g.derivar(w)
    if r.passos:
        for i, p in enumerate(r.passos, 1):
            print(f"  {i:>2}. {descrever_passo(p)}")
        print("Árvore:")
        for linha in r.arvore.desenhar():
            print("  " + linha)
    print(f"Saída: {'Aceita' if r.aceita else 'Rejeita'}   ({r.motivo})")


def menu() -> None:
    while True:
        titulo("SIMULADOR DE LINGUAGENS FORMAIS E MODELOS COMPUTACIONAIS")
        print("  1. Linguagens formais (Σ, Σ*, Σ+, |w|, concatenação, L)")
        print("  2. Autômato finito (AFD / AFN / AFN-ε) via JSON")
        print("  3. Gramática livre de contexto (derivação + árvore)")
        print("  4. Autômato com pilha")
        print("  5. Máquina de Turing (w#w ou soma unária)")
        print("  6. Complexidade computacional")
        print("  7. Demonstração completa (exemplos do enunciado)")
        print("  0. Sair")
        op = _perguntar("> ").strip()
        try:
            if op == "1":
                _menu_linguagens()
            elif op == "2":
                arq = _escolher_arquivo(("afd", "afn"))
                if arq:
                    af = AutomatoFinito.carregar_json(arq)
                    mostrar_af(af, [], converter=af.tipo == "AFN")
                    _loop_cadeias(lambda w: mostrar_af_cadeia(af, w))
            elif op == "3":
                _menu_glc()
            elif op == "4":
                arq = _escolher_arquivo(("ap",))
                if arq:
                    ap = AutomatoPilha.carregar_json(arq)
                    mostrar_ap(ap, [])
                    _loop_cadeias(lambda w: mostrar_ap(ap, [w]))
            elif op == "5":
                arq = _escolher_arquivo(("mt",))
                if arq:
                    mt = MaquinaTuring.carregar_json(arq)
                    mostrar_mt(mt, [])
                    _loop_cadeias(lambda w: mostrar_mt(mt, [w]))
            elif op == "6":
                print(relatorio_teorico())
                if _perguntar("\nRodar medição empírica? (s/N) ").lower() == "s":
                    print(relatorio_empirico())
            elif op == "7":
                demonstracao()
            elif op == "0":
                return
        except ValueError as e:
            print(f"Erro: {e}")


def mostrar_af_cadeia(af: AutomatoFinito, w: str) -> None:
    r = af.executar(w)
    for p in r.passos[:LIMITE_PASSOS_EXIBIDOS]:
        print("  " + p)
    print("  " + " -> ".join(r.caminho))
    print(f"  {'ACEITA' if r.aceita else 'REJEITA'}   ({r.motivo})")


# ---------------------------------------------------------------------------
# Comandos diretos (argparse)
# ---------------------------------------------------------------------------
def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python main.py",
        description="Simulador de Linguagens Formais e Modelos Computacionais. "
                    "Sem argumentos, abre o menu interativo.")
    sub = p.add_subparsers(dest="comando")

    s = sub.add_parser("linguagem", help="Módulo 1: alfabeto, cadeia, Σ*, Σ+, concatenação, L")
    s.add_argument("--alfabeto", "-a", required=True, help='ex.: "a,b"')
    s.add_argument("--cadeia", "-w", default="", help="cadeia a validar (use ε para vazia)")
    s.add_argument("--concatenar", "-c", help="segunda cadeia para concatenar com w")
    s.add_argument("--sigma", "-k", type=int, help="enumerar Σ* e Σ+ até o tamanho k")
    s.add_argument("--linguagem", "-L", help='linguagem finita: "ab,ba,aabb"')
    s.add_argument("--regex", "-r", help="linguagem por expressão regular: a*b+")

    s = sub.add_parser("af", help="Módulo 2: executar AFD/AFN de um JSON")
    s.add_argument("arquivo")
    s.add_argument("cadeias", nargs="*")
    s.add_argument("--converter", action="store_true", help="mostra o AFD equivalente (AFN -> AFD)")

    s = sub.add_parser("glc", help="Módulo 3: derivação e árvore em uma GLC")
    s.add_argument("arquivo")
    s.add_argument("cadeias", nargs="*")
    s.add_argument("--fnc", action="store_true", help="mostra a Forma Normal de Chomsky")

    s = sub.add_parser("ap", help="Módulo 4: executar autômato com pilha")
    s.add_argument("arquivo")
    s.add_argument("cadeias", nargs="*")

    s = sub.add_parser("mt", help="Módulo 5: executar máquina de Turing")
    s.add_argument("arquivo")
    s.add_argument("cadeias", nargs="*")
    s.add_argument("--max-passos", type=int, default=10_000)
    s.add_argument("--sem-passos", action="store_true", help="não imprime a fita a cada passo")

    s = sub.add_parser("soma", help="Módulo 5 (opção B): soma dois naturais na MT unária")
    s.add_argument("a", type=int)
    s.add_argument("b", type=int)

    s = sub.add_parser("complexidade", help="Módulo 6: tabela O/Ω/Θ e medição empírica")
    s.add_argument("--empirico", action="store_true", help="roda os experimentos de medição")

    sub.add_parser("demo", help="roda todos os exemplos do enunciado em sequência")
    return p


def main(argv: list[str] | None = None) -> int:
    # garante acentos e símbolos (Σ, ε, δ, λ) no console do Windows, inclusive na entrada
    for fluxo in (sys.stdin, sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    args = criar_parser().parse_args(argv)
    try:
        if args.comando is None:
            menu()
        elif args.comando == "linguagem":
            sigma = lf.Alfabeto.de_texto(args.alfabeto)
            mostrar_linguagem(sigma, ler_cadeia(args.cadeia),
                              None if args.concatenar is None else ler_cadeia(args.concatenar),
                              args.sigma)
            w = [ler_cadeia(args.cadeia)]
            if args.linguagem:
                mostrar_pertinencia_linguagem(
                    lf.Linguagem.finita(sigma, args.linguagem.split(",")), w)
            if args.regex:
                mostrar_pertinencia_linguagem(lf.Linguagem.por_regex(sigma, args.regex), w)
        elif args.comando == "af":
            mostrar_af(AutomatoFinito.carregar_json(args.arquivo),
                       [ler_cadeia(c) for c in args.cadeias], args.converter)
        elif args.comando == "glc":
            mostrar_glc(Gramatica.carregar_json(args.arquivo),
                        [ler_cadeia(c) for c in args.cadeias], args.fnc)
        elif args.comando == "ap":
            mostrar_ap(AutomatoPilha.carregar_json(args.arquivo), [ler_cadeia(c) for c in args.cadeias])
        elif args.comando == "mt":
            mostrar_mt(MaquinaTuring.carregar_json(args.arquivo), [ler_cadeia(c) for c in args.cadeias],
                       args.max_passos, not args.sem_passos)
        elif args.comando == "soma":
            w = codificar_soma_unaria(args.a, args.b)
            print(f"{args.a} + {args.b} codificado em unário: {w}")
            mostrar_mt(MaquinaTuring.carregar_json(EXEMPLOS / "mt_soma_unaria.json"), [w])
        elif args.comando == "complexidade":
            titulo("MÓDULO 6 - COMPLEXIDADE COMPUTACIONAL")
            print(relatorio_teorico())
            if args.empirico:
                titulo("MEDIÇÃO EMPÍRICA")
                print(relatorio_empirico())
        elif args.comando == "demo":
            demonstracao()
    except (ValueError, FileNotFoundError, KeyError) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    return 0
