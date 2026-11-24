"""
Ponto de entrada do Simulador de Linguagens Formais e Modelos Computacionais.

    python main.py            -> menu interativo
    python main.py --help     -> lista de comandos diretos
    python main.py demo       -> roda todos os exemplos do enunciado
"""

import sys

from simulador.cli import main

if __name__ == "__main__":
    sys.exit(main())
