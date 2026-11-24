import type {
  ExemplosResponse,
  SimulacaoAFResponse,
  SimulacaoAPResponse,
  SimulacaoMTResponse,
} from './types';

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.erro || `Erro HTTP ${res.status}`);
  }
  return data as T;
}

export function carregarExemplos(): Promise<ExemplosResponse> {
  return requestJson<ExemplosResponse>('/api/exemplos');
}

export function simularAF(
  modelo: Record<string, unknown>,
  cadeia: string,
  converterAfd = false
): Promise<SimulacaoAFResponse> {
  return requestJson<SimulacaoAFResponse>('/api/simular/af', {
    method: 'POST',
    body: JSON.stringify({ modelo, cadeia, converterAfd }),
  });
}

export function simularAP(
  modelo: Record<string, unknown>,
  cadeia: string
): Promise<SimulacaoAPResponse> {
  return requestJson<SimulacaoAPResponse>('/api/simular/ap', {
    method: 'POST',
    body: JSON.stringify({ modelo, cadeia }),
  });
}

export function simularMT(
  modelo: Record<string, unknown>,
  cadeia: string,
  maxPassos = 2000
): Promise<SimulacaoMTResponse> {
  return requestJson<SimulacaoMTResponse>('/api/simular/mt', {
    method: 'POST',
    body: JSON.stringify({ modelo, cadeia, maxPassos }),
  });
}
