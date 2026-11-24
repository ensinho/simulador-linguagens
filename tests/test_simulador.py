"""
Testes automatizados de todos os módulos.

Executar:   python -m unittest -v

Além dos exemplos do enunciado, vários testes são EXAUSTIVOS: comparam o
simulador com a definição matemática da linguagem para TODAS as cadeias de
Σ* até um certo tamanho (é a forma prática de "provar" que o modelo está certo).
"""

import contextlib
import io
import itertools
import unittest
from pathlib import Path

from simulador import linguagens as lf
from simulador.automato_finito import AutomatoFinito
from simulador.automato_pilha import AutomatoPilha
from simulador.cli import main
from simulador.complexidade import TABELA
from simulador.glc import Gramatica
from simulador.maquina_turing import MaquinaTuring, codificar_soma_unaria

EX = Path(__file__).resolve().parent.parent / "exemplos"


def todas(sigma: str, max_len: int):
    for n in range(max_len + 1):
        for t in itertools.product(sigma, repeat=n):
            yield "".join(t)


# ---------------------------------------------------------------------------
class TestModulo1Linguagens(unittest.TestCase):
    def setUp(self):
        self.sigma = lf.Alfabeto.de_texto("{a, b}")

    def test_exemplo_enunciado(self):
        ok, _ = self.sigma.validar_cadeia("abba")
        self.assertTrue(ok)
        self.assertEqual(lf.tamanho("abba"), 4)

    def test_cadeia_invalida_aponta_posicao(self):
        ok, inval = self.sigma.validar_cadeia("abca")
        self.assertFalse(ok)
        self.assertEqual(inval, [(2, "c")])

    def test_cadeia_vazia_pertence_a_sigma_estrela(self):
        self.assertTrue(self.sigma.pertence(""))
        self.assertEqual(lf.tamanho(""), 0)

    def test_alfabeto_invalido(self):
        with self.assertRaises(ValueError):
            lf.Alfabeto.de_texto("")
        with self.assertRaises(ValueError):
            lf.Alfabeto.de_texto("ab, c")

    def test_sigma_estrela_e_mais(self):
        estrela = list(self.sigma.sigma_estrela(2))
        mais = list(self.sigma.sigma_mais(2))
        self.assertEqual(estrela, ["", "a", "b", "aa", "ab", "ba", "bb"])
        self.assertEqual(mais, estrela[1:])                    # Σ+ = Σ* - {ε}
        self.assertEqual(self.sigma.quantidade_sigma_estrela(3), 1 + 2 + 4 + 8)

    def test_concatenacao_propriedades(self):
        u, v = "ab", "ba"
        self.assertEqual(lf.concatenar(u, v), "abba")
        self.assertEqual(len(lf.concatenar(u, v)), len(u) + len(v))
        self.assertEqual(lf.concatenar("", u), u)               # ε é elemento neutro
        self.assertEqual(lf.potencia("ab", 3), "ababab")
        self.assertEqual(lf.potencia("ab", 0), "")

    def test_linguagem_finita_e_regex(self):
        L1 = lf.Linguagem.finita(self.sigma, ["ab", "ba", "ε"])
        self.assertTrue(L1.pertence(""))
        self.assertTrue(L1.pertence("ba"))
        self.assertFalse(L1.pertence("aa"))
        L2 = lf.Linguagem.por_regex(self.sigma, "a*b+")
        self.assertTrue(L2.pertence("aabbb"))
        self.assertFalse(L2.pertence("aab a"))
        with self.assertRaises(ValueError):
            lf.Linguagem.finita(self.sigma, ["abc"])

    def test_operacoes_sobre_linguagens(self):
        L1 = lf.Linguagem.finita(self.sigma, ["a"])
        L2 = lf.Linguagem.finita(self.sigma, ["b", "bb"])
        self.assertEqual(L1.concatenacao(L2).palavras, {"ab", "abb"})
        self.assertEqual(L1.uniao(L2).palavras, {"a", "b", "bb"})
        estrela = lf.Linguagem.finita(self.sigma, ["ab"]).fecho_kleene()
        self.assertTrue(estrela.pertence(""))
        self.assertTrue(estrela.pertence("ababab"))
        self.assertFalse(estrela.pertence("aba"))


