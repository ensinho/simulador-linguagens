# Simulador de Linguagens Formais e Modelos Computacionais

Projeto prático em dupla (AV3) da disciplina **Aspectos Teóricos da Computação (T291)** da
**Universidade de Fortaleza (UNIFOR)**, ministrada pelo prof. Ildo Ramos Vieira.

O simulador modela, valida e executa os principais formalismos da Teoria da Computação,
mostrando **passo a passo** o que cada modelo faz com a cadeia de entrada:

| Módulo | Conteúdo | Destaques |
|---|---|---|
| 1. Linguagens formais | Σ, cadeias, Σ\*, Σ⁺, \|w\|, concatenação, linguagem L | L finita ou por expressão regular, união, concatenação e fecho de Kleene de linguagens |
| 2. Autômato finito | AFD, AFN e AFN-ε carregados por JSON | Passo a passo das transições, fecho-ε, conversão AFN → AFD (construção de subconjuntos) |
| 3. Gramática livre de contexto | Variáveis, terminais, produções, símbolo inicial | Derivação mais à esquerda passo a passo, árvore de derivação, Forma Normal de Chomsky, CYK |
| 4. Autômato com pilha | Pilha, empilhar e desempilhar | Leitura, estado e conteúdo da pilha a cada passo; APs não determinísticos (wwᴿ) |
| 5. Máquina de Turing | **Opção A**: L = {w#w} e **Opção B**: soma unária | Fita com o cabeçote marcado a cada passo, limite de passos (problema da parada) |
| 6. Complexidade | O, Ω e Θ (melhor, médio e pior caso) | Tabela teórica + medição empírica (operações / f(n)) |

> Linguagem: **Python 3.10+**, interface **console**, **sem dependências externas**.

---

## Como executar

### Pré-requisito
- Python 3.10 ou superior (`python --version`)

### Clonar e rodar
```bash
git clone https://github.com/ensinho/simulador-linguagens.git
cd simulador-linguagens

python main.py            # abre o MENU INTERATIVO
python main.py demo       # roda todos os exemplos do enunciado em sequência
python main.py --help     # lista os comandos diretos
```

> No Windows, se os símbolos (Σ, ε, δ) aparecerem estranhos no terminal, rode antes `chcp 65001`.

### Comandos diretos

| Comando | O que faz |
|---|---|
| `python main.py linguagem -a "a,b" -w abba -c ba -k 2` | Módulo 1: valida w, tamanho, concatenação, enumera Σ\* e Σ⁺ até k |
| `python main.py linguagem -a "a,b" -w aabb -r "a*b*"` | Testa w ∈ L com L dada por expressão regular (`-L "ab,ba"` para L finita) |
| `python main.py af exemplos/afd_enunciado.json ab aba` | Módulo 2: executa um AFD/AFN de um JSON |
| `python main.py af exemplos/afn_termina_em_ab.json abab --converter` | Executa AFN e mostra o AFD equivalente |
| `python main.py glc exemplos/glc_anbn.json aaabbb --fnc` | Módulo 3: derivação, árvore e Forma Normal de Chomsky |
| `python main.py ap exemplos/ap_anbn.json aaabbb aabbb` | Módulo 4: autômato com pilha |
| `python main.py mt exemplos/mt_w_sharp_w.json 01#01` | Módulo 5, opção A: MT que reconhece w#w |
| `python main.py mt exemplos/mt_soma_unaria.json 000100` | Módulo 5, opção B: soma unária |
| `python main.py soma 3 2` | Codifica 3+2 em unário e roda a MT de soma |
| `python main.py complexidade --empirico` | Módulo 6: tabela O/Ω/Θ + medição empírica |

Use `ε` (ou `vazia`) para passar a cadeia vazia.

### Testes automatizados
```bash
python -m unittest -v
```
São 33 testes. Vários deles são **exaustivos**: comparam o simulador com a definição matemática
da linguagem para **todas** as cadeias até um certo tamanho (ex.: o AP de wwᴿ é testado em todas
as 511 cadeias de {a,b}\* com tamanho ≤ 8).

---

## Exemplos de entrada e saída

### Módulo 1: linguagens formais (exemplo do enunciado)
Entrada:
```bash
python main.py linguagem -a "a,b" -w abba -c ba -k 2
```
Saída:
```
Σ = {a, b}
Entrada: abba

Cadeia válida para Σ  (w ∈ Σ*)
Tamanho = 4
Reverso wᴿ = abba
w ∈ Σ+ ? sim  (Σ+ = Σ* - {ε})
Concatenação: abba · ba = abbaba   (|uv| = 4 + 2 = 6)

Σ* (até tamanho 2) = {ε, a, b, aa, ab, ba, bb}
   |Σ⁰ ∪ ... ∪ Σ^2| = 7 cadeias (Σ* completo é INFINITO, mas enumerável)
Σ+ (até tamanho 2) = {a, b, aa, ab, ba, bb}
```
Com símbolo inválido (`-w abca`):
```
Cadeia INVÁLIDA para Σ  (w ∉ Σ*): símbolo(s) 'c' na posição 2
```

### Módulo 2: autômato finito (exemplo do enunciado)
Entrada: `exemplos/afd_enunciado.json` (q0 –a→ q1, q1 –b→ q2) e a cadeia `ab`
```bash
python main.py af exemplos/afd_enunciado.json ab
```
Saída:
```
δ     | a  | b
------+----+---
-> q0 | q1 | -
   q1 | -  | q2
  *q2 | -  | -

Entrada: ab
  Início: estado q0, entrada 'ab'
  Passo 1: δ(q0, a) = q1    [lido: a | resta: b]
  Passo 2: δ(q1, b) = q2    [lido: ab | resta: ε]
Saída:
  q0 -> q1 -> q2
  ACEITA   (terminou em q2 ∈ F)
```
AFN (simulação por conjuntos de estados ativos):
```
Entrada: abab
  Passo 1: lê 'a': δ({q0}, a) = {q0, q1}  ->  fecho-ε = {q0, q1}
  Passo 2: lê 'b': δ({q0, q1}, b) = {q0, q2}  ->  fecho-ε = {q0, q2}
  ...
  {q0} -> {q0, q1} -> {q0, q2} -> {q0, q1} -> {q0, q2}
  ACEITA   (estados ativos ∩ F = {q2} ≠ ∅)
```

### Módulo 3: gramática livre de contexto (exemplo do enunciado)
Entrada: `S -> aSb | λ` e a cadeia `aaabbb`
```bash
python main.py glc exemplos/glc_anbn.json aaabbb
```
Saída:
```
Derivação mais à esquerda passo a passo:
   1. S                    ⇒ aSb                  [aplicando S -> aSb]
   2. aSb                  ⇒ aaSbb                [aplicando S -> aSb]
   3. aaSbb                ⇒ aaaSbbb              [aplicando S -> aSb]
   4. aaaSbbb              ⇒ aaabbb               [aplicando S -> λ]

Árvore de derivação (simplificada):
  S
  ├── a
  ├── S
  │   ├── a
  │   ├── S
  │   │   ├── a
  │   │   ├── S
  │   │   │   └── λ
  │   │   └── b
  │   └── b
  └── b
  fronteira (folhas) = aaabbb
Saída: Aceita   (derivação mais à esquerda encontrada em 4 passo(s))
```

### Módulo 4: autômato com pilha, L = { aⁿbⁿ | n ≥ 1 }
```bash
python main.py ap exemplos/ap_anbn.json aaabbb
```
Saída:
```
Passo | Estado | Leitura | Entrada restante | Pilha (topo à esq.) | Operação
------+--------+---------+------------------+---------------------+---------------------------------
0     | q0     | -       | aaabbb           | Z                   | configuração inicial
1     | q0     | a       | aabbb            | AZ                  | empilha A   [δ(q0, a, Z) = (q0, AZ)]
2     | q0     | a       | abbb             | AAZ                 | empilha A   [δ(q0, a, A) = (q0, AA)]
3     | q0     | a       | bbb              | AAAZ                | empilha A   [δ(q0, a, A) = (q0, AA)]
4     | q1     | b       | bb               | AAZ                 | desempilha A   [δ(q0, b, A) = (q1, ε)]
5     | q1     | b       | b                | AZ                  | desempilha A   [δ(q1, b, A) = (q1, ε)]
6     | q1     | b       | ε                | Z                   | desempilha A   [δ(q1, b, A) = (q1, ε)]
7     | q2     | ε       | ε                | Z                   | mantém Z no topo   [δ(q1, ε, Z) = (q2, Z)]
Saída: ACEITA ✔   (entrada consumida e estado q2 ∈ F)
```

### Módulo 5: máquina de Turing
**Opção B, soma unária (exemplo do enunciado: 000100 = 3 + 2):**
```bash
python main.py mt exemplos/mt_soma_unaria.json 000100
```
```
Passo | Estado    | Fita ([x] = cabeçote)        | Transição aplicada
    0 | q0        | [0]00100                     | configuração inicial
    1 | q0        | 0[0]0100                     | δ(q0, 0) = (q0, 0, R)
    2 | q0        | 00[0]100                     | δ(q0, 0) = (q0, 0, R)
    3 | q0        | 000[1]00                     | δ(q0, 0) = (q0, 0, R)
    4 | q1        | 0000[0]0                     | δ(q0, 1) = (q1, 0, R)
    5 | q1        | 00000[0]                     | δ(q1, 0) = (q1, 0, R)
    6 | q1        | 000000[_]                    | δ(q1, 0) = (q1, 0, R)
    7 | q2        | 00000[0]                     | δ(q1, _) = (q2, _, L)
    8 | qf        | 0000[0]                      | δ(q2, 0) = (qf, _, L)
Total de passos: 8   células visitadas: 7
Resultado: 00000   (= 5 em unário)
```
**Opção A, L = { w#w }:**
```bash
python main.py mt exemplos/mt_w_sharp_w.json 01#01 01#10 --sem-passos
```
```
Entrada: 01#01
Total de passos: 18   células visitadas: 7
Saída: ACEITA ✔   (atingiu o estado de aceitação qaceita)

Entrada: 01#10
Total de passos: 4   células visitadas: 5
Saída: REJEITA ✘   (atingiu o estado de rejeição qrejeita)
```
Sem `--sem-passos`, a fita é impressa a cada passo, com o cabeçote entre colchetes (`x1#[0]1`).

### Módulo 6: complexidade (trecho da medição empírica)
```bash
python main.py complexidade --empirico
```
```
--- MT w#w   [esperado Θ(n²)]
       n |    operações |      razão
      11 |           72 |     0.5950
     101 |         5202 |     0.5100
     401 |        80802 |     0.5025      <- razão estabiliza em 1/2: T(n) = (n+1)²/2 = Θ(n²)
```

---

## Formato dos arquivos JSON

Todos os modelos ficam em [`exemplos/`](exemplos). Crie os seus seguindo o mesmo formato.

<details>
<summary><b>AFD / AFN / AFN-ε</b></summary>

```json
{
  "tipo": "AFN",
  "alfabeto": ["a", "b"],
  "estados": ["q0", "q1", "q2"],
  "estado_inicial": "q0",
  "estados_finais": ["q2"],
  "transicoes": [
    {"de": "q0", "simbolo": "a", "para": ["q0", "q1"]},
    {"de": "q1", "simbolo": "b", "para": "q2"},
    {"de": "q2", "simbolo": "ε", "para": "q0"}
  ]
}
```
Em `"tipo": "AFD"` o simulador recusa transições ε e destinos múltiplos.
</details>

<details>
<summary><b>GLC</b></summary>

```json
{
  "variaveis": ["S"],
  "terminais": ["a", "b"],
  "simbolo_inicial": "S",
  "producoes": { "S": ["aSb", "λ"] }
}
```
Cada corpo é lido caractere a caractere; `λ`, `ε` ou `""` é a cadeia vazia. No menu interativo também
dá para digitar as produções no formato `S -> aSb | λ`.
</details>

<details>
<summary><b>Autômato com pilha</b></summary>

```json
{
  "alfabeto": ["a", "b"],
  "alfabeto_pilha": ["A", "Z"],
  "estados": ["q0", "q1", "q2"],
  "estado_inicial": "q0",
  "simbolo_inicial_pilha": "Z",
  "estados_finais": ["q2"],
  "aceitacao": "estado_final",
  "transicoes": [
    {"de": "q0", "le": "a", "desempilha": "Z", "para": "q0", "empilha": "AZ"}
  ]
}
```
`empilha` é escrito com o **topo à esquerda**. `aceitacao` pode ser `estado_final` ou `pilha_vazia`.
</details>

<details>
<summary><b>Máquina de Turing</b></summary>

```json
{
  "modo": "reconhecedor",
  "estados": ["q1", "q2", "qaceita", "qrejeita"],
  "alfabeto": ["0", "1", "#"],
  "alfabeto_fita": ["0", "1", "#", "x", "_"],
  "branco": "_",
  "estado_inicial": "q1",
  "estado_aceita": "qaceita",
  "estado_rejeita": "qrejeita",
  "transicoes": [
    {"de": "q1", "le": "0", "escreve": "x", "move": "R", "para": "q2"},
    {"de": "q2", "le": ["0", "1"], "move": "R", "para": "q2"}
  ]
}
```
`modo` = `reconhecedor` (aceita/rejeita) ou `transdutor` (a saída é o conteúdo final da fita).
Sem `escreve`, a MT reescreve o próprio símbolo lido. `move` ∈ {L, R, S}.
</details>

---

## Estrutura do projeto

```
simulador-linguagens/
├── main.py                       # ponto de entrada (menu e comandos)
├── simulador/
│   ├── linguagens.py             # Módulo 1: Alfabeto, Linguagem, operações com cadeias
│   ├── automato_finito.py        # Módulo 2: AFD, AFN, AFN-ε, AFN -> AFD
│   ├── glc.py                    # Módulo 3: Gramatica, FNC, CYK, derivação, árvore
│   ├── automato_pilha.py         # Módulo 4: AutomatoPilha (BFS de configurações)
│   ├── maquina_turing.py         # Módulo 5: MaquinaTuring (fita, cabeçote, limite de passos)
│   ├── complexidade.py           # Módulo 6: tabela O/Ω/Θ e medição empírica
│   └── cli.py                    # interface de console
├── exemplos/                     # modelos prontos em JSON
├── tests/test_simulador.py       # 33 testes (unittest)
└── docs/
    ├── documento_tecnico.md      # documento técnico
    └── uml/                      # diagramas de classes e de casos de uso (PlantUML)
```

## Documentação
- [Documento técnico](docs/documento_tecnico.md): introdução, fundamentação teórica, arquitetura (UML), implementação, complexidade e conclusão

## Referências principais
- SIPSER, M. *Introdução à Teoria da Computação*. Cengage Learning, 2007.
- MENEZES, P. B. *Linguagens Formais e Autômatos*. 6. ed. Bookman, 2011.
- LEWIS, H. R.; PAPADIMITRIOU, C. H. *Elementos de Teoria da Computação*. 2. ed. Bookman, 2000.
- TOSCANI, L. V.; VELOSO, P. A. S. *Complexidade de Algoritmos*. 3. ed. Bookman, 2012.

## Autores
- _Enzo Esmeraldo_, matrícula _2516948_
- _Lucas Braide_, matrícula _2526367_
