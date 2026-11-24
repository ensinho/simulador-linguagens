"""
MÓDULO 5 - MÁQUINA DE TURING (MT)
=================================

Definição formal (Sipser, def. 3.3):   M = (Q, Σ, Γ, δ, q0, q_aceita, q_rejeita)

* Q : estados                     * Γ : alfabeto da fita (Σ ⊂ Γ, branco ␣ ∈ Γ)
* Σ : alfabeto de entrada (␣ ∉ Σ) * δ : Q × Γ -> Q × Γ × {L, R}
* q0 : inicial; q_aceita / q_rejeita : estados de PARADA

Diferenças em relação aos autômatos anteriores:
  - a fita é de LEITURA E ESCRITA;
  - o cabeçote anda para a ESQUERDA ou para a DIREITA;
  - a fita é ilimitada (aqui: um dicionário posição -> símbolo, "infinito");
  - a máquina pode NÃO PARAR. Pelo PROBLEMA DA PARADA (Turing, 1936) não
    existe algoritmo que decida, para toda MT e entrada, se ela para. Por
    isso o simulador usa um LIMITE DE PASSOS: se for atingido, informamos
    "não parou dentro do limite" (não podemos concluir que é laço infinito).

Convenção: se não houver transição definida para (q, símbolo), a máquina
PARA e REJEITA (rejeição implícita, como nos diagramas do Sipser).

A MT pode ser usada como:
  * RECONHECEDOR (Opção A: L = { w#w | w ∈ {0,1}* })  -> ACEITA / REJEITA
  * TRANSDUTOR   (Opção B: soma unária 000100 -> 00000) -> conteúdo final da fita

Formato JSON (ver exemplos/mt_*.json):
    {"de": "q1", "le": "0", "para": "q2", "escreve": "x", "move": "R"}
    move ∈ {"L", "R", "S"} (S = permanece; equivalente a mover R e voltar L)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

BRANCO_PADRAO = "_"


@dataclass(frozen=True)
class TransicaoMT:
    de: str
    le: str
    para: str
    escreve: str
    move: str

    def __str__(self) -> str:
        return f"δ({self.de}, {self.le}) = ({self.para}, {self.escreve}, {self.move})"


@dataclass
class PassoMT:
    numero: int
    estado: str
    fita: str              # trecho visível da fita com o cabeçote marcado [x]
    transicao: str


@dataclass
class ResultadoMT:
    aceita: bool
    parou: bool
    cadeia: str
    passos: list[PassoMT]
    fita_final: str
    estado_final: str
    motivo: str
    numero_passos: int = 0
    celulas_usadas: int = 0

    def saida(self, branco: str = BRANCO_PADRAO) -> str:
        """Conteúdo da fita sem os brancos das extremidades (saída do transdutor)."""
        return self.fita_final.strip(branco)


@dataclass
class MaquinaTuring:
    estados: set[str]
    alfabeto: set[str]
    alfabeto_fita: set[str]
    estado_inicial: str
    estados_aceitacao: set[str]
    estado_rejeicao: str | None
    transicoes: dict[tuple[str, str], TransicaoMT] = field(default_factory=dict)
    branco: str = BRANCO_PADRAO
    descricao: str = ""
    modo: str = "reconhecedor"      # ou "transdutor"

    # ------------------------------------------------------------------ I/O
    @staticmethod
    def de_dict(dados: dict) -> "MaquinaTuring":
        branco = dados.get("branco", BRANCO_PADRAO)
        trans: dict[tuple[str, str], TransicaoMT] = {}
        for t in dados["transicoes"]:
            simbolos = t["le"] if isinstance(t["le"], list) else [t["le"]]
            for s in simbolos:
                escreve = t.get("escreve", s)          # padrão: reescreve o mesmo símbolo
                tr = TransicaoMT(t["de"], s, t["para"], escreve, t["move"].upper())
                if (t["de"], s) in trans:
                    raise ValueError(f"MT não determinística: duas transições para δ({t['de']}, {s})")
                trans[(t["de"], s)] = tr

        aceitacao = dados.get("estados_aceitacao") or [dados["estado_aceita"]]
        mt = MaquinaTuring(
            estados=set(dados["estados"]),
            alfabeto=set(dados["alfabeto"]),
            alfabeto_fita=set(dados["alfabeto_fita"]) | {branco},
            estado_inicial=dados["estado_inicial"],
            estados_aceitacao=set(aceitacao),
            estado_rejeicao=dados.get("estado_rejeita"),
            transicoes=trans,
            branco=branco,
            descricao=dados.get("descricao", ""),
            modo=dados.get("modo", "reconhecedor"),
        )
        erros = mt.validar()
        if erros:
            raise ValueError("MT inválida:\n  - " + "\n  - ".join(erros))
        return mt

    @staticmethod
    def carregar_json(caminho: str | Path) -> "MaquinaTuring":
        with open(caminho, encoding="utf-8") as f:
            return MaquinaTuring.de_dict(json.load(f))

    def validar(self) -> list[str]:
        erros = []
        if self.branco in self.alfabeto:
            erros.append("o símbolo branco não pode pertencer a Σ")
        if not self.alfabeto <= self.alfabeto_fita:
            erros.append("Σ deve estar contido em Γ")
        for q in {self.estado_inicial} | self.estados_aceitacao | ({self.estado_rejeicao} - {None}):
            if q not in self.estados:
                erros.append(f"estado '{q}' ∉ Q")
        for t in self.transicoes.values():
            if t.de not in self.estados or t.para not in self.estados:
                erros.append(f"{t}: estado inexistente")
            if t.le not in self.alfabeto_fita or t.escreve not in self.alfabeto_fita:
                erros.append(f"{t}: símbolo fora de Γ")
            if t.move not in ("L", "R", "S"):
                erros.append(f"{t}: movimento deve ser L, R ou S")
            if t.de in self.estados_aceitacao or t.de == self.estado_rejeicao:
                erros.append(f"{t}: estados de parada não podem ter transições de saída")
        return erros

    # ------------------------------------------------------------- execução
    def _fita_str(self, fita: dict[int, str], cabeca: int, marcar: bool = True) -> str:
        if fita:
            ini = min(min(fita), cabeca)
            fim = max(max(fita), cabeca)
        else:
            ini = fim = cabeca
        partes = []
        for i in range(ini, fim + 1):
            s = fita.get(i, self.branco)
            partes.append(f"[{s}]" if (marcar and i == cabeca) else s)
        return "".join(partes)

    def executar(self, w: str, max_passos: int = 10_000, registrar: bool = True) -> ResultadoMT:
        for i, a in enumerate(w):
            if a not in self.alfabeto:
                return ResultadoMT(False, True, w, [], w, self.estado_inicial,
                                   f"símbolo '{a}' (posição {i}) ∉ Σ")

        fita: dict[int, str] = {i: a for i, a in enumerate(w)}
        cabeca, estado = 0, self.estado_inicial
        passos: list[PassoMT] = []
        if registrar:
            passos.append(PassoMT(0, estado, self._fita_str(fita, cabeca), "configuração inicial"))
        visitadas = {0}

        for n in range(1, max_passos + 1):
            if estado in self.estados_aceitacao:
                return self._fim(True, w, passos, fita, cabeca, estado,
                                 f"atingiu o estado de aceitação {estado}", n - 1, visitadas)
            if estado == self.estado_rejeicao:
                return self._fim(False, w, passos, fita, cabeca, estado,
                                 f"atingiu o estado de rejeição {estado}", n - 1, visitadas)
            simbolo = fita.get(cabeca, self.branco)
            t = self.transicoes.get((estado, simbolo))
            if t is None:
                return self._fim(False, w, passos, fita, cabeca, estado,
                                 f"δ({estado}, {simbolo}) indefinida -> para e REJEITA", n - 1, visitadas)
            # executa a transição: escreve, move, muda de estado
            if t.escreve == self.branco:
                fita.pop(cabeca, None)
            else:
                fita[cabeca] = t.escreve
            cabeca += {"L": -1, "R": 1, "S": 0}[t.move]
            visitadas.add(cabeca)
            estado = t.para
            if registrar:
                passos.append(PassoMT(n, estado, self._fita_str(fita, cabeca), str(t)))

        # verifica uma última vez se o último passo levou a um estado de parada
        if estado in self.estados_aceitacao:
            return self._fim(True, w, passos, fita, cabeca, estado,
                             f"atingiu o estado de aceitação {estado}", max_passos, visitadas)
        if estado == self.estado_rejeicao:
            return self._fim(False, w, passos, fita, cabeca, estado,
                             f"atingiu o estado de rejeição {estado}", max_passos, visitadas)
        return ResultadoMT(False, False, w, passos, self._fita_str(fita, cabeca, False), estado,
                           f"NÃO PAROU em {max_passos} passos (limite). Pelo problema da parada, "
                           f"não é possível decidir em geral se ela pararia.",
                           max_passos, len(visitadas))

    def _fim(self, aceita, w, passos, fita, cabeca, estado, motivo, n, visitadas) -> ResultadoMT:
        return ResultadoMT(aceita, True, w, passos, self._fita_str(fita, cabeca, False),
                           estado, motivo, n, len(visitadas))

    def aceita(self, w: str) -> bool:
        return self.executar(w, registrar=False).aceita

    def __str__(self) -> str:
        linhas = [f"MT ({self.modo}): {self.descricao}",
                  f"Q = {sorted(self.estados)}",
                  f"Σ = {sorted(self.alfabeto)}   Γ = {sorted(self.alfabeto_fita)}   branco = '{self.branco}'",
                  f"q0 = {self.estado_inicial}   aceita = {sorted(self.estados_aceitacao)}   "
                  f"rejeita = {self.estado_rejeicao or '(implícito)'}",
                  "δ:"]
        linhas += [f"  {t}" for t in self.transicoes.values()]
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Utilitários para a Opção B (soma unária)
# ---------------------------------------------------------------------------
def codificar_soma_unaria(a: int, b: int) -> str:
    """3 + 2  ->  '000' + '1' + '00'  = '000100'."""
    if a < 0 or b < 0:
        raise ValueError("Representação unária só para naturais (≥ 0).")
    return "0" * a + "1" + "0" * b


def decodificar_unario(fita: str) -> int:
    return fita.count("0")