# ---------------------------------------------------------------------------
class TestModulo2AutomatoFinito(unittest.TestCase):
    def test_exemplo_enunciado(self):
        af = AutomatoFinito.carregar_json(EX / "afd_enunciado.json")
        r = af.executar("ab")
        self.assertTrue(r.aceita)
        self.assertEqual(r.caminho, ["q0", "q1", "q2"])
        self.assertFalse(af.aceita("aba"))       # trava em q2
        self.assertFalse(af.aceita(""))

    def test_afd_numero_par_de_a_exaustivo(self):
        af = AutomatoFinito.carregar_json(EX / "afd_numero_par_de_a.json")
        self.assertTrue(af.eh_completo())
        for w in todas("ab", 7):
            self.assertEqual(af.aceita(w), w.count("a") % 2 == 0, w)

    def test_afd_multiplo_de_3_exaustivo(self):
        af = AutomatoFinito.carregar_json(EX / "afd_binario_multiplo_3.json")
        for w in todas("01", 9):
            esperado = int(w, 2) % 3 == 0 if w else True
            self.assertEqual(af.aceita(w), esperado, w)

    def test_afn_termina_em_ab_exaustivo(self):
        afn = AutomatoFinito.carregar_json(EX / "afn_termina_em_ab.json")
        for w in todas("ab", 7):
            self.assertEqual(afn.aceita(w), w.endswith("ab"), w)

    def test_afn_epsilon(self):
        afn = AutomatoFinito.carregar_json(EX / "afne_a_estrela_ou_b_estrela.json")
        self.assertEqual(afn.fecho_epsilon({"q0"}), {"q0", "qa", "qb"})
        for w in todas("ab", 6):
            esperado = set(w) <= {"a"} or set(w) <= {"b"}
            self.assertEqual(afn.aceita(w), esperado, w)

    def test_construcao_subconjuntos_equivalente(self):
        for arq in ("afn_termina_em_ab.json", "afne_a_estrela_ou_b_estrela.json"):
            afn = AutomatoFinito.carregar_json(EX / arq)
            afd = afn.para_afd()
            self.assertTrue(afd.eh_deterministico())
            self.assertEqual(afd.validar(), [])
            for w in todas("ab", 7):
                self.assertEqual(afn.aceita(w), afd.aceita(w), (arq, w))

    def test_validacao_afd(self):
        base = {"tipo": "AFD", "alfabeto": ["a"], "estados": ["p", "q"],
                "estado_inicial": "p", "estados_finais": ["q"]}
        with self.assertRaises(ValueError):       # ε em AFD
            AutomatoFinito.de_dict({**base, "transicoes": [{"de": "p", "simbolo": "ε", "para": "q"}]})
        with self.assertRaises(ValueError):       # dois destinos em AFD
            AutomatoFinito.de_dict({**base, "transicoes": [{"de": "p", "simbolo": "a", "para": ["p", "q"]}]})
        with self.assertRaises(ValueError):       # estado inexistente
            AutomatoFinito.de_dict({**base, "transicoes": [{"de": "p", "simbolo": "a", "para": "r"}]})

    def test_simbolo_fora_do_alfabeto(self):
        af = AutomatoFinito.carregar_json(EX / "afd_numero_par_de_a.json")
        r = af.executar("abc")
        self.assertFalse(r.aceita)
        self.assertIn("não pertence a Σ", r.motivo)


