export interface SugestaoCadeia {
  cadeia: string;
  esperado: boolean;
  rotulo: string;
}

export interface ExemploItem {
  id: string;
  nome: string;
  descricao: string;
  modelo: Record<string, unknown>;
  sugestoes: SugestaoCadeia[];
}

export interface ExemplosResponse {
  af: ExemploItem[];
  ap: ExemploItem[];
  mt: ExemploItem[];
}

// --- Módulo 2: Autômato Finito ---
export interface TransicaoAFUsada {
  de: string;
  simbolo: string;
  para: string;
}

export interface PassoAF {
  numero: number;
  estadosAnterior: string[];
  estadosAtivos: string[];
  simboloLido: string | null;
  posEntrada: number;
  transicoesUsadas: TransicaoAFUsada[];
  descricao: string;
  travou: boolean;
}

export interface LinhaTabelaAF {
  estado: string;
  inicial: boolean;
  final: boolean;
  celulas: Record<string, string[]>;
}

export interface ModeloAF {
  tipo: string;
  descricao: string;
  alfabeto: string[];
  estados: string[];
  estado_inicial: string;
  estados_finais: string[];
  transicoes: Array<{
    de: string;
    simbolo: string;
    para: string | string[];
  }>;
}

export interface SimulacaoAFResponse {
  aceita: boolean;
  motivo: string;
  cadeia: string;
  operacoes: number;
  tipo: string;
  ehDeterministico: boolean;
  ehCompleto: boolean;
  modelo: ModeloAF;
  simbolosTabela: string[];
  tabela: LinhaTabelaAF[];
  passos: PassoAF[];
}

// --- Módulo 4: Autômato com Pilha ---
export interface TransicaoAP {
  de: string;
  le: string;
  desempilha: string;
  para: string;
  empilha: string;
}

export interface PassoAP {
  numero: number;
  estado: string;
  estadoAnterior: string | null;
  lido: string;
  posEntrada: number;
  restante: string;
  pilha: string[];
  pilhaTexto: string;
  operacao: string;
  operacaoCompleta: string;
  tipoOperacao: 'inicio' | 'push' | 'pop' | 'keep' | 'replace' | 'erro';
  transicao: TransicaoAP | null;
}

export interface ModeloAP {
  tipo: string;
  descricao: string;
  alfabeto: string[];
  alfabeto_pilha: string[];
  estados: string[];
  estado_inicial: string;
  simbolo_inicial_pilha: string;
  estados_finais: string[];
  aceitacao: string;
  transicoes: TransicaoAP[];
}

export interface SimulacaoAPResponse {
  aceita: boolean;
  motivo: string;
  cadeia: string;
  configuracoesExploradas: number;
  ehDeterministico: boolean;
  aceitacao: string;
  modelo: ModeloAP;
  passos: PassoAP[];
}

// --- Módulo 5: Máquina de Turing ---
export interface TransicaoMT {
  de: string;
  le: string;
  para: string;
  escreve: string;
  move: 'L' | 'R' | 'S';
}

export interface PassoMT {
  numero: number;
  estado: string;
  estadoAnterior: string | null;
  cabeca: number;
  celulas: Record<string, string>;
  celulaEscrita: number | null;
  transicao: TransicaoMT | null;
  descricao: string;
}

export interface ModeloMT {
  tipo: string;
  modo: 'reconhecedor' | 'transdutor';
  descricao: string;
  estados: string[];
  alfabeto: string[];
  alfabeto_fita: string[];
  branco: string;
  estado_inicial: string;
  estados_aceitacao: string[];
  estado_rejeicao: string | null;
  transicoes: TransicaoMT[];
}

export interface SimulacaoMTResponse {
  aceita: boolean;
  parou: boolean;
  cadeia: string;
  motivo: string;
  modo: 'reconhecedor' | 'transdutor';
  fitaFinal: string;
  saida: string;
  saidaUnaria: number | null;
  numeroPassos: number;
  celulasUsadas: number;
  branco: string;
  modelo: ModeloMT;
  passos: PassoMT[];
}
