import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { simularMT } from '../api';
import type { ExemploItem, SimulacaoMTResponse } from '../types';
import { ModelEditor } from './ModelEditor';
import { PlaybackBar } from './PlaybackBar';
import { StateGraph, type GraphEdge } from './StateGraph';

interface MaquinaTuringViewProps {
  exemplos: ExemploItem[];
}

export function MaquinaTuringView({ exemplos }: MaquinaTuringViewProps) {
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
  const [somaA, setSomaA] = useState(3);
  const [somaB, setSomaB] = useState(2);
  const [editorOpen, setEditorOpen] = useState(false);

  const [resultado, setResultado] = useState<SimulacaoMTResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [step, setStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const headRef = useRef<HTMLDivElement | null>(null);

  const executar = useCallback(async (mod: Record<string, unknown>, w: string) => {
    setErro(null);
    setIsPlaying(false);
    try {
      const res = await simularMT(mod, w, 2000);
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

  useEffect(() => {
    headRef.current?.scrollIntoView({
      behavior: 'smooth',
      inline: 'center',
      block: 'nearest',
    });
  }, [step, resultado]);

  const tapeIndices = useMemo(() => {
    if (!resultado) return [];
    let minIdx = 0;
    let maxIdx = Math.max(5, resultado.cadeia.length);
    for (const p of resultado.passos) {
      minIdx = Math.min(minIdx, p.cabeca);
      maxIdx = Math.max(maxIdx, p.cabeca);
      for (const k of Object.keys(p.celulas)) {
        const n = Number(k);
        minIdx = Math.min(minIdx, n);
        maxIdx = Math.max(maxIdx, n);
      }
    }
    const arr: number[] = [];
    for (let i = minIdx - 2; i <= maxIdx + 2; i++) arr.push(i);
    return arr;
  }, [resultado]);

  const edges: GraphEdge[] = useMemo(() => {
    if (!resultado) return [];
    return resultado.modelo.transicoes.map((t) => ({
      de: t.de,
      para: t.para,
      label:
        t.le === t.escreve
          ? `${t.le},${t.move}`
          : `${t.le}→${t.escreve},${t.move}`,
      key: `${t.de}|${t.le}|${t.para}|${t.escreve}|${t.move}`,
    }));
  }, [resultado]);

  const activeEdgeKeys = useMemo(() => {
    const t = passoAtual?.transicao;
    if (!t) return [];
    return [`${t.de}|${t.le}|${t.para}|${t.escreve}|${t.move}`];
  }, [passoAtual]);

  const rejectStates = resultado?.modelo.estado_rejeicao
    ? [resultado.modelo.estado_rejeicao]
    : [];

  const headTone = isLast
    ? !resultado?.parou
      ? ''
      : resultado?.aceita
        ? 'accept'
        : 'reject'
    : '';

  const isSomaUnaria =
    selectedExample?.id === 'mt_soma_unaria.json' ||
    resultado?.modo === 'transdutor';

  return (
    <>
      {/* 1. Configuração */}
      <section className="section-card">
        <div className="section-header">
          <h2 className="section-title">1. Modelo de MT e fita inicial</h2>
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
              <label htmlFor="mt-model">Máquina de Turing</label>
              <select
                id="mt-model"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {exemplos.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.nome} ({String(ex.modelo.modo ?? 'reconhecedor')})
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label htmlFor="mt-word">Conteúdo inicial da fita</label>
              <input
                id="mt-word"
                type="text"
                className="mono-input"
                value={cadeia}
                onChange={(e) => setCadeia(e.target.value)}
                placeholder="ex.: 01#01 ou 000100"
              />
            </div>

            <button type="submit" className="btn btn-primary">
              Simular
            </button>

            {isSomaUnaria && (
              <div className="field">
                <label>Soma unária (a + b)</label>
                <div className="unary-group">
                  <input
                    type="number"
                    className="num-input"
                    min={0}
                    max={12}
                    value={somaA}
                    onChange={(e) => setSomaA(Math.max(0, Number(e.target.value)))}
                    aria-label="a"
                  />
                  <strong>+</strong>
                  <input
                    type="number"
                    className="num-input"
                    min={0}
                    max={12}
                    value={somaB}
                    onChange={(e) => setSomaB(Math.max(0, Number(e.target.value)))}
                    aria-label="b"
                  />
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => {
                      const w = '0'.repeat(somaA) + '1' + '0'.repeat(somaB);
                      setCadeia(w);
                      executar(modeloAtual, w);
                    }}
                  >
                    Aplicar
                  </button>
                </div>
              </div>
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
          kind="mt"
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

      {/* 2. Fita + Estados */}
      {resultado && passoAtual && (
        <>
          <section className="section-card">
            <div className="section-header">
              <h2 className="section-title">
                2. Fita e estados da Máquina de Turing
              </h2>
              <span className="section-meta mono">
                Γ = {'{' + resultado.modelo.alfabeto_fita.join(', ') + '}'} · branco = '
                {resultado.branco}'
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
                isLast
                  ? !resultado.parou
                    ? 'warn'
                    : resultado.aceita
                      ? 'accept'
                      : 'reject'
                  : ''
              }`}
            >
              <div>
                <div className="status-rule">{passoAtual.descricao}</div>
                {isLast && (
                  <div className="status-sub">
                    {resultado.motivo}
                    {resultado.modo === 'transdutor' && (
                      <>
                        {' '}
                        · Saída final: <strong>{resultado.saida}</strong>
                        {resultado.saidaUnaria !== null &&
                          ` (${resultado.saidaUnaria} em unário)`}
                      </>
                    )}
                  </div>
                )}
              </div>
              <span
                className={`verdict-chip ${
                  isLast
                    ? !resultado.parou
                      ? 'warn'
                      : resultado.aceita
                        ? 'accept'
                        : 'reject'
                    : ''
                }`}
              >
                {isLast
                  ? !resultado.parou
                    ? 'LIMITE DE PASSOS'
                    : resultado.modo === 'transdutor'
                      ? `SAÍDA: ${resultado.saidaUnaria ?? resultado.saida}`
                      : resultado.aceita
                        ? 'ACEITA'
                        : 'REJEITA'
                  : `Cabeçote: pos ${passoAtual.cabeca}`}
              </span>
            </div>

            <div className="stage-content">
              <div className="tape-box">
                <div className="tape-scroll">
                  <div className="tape-row">
                    <div className="tape-dots">…</div>
                    {tapeIndices.map((idx) => {
                      const sym = passoAtual.celulas[String(idx)] ?? resultado.branco;
                      const isHead = idx === passoAtual.cabeca;
                      const isBlank = sym === resultado.branco;
                      const written =
                        !isHead && passoAtual.celulaEscrita === idx;

                      return (
                        <div
                          key={idx}
                          ref={isHead ? headRef : undefined}
                          className="tape-col"
                        >
                          <div className="tape-head">
                            {isHead && (
                              <>
                                <span className={`tape-state ${headTone}`}>
                                  {passoAtual.estado}
                                </span>
                                <span className={`tape-caret ${headTone}`} />
                              </>
                            )}
                          </div>
                          <div
                            className={`tape-cell ${isBlank ? 'blank' : ''} ${
                              isHead ? `head ${headTone}` : ''
                            } ${written ? 'written' : ''}`}
                          >
                            {sym}
                          </div>
                          <div className={`tape-idx ${isHead ? 'head' : ''}`}>
                            {idx}
                          </div>
                        </div>
                      );
                    })}
                    <div className="tape-dots">…</div>
                  </div>
                </div>

                <div className="tape-footer">
                  <span>
                    cabeçote: pos <strong>{passoAtual.cabeca}</strong> · estado{' '}
                    <strong>{passoAtual.estado}</strong>
                  </span>
                  <span>
                    {resultado.numeroPassos} passos · {resultado.celulasUsadas} células
                    visitadas
                  </span>
                </div>
              </div>

              <StateGraph
                states={resultado.modelo.estados}
                initialState={resultado.modelo.estado_inicial}
                acceptStates={resultado.modelo.estados_aceitacao}
                rejectStates={rejectStates}
                edges={edges}
                activeStates={[passoAtual.estado]}
                activeEdgeKeys={activeEdgeKeys}
                finalVerdict={
                  isLast && resultado.parou
                    ? resultado.aceita
                      ? 'accept'
                      : 'reject'
                    : null
                }
              />
            </div>
          </section>

          {/* 3. Histórico */}
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
                    <th>Estado</th>
                    <th>Posição</th>
                    <th>Transição aplicada</th>
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
                      <td>{p.cabeca}</td>
                      <td>{p.descricao}</td>
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
