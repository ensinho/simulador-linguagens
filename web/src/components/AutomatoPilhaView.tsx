import { useCallback, useEffect, useMemo, useState } from 'react';
import { simularAP } from '../api';
import type { ExemploItem, SimulacaoAPResponse } from '../types';
import { InputStrip } from './InputStrip';
import { ModelEditor } from './ModelEditor';
import { PlaybackBar } from './PlaybackBar';
import { StateGraph, type GraphEdge } from './StateGraph';

interface AutomatoPilhaViewProps {
  exemplos: ExemploItem[];
}

export function AutomatoPilhaView({ exemplos }: AutomatoPilhaViewProps) {
  const [selectedId, setSelectedId] = useState<string>(exemplos[0]?.id ?? '');
  const selectedExample = useMemo(
    () => exemplos.find((e) => e.id === selectedId) ?? exemplos[0],
    [exemplos, selectedId]
  );

  const [modeloAtual, setModeloAtual] = useState<Record<string, unknown>>(
    selectedExample?.modelo ?? {}
  );
  const [cadeia, setCadeia] = useState<string>(
    selectedExample?.sugestoes[0]?.cadeia ?? ''
  );
  const [editorOpen, setEditorOpen] = useState(false);

  const [resultado, setResultado] = useState<SimulacaoAPResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const executar = useCallback(async (mod: Record<string, unknown>, w: string) => {
    setErro(null);
    setIsPlaying(false);
    try {
      const res = await simularAP(mod, w);
      setResultado(res);
      setStep(0);
    } catch (e) {
      setErro(e instanceof Error ? e.message : 'Erro ao simular.');
    }
  }, []);

  useEffect(() => {
    if (!selectedExample) return;
    const wInicial = selectedExample.sugestoes[0]?.cadeia ?? '';
    setModeloAtual(selectedExample.modelo);
    setCadeia(wInicial);
    setEditorOpen(false);
    executar(selectedExample.modelo, wInicial);
  }, [selectedExample, executar]);

  const passoAtual = resultado?.passos[step];
  const isLast = resultado ? step === resultado.passos.length - 1 : false;

  const edges: GraphEdge[] = useMemo(() => {
    if (!resultado) return [];
    return resultado.modelo.transicoes.map((t) => ({
      de: t.de,
      para: t.para,
      label: `${t.le}, ${t.desempilha}→${t.empilha}`,
      key: `${t.de}|${t.le}|${t.desempilha}|${t.para}|${t.empilha}`,
    }));
  }, [resultado]);

  const activeEdgeKeys = useMemo(() => {
    const t = passoAtual?.transicao;
    if (!t) return [];
    return [`${t.de}|${t.le}|${t.desempilha}|${t.para}|${t.empilha}`];
  }, [passoAtual]);

  const opClass =
    passoAtual?.tipoOperacao === 'push'
      ? 'push'
      : passoAtual?.tipoOperacao === 'pop'
        ? 'pop'
        : '';

  return (
    <>
      {/* 1. Configuração */}
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">1. Modelo de AP e entrada</h2>
          <button
            type="button"
            className={`btn btn-sm ${editorOpen ? 'btn-primary' : ''}`}
            onClick={() => setEditorOpen((v) => !v)}
          >
            {editorOpen ? 'Ocultar editor' : 'Editar modelo / JSON'}
          </button>
        </div>

        <div className="section-body">
          <form
            className="controls-grid"
            onSubmit={(e) => {
              e.preventDefault();
              executar(modeloAtual, cadeia);
            }}
          >
            <div className="field" style={{ flex: '1 1 260px' }}>
              <label htmlFor="ap-model">Autômato com pilha</label>
              <select
                id="ap-model"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {exemplos.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.nome}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="ap-word">Cadeia de entrada (w)</label>
              <input
                id="ap-word"
                type="text"
                className="mono-input"
                value={cadeia}
                onChange={(e) => setCadeia(e.target.value)}
                placeholder="ex.: aaabbb (vazio = ε)"
              />
            </div>

            <button type="submit" className="btn btn-primary">
              Simular
            </button>
          </form>

          <div className="sub-row">
            <div className="chips-group">
              <span className="chips-label">Testar:</span>
              {selectedExample?.sugestoes.map((s) => (
                <button
                  key={s.rotulo}
                  type="button"
                  className={`chip-btn ${cadeia === s.cadeia ? 'active' : ''}`}
                  onClick={() => {
                    setCadeia(s.cadeia);
                    executar(modeloAtual, s.cadeia);
                  }}
                >
                  {s.rotulo}
                </button>
              ))}
            </div>
            {resultado?.modelo.descricao && (
              <span className="model-desc">{resultado.modelo.descricao}</span>
            )}
          </div>
        </div>
      </section>

      {selectedExample && (
        <ModelEditor
          kind="ap"
          open={editorOpen}
          modelo={modeloAtual}
          modeloOriginal={selectedExample.modelo}
          onApply={(novo) => {
            setModeloAtual(novo);
            executar(novo, cadeia);
          }}
          onClose={() => setEditorOpen(false)}
        />
      )}

      {erro && <div className="error-msg">{erro}</div>}

      {/* 2. Estados + Pilha */}
      {resultado && passoAtual && (
        <>
          <section className="section-card">
            <div className="section-header">
              <h2 className="section-title">2. Estados e pilha do AP</h2>
              <span className="section-meta mono">
                Γ = {'{' + resultado.modelo.alfabeto_pilha.join(', ') + '}'} · Z₀ ={' '}
                {resultado.modelo.simbolo_inicial_pilha} ·{' '}
                {resultado.ehDeterministico ? 'Determinístico' : 'Não determinístico'}
              </span>
            </div>

            <PlaybackBar
              currentStep={step}
              totalSteps={resultado.passos.length}
              isPlaying={isPlaying}
              onStepChange={(s) => {
                setStep(s);
                if (s >= resultado.passos.length - 1) setIsPlaying(false);
              }}
              onTogglePlay={() => setIsPlaying((p) => !p)}
            />

            <div
              className={`status-bar ${
                isLast ? (resultado.aceita ? 'accept' : 'reject') : ''
              }`}
            >
              <div>
                <div className="status-rule">{passoAtual.operacaoCompleta}</div>
                {isLast && <div className="status-sub">{resultado.motivo}</div>}
              </div>
              <span
                className={`verdict-chip ${
                  isLast ? (resultado.aceita ? 'accept' : 'reject') : ''
                }`}
              >
                {isLast
                  ? resultado.aceita
                    ? 'ACEITA'
                    : 'REJEITA'
                  : `Estado: ${passoAtual.estado}`}
              </span>
            </div>

            <div className="stage-content">
              <InputStrip
                cadeia={resultado.cadeia}
                posEntrada={passoAtual.posEntrada}
                simboloLido={passoAtual.lido === '-' ? null : passoAtual.lido}
              />

              <div className="stage-split">
                <StateGraph
                  states={resultado.modelo.estados}
                  initialState={resultado.modelo.estado_inicial}
                  acceptStates={resultado.modelo.estados_finais}
                  edges={edges}
                  activeStates={[passoAtual.estado]}
                  activeEdgeKeys={activeEdgeKeys}
                  finalVerdict={
                    isLast ? (resultado.aceita ? 'accept' : 'reject') : null
                  }
                />

                <div className="stack-panel">
                  <div className="stack-top-bar">
                    <span className="stack-title">Pilha</span>
                    <span className={`stack-op-pill ${opClass}`}>
                      {passoAtual.operacao}
                    </span>
                  </div>

                  <div className="stack-well" aria-label="Pilha do AP">
                    {passoAtual.pilha.length === 0 ? (
                      <div className="stack-empty">ε (vazia)</div>
                    ) : (
                      passoAtual.pilha.map((sym, idx) => {
                        const isTop = idx === 0;
                        const isBase =
                          idx === passoAtual.pilha.length - 1 &&
                          sym === resultado.modelo.simbolo_inicial_pilha;
                        const pushed = isTop && passoAtual.tipoOperacao === 'push';

                        return (
                          <div
                            key={`${idx}-${sym}`}
                            className={`stack-cell ${isTop ? 'top' : ''} ${
                              pushed ? 'pushed' : ''
                            } ${isBase ? 'base' : ''}`}
                          >
                            {sym}
                            {isTop && <span className="stack-top-tag">← TOPO</span>}
                          </div>
                        );
                      })
                    )}
                  </div>

                  <div className="stack-foot">
                    topo→fundo: {passoAtual.pilhaTexto} ({passoAtual.pilha.length})
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 3. Histórico */}
          <section className="section-card">
            <div className="section-header">
              <h2 className="section-title">Histórico de configurações</h2>
              <span className="section-meta">Clique em uma linha para ir ao passo</span>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Estado</th>
                    <th>Lido</th>
                    <th>Resta</th>
                    <th>Pilha (topo à esq.)</th>
                    <th>Operação</th>
                  </tr>
                </thead>
                <tbody>
                  {resultado.passos.map((p, idx) => (
                    <tr
                      key={p.numero}
                      className={`clickable ${idx === step ? 'active-row' : ''}`}
                      onClick={() => {
                        setIsPlaying(false);
                        setStep(idx);
                      }}
                    >
                      <td>{p.numero}</td>
                      <td>{p.estado}</td>
                      <td>{p.lido}</td>
                      <td>{p.restante || 'ε'}</td>
                      <td>{p.pilhaTexto}</td>
                      <td>{p.operacaoCompleta}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