# ---------------------------------------------------------------------------
class TestModulo3GLC(unittest.TestCase):
    def test_exemplo_enunciado(self):
        g = Gramatica.carregar_json(EX / "glc_anbn.json")
        r = g.derivar("aaabbb")
        self.assertTrue(r.aceita)
        self.assertEqual(r.derivacao_texto(), "S ⇒ aSb ⇒ aaSbb ⇒ aaaSbbb ⇒ aaabbb")
        self.assertEqual(r.arvore.fronteira(), "aaabbb")
        self.assertFalse(g.derivar("aab").aceita)

    def test_anbn_exaustivo(self):
        g = Gramatica.carregar_json(EX / "glc_anbn.json")
        fnc = g.para_fnc()
        for w in todas("ab", 8):
            k = len(w) // 2
            esperado = w == "a" * k + "b" * k
            self.assertEqual(g.cyk(w, fnc)[0], esperado, w)

    def test_palindromos_exaustivo(self):
        g = Gramatica.carregar_json(EX / "glc_palindromos.json")
        fnc = g.para_fnc()
        for w in todas("ab", 7):
            self.assertEqual(g.cyk(w, fnc)[0], w == w[::-1], w)

    def test_parenteses_exaustivo(self):
        g = Gramatica.carregar_json(EX / "glc_parenteses.json")
        fnc = g.para_fnc()

        def balanceada(w):
            nivel = 0
            for c in w:
                nivel += 1 if c == "(" else -1
                if nivel < 0:
                    return False
            return nivel == 0

        for w in todas("()", 8):
            self.assertEqual(g.cyk(w, fnc)[0], balanceada(w), w)

    def test_expressoes_derivacao_e_arvore(self):
        g = Gramatica.carregar_json(EX / "glc_expressoes.json")
        for w in ["a", "a+a*a", "(a+a)*a", "((a))"]:
            r = g.derivar(w)
            self.assertTrue(r.aceita, w)
            self.assertEqual(r.arvore.fronteira(), w)
            # cada passo expande a variável MAIS À ESQUERDA
            for p in r.passos:
                antes = p.forma_antes[:p.posicao]
                self.assertTrue(all(s in g.terminais for s in antes))
        for w in ["a+", "()", "a**a", "+a"]:
            self.assertFalse(g.derivar(w).aceita, w)

    def test_fnc_tem_forma_correta(self):
        for arq in ("glc_anbn.json", "glc_expressoes.json", "glc_palindromos.json", "glc_parenteses.json"):
            fnc = Gramatica.carregar_json(EX / arq).para_fnc()
            self.assertTrue(fnc.esta_na_fnc(), arq)

    def test_gramatica_por_texto(self):
        g = Gramatica.de_texto("S -> aSb | λ")
        self.assertTrue(g.derivar("ab").aceita)
        self.assertEqual(g.anulaveis(), {"S"})
        with self.assertRaises(ValueError):
            Gramatica.de_texto("S aSb")


# ---------------------------------------------------------------------------
class TestModulo4AutomatoPilha(unittest.TestCase):
    def test_anbn_enunciado(self):
        ap = AutomatoPilha.carregar_json(EX / "ap_anbn.json")
        self.assertTrue(ap.eh_deterministico())
        r = ap.executar("aaabbb")
        self.assertTrue(r.aceita)
        pilhas = [p.pilha for p in r.passos]
        self.assertEqual(pilhas, ["Z", "AZ", "AAZ", "AAAZ", "AAZ", "AZ", "Z", "Z"])
        for w in todas("ab", 8):
            k = len(w) // 2
            esperado = k >= 1 and w == "a" * k + "b" * k       # n ≥ 1
            self.assertEqual(ap.aceita(w), esperado, w)

    def test_wwr_nao_deterministico(self):
        ap = AutomatoPilha.carregar_json(EX / "ap_wwr.json")
        self.assertFalse(ap.eh_deterministico())
        for w in todas("ab", 8):
            esperado = len(w) % 2 == 0 and w == w[::-1]
            self.assertEqual(ap.aceita(w), esperado, w)

    def test_aceitacao_por_pilha_vazia(self):
        ap = AutomatoPilha.de_dict({
            "alfabeto": ["(", ")"], "alfabeto_pilha": ["P", "Z"], "estados": ["q"],
            "estado_inicial": "q", "simbolo_inicial_pilha": "Z", "aceitacao": "pilha_vazia",
            "transicoes": [
                {"de": "q", "le": "(", "desempilha": "ε", "para": "q", "empilha": "P"},
                {"de": "q", "le": ")", "desempilha": "P", "para": "q", "empilha": "ε"},
                {"de": "q", "le": "ε", "desempilha": "Z", "para": "q", "empilha": "ε"},
            ]})
        self.assertTrue(ap.aceita("(()())"))
        self.assertFalse(ap.aceita("(()"))
        self.assertFalse(ap.aceita("())"))


