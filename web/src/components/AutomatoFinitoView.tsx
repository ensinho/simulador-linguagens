import { useCallback, useEffect, useMemo, useState } from 'react';
import { simularAF } from '../api';
import type { ExemploItem, SimulacaoAFResponse } from '../types';
import { InputStrip } from './InputStrip';
import { ModelEditor } from './ModelEditor';
import { PlaybackBar } from './PlaybackBar';
import { StateGraph, type GraphEdge } from './StateGraph';

interface AutomatoFinitoViewProps {
  exemplos: ExemploItem[];
}

export function AutomatoFinitoView({ exemplos }: AutomatoFinitoViewProps) {
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
  const [converterAfd, setConverterAfd] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);

  const [resultado, setResultado] = useState<SimulacaoAFResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const executar = useCallback(
    async (mod: Record<string, unknown>, w: string, conv: boolean) => {
      setErro(null);
      setIsPlaying(false);
      try {
        const res = await simularAF(mod, w, conv);
        setResultado(res);
        setStep(0);
      } catch (e) {
        setErro(e instanceof Error ? e.message : 'Erro ao simular.');
      }
    },
    []
  );

  useEffect(() => {
    if (!selectedExample) return;
    const wInicial = selectedExample.sugestoes[0]?.cadeia ?? '';
    setModeloAtual(selectedExample.modelo);
    setCadeia(wInicial);
    setConverterAfd(false);
    setEditorOpen(false);
    executar(selectedExample.modelo, wInicial, false);
  }, [selectedExample, executar]);

  const ehAfn = String(modeloAtual.tipo ?? 'AFD').toUpperCase() !== 'AFD';
  const passoAtual = resultado?.passos[step];
  const isLast = resultado ? step === resultado.passos.length - 1 : false;

  const edges: GraphEdge[] = useMemo(() => {
    if (!resultado) return [];
    const list: GraphEdge[] = [];
    for (const t of resultado.modelo.transicoes) {
      const destinos = Array.isArray(t.para) ? t.para : [t.para];
      for (const para of destinos) {
        list.push({
          de: t.de,
          para,
          label: t.simbolo || 'ε',
          key: `${t.de}|${t.simbolo || 'ε'}|${para}`,
        });
      }
    }
    return list;
  }, [resultado]);

  const activeEdgeKeys = useMemo(() => {
    if (!passoAtual) return [];
    return passoAtual.transicoesUsadas.map(
      (t) => `${t.de}|${t.simbolo || 'ε'}|${t.para}`
    );
  }, [passoAtual]);

  return (
    <>
      {/* 1. Configuração */}
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">1. Modelo e entrada</h2>
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
              executar(modeloAtual, cadeia, converterAfd);
            }}
          >
            <div className="field" style={{ flex: '1 1 260px' }}>
              <label htmlFor="af-model">Autômato</label>
              <select
                id="af-model"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {exemplos.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.nome} ({String(ex.modelo.tipo ?? 'AFD')})
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="af-word">Cadeia de entrada (w)</label>
              <input
                id="af-word"
                type="text"
                className="mono-input"
                value={cadeia}
                onChange={(e) => setCadeia(e.target.value)}
                placeholder="ex.: ab (vazio = ε)"
              />
            </div>

            <button type="submit" className="btn btn-primary">
              Simular
            </button>

            {ehAfn && (
              <label className="check-btn">
                <input
                  type="checkbox"
                  checked={converterAfd}
                  onChange={(e) => {
                    const next = e.target.checked;
                    setConverterAfd(next);
                    executar(modeloAtual, cadeia, next);
                  }}
                />
                Converter AFN → AFD
              </label>
            )}
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
                    executar(modeloAtual, s.cadeia, converterAfd);
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

      {/* Editor estruturado de campos e JSON */}
      {selectedExample && (
        <ModelEditor
          kind="af"
          open={editorOpen}
          modelo={modeloAtual}
          modeloOriginal={selectedExample.modelo}
          onApply={(novo) => {
            setModeloAtual(novo);
            executar(novo, cadeia, converterAfd);
          }}
          onClose={() => setEditorOpen(false)}
        />
      )}

      {erro && <div className="error-msg">{erro}</div>}

      {/* 2. Visualização dos Estados */}
      {resultado && passoAtual && (
        <>
          <section className="section-card">
            <div className="section-header">
              <h2 className="section-title">
                2. Estados do autômato ({resultado.tipo})
              </h2>
              <span className="section-meta mono">
                Q = {'{' + resultado.modelo.estados.join(', ') + '}'} · F ={' '}
                {'{' + resultado.modelo.estados_finais.join(', ') + '}'}
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
                <div className="status-rule">{passoAtual.descricao}</div>
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
                  : resultado.tipo === 'AFD'
                    ? `Estado: ${passoAtual.estadosAtivos[0] ?? '∅'}`
                    : `Ativos: {${passoAtual.estadosAtivos.join(', ') || '∅'}}`}
              </span>
            </div>

            <div className="stage-content">
              <InputStrip
                cadeia={resultado.cadeia}
                posEntrada={passoAtual.posEntrada}
                simboloLido={passoAtual.simboloLido}
              />

              <StateGraph
                states={resultado.modelo.estados}
                initialState={resultado.modelo.estado_inicial}
                acceptStates={resultado.modelo.estados_finais}
                edges={edges}
                activeStates={passoAtual.estadosAtivos}
                activeEdgeKeys={activeEdgeKeys}
                finalVerdict={
                  isLast ? (resultado.aceita ? 'accept' : 'reject') : null
                }
              />
            </div>
          </section>

          {/* 3. Tabela e Histórico */}
          <div className="bottom-grid">
            <section className="section-card">
              <div className="section-header">
                <h2 className="section-title">Tabela de transições (δ)</h2>
                <span className="section-meta mono">
                  Σ = {'{' + resultado.modelo.alfabeto.join(', ') + '}'}
                </span>
              </div>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Estado</th>
                      {resultado.simbolosTabela.map((s) => (
                        <th key={s}>{s}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {resultado.tabela.map((linha) => {
                      const rowActive = passoAtual.estadosAtivos.includes(linha.estado);
                      const wasSource = passoAtual.estadosAnterior.includes(linha.estado);
                      const marca = `${linha.inicial ? '→' : ''}${linha.final ? '*' : ''}`;
                      return (
                        <tr
                          key={linha.estado}
                          className={rowActive ? 'active-row' : ''}
                        >
                          <td>
                            {marca ? `${marca} ` : ''}
                            {linha.estado}
                          </td>
                          {resultado.simbolosTabela.map((simb) => {
                            const destinos = linha.celulas[simb] ?? [];
                            const texto =
                              destinos.length === 0
                                ? '-'
                                : resultado.tipo === 'AFD'
                                  ? destinos[0]
                                  : `{${destinos.join(', ')}}`;
                            const cellHit =
                              wasSource && passoAtual.simboloLido === simb;
                            return (
                              <td key={simb} className={cellHit ? 'active-cell' : ''}>
                                {texto}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="section-card">
              <div className="section-header">
                <h2 className="section-title">Histórico de passos</h2>
                <span className="section-meta">Clique em uma linha para ir ao passo</span>
              </div>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Lido</th>
                      <th>Estado(s)</th>
                      <th>Transição</th>
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
                        <td>{p.simboloLido ?? '-'}</td>
                        <td>
                          {resultado.tipo === 'AFD'
                            ? p.estadosAtivos[0] ?? '∅'
                            : `{${p.estadosAtivos.join(', ') || '∅'}}`}
                        </td>
                        <td>{p.descricao}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </>
      )}
    </>
  );
}
