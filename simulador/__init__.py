"""
Simulador de Linguagens Formais e Modelos Computacionais.

Disciplina: Aspectos Teóricos da Computação (T291) - UNIFOR
Projeto prático em dupla - AV3

Pacotes / módulos:
    linguagens       -> Módulo 1: alfabetos, cadeias e linguagens formais
    automato_finito  -> Módulo 2: AFD, AFN e AFN-ε (com conversão AFN -> AFD)
    glc              -> Módulo 3: gramáticas livres de contexto (derivação, árvore, FNC, CYK)
    automato_pilha   -> Módulo 4: autômato com pilha (AP) não determinístico
    maquina_turing   -> Módulo 5: máquina de Turing determinística de fita única
    complexidade     -> Módulo 6: análise assintótica teórica + medição empírica
"""

__version__ = "1.0.0"

EPSILON_SIMBOLOS = {"", "ε", "λ", "eps", "epsilon", "lambda"}


def eh_epsilon(simbolo: str) -> bool:
    """Retorna True se o texto representa a cadeia vazia (ε / λ)."""
    return simbolo is None or simbolo.strip() in EPSILON_SIMBOLOS