# ---------------------------------------------------------------------------
class TestModulo5MaquinaTuring(unittest.TestCase):
    def test_w_sharp_w_exaustivo(self):
        mt = MaquinaTuring.carregar_json(EX / "mt_w_sharp_w.json")
        for w in todas("01#", 7):
            partes = w.split("#")
            esperado = len(partes) == 2 and partes[0] == partes[1]
            r = mt.executar(w, registrar=False)
            self.assertTrue(r.parou, w)
            self.assertEqual(r.aceita, esperado, w)

    def test_soma_unaria_enunciado(self):
        mt = MaquinaTuring.carregar_json(EX / "mt_soma_unaria.json")
        r = mt.executar("000100")
        self.assertTrue(r.aceita)
        self.assertEqual(r.saida(), "00000")

    def test_soma_unaria_varios(self):
        mt = MaquinaTuring.carregar_json(EX / "mt_soma_unaria.json")
        for a in range(6):
            for b in range(6):
                w = codificar_soma_unaria(a, b)
                r = mt.executar(w, registrar=False)
                self.assertEqual(r.saida(), "0" * (a + b), (a, b))
                self.assertEqual(r.numero_passos, len(w) + 2)   # Θ(n) exato

    def test_limite_de_passos_problema_da_parada(self):
        # MT que anda para a direita para sempre: nunca alcança "fim"
        mt = MaquinaTuring.de_dict({
            "estados": ["q", "fim"], "alfabeto": ["0"], "alfabeto_fita": ["0"],
            "estado_inicial": "q", "estado_aceita": "fim",
            "transicoes": [
                {"de": "q", "le": ["0", "_"], "move": "R", "para": "q"}]})
        r = mt.executar("0", max_passos=500, registrar=False)
        self.assertFalse(r.parou)
        self.assertIn("NÃO PAROU", r.motivo)


# ---------------------------------------------------------------------------
class TestModulo6EInterface(unittest.TestCase):
    def test_tabela_cobre_todos_os_modulos(self):
        modulos = {a.modulo.split(" ")[0] for a in TABELA}
        self.assertEqual(modulos, {"1", "2", "3", "4", "5"})
        for a in TABELA:
            self.assertTrue(a.melhor and a.pior and a.justificativa)

    def test_cli_demo_e_comandos(self):
        comandos = [
            ["demo"],
            ["linguagem", "-a", "a,b", "-w", "abba", "-c", "ba", "-k", "2", "-L", "ab,abba", "-r", "a*b*"],
            ["af", str(EX / "afn_termina_em_ab.json"), "abab", "--converter"],
            ["glc", str(EX / "glc_expressoes.json"), "a+a", "--fnc"],
            ["ap", str(EX / "ap_wwr.json"), "abba"],
            ["mt", str(EX / "mt_w_sharp_w.json"), "01#01"],
            ["soma", "3", "2"],
            ["complexidade"],
        ]
        for argv in comandos:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(argv), 0, argv)
            self.assertTrue(buf.getvalue())

    def test_cli_arquivo_inexistente(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["af", "nao_existe.json", "a"]), 1)


if __name__ == "__main__":
    unittest.main()
