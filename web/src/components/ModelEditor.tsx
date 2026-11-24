import { useEffect, useState } from 'react';

type ModelKind = 'af' | 'ap' | 'mt';

interface ModelEditorProps {
  kind: ModelKind;
  open: boolean;
  modelo: Record<string, unknown>;
  modeloOriginal: Record<string, unknown>;
  onApply: (novoModelo: Record<string, unknown>) => void;
  onClose: () => void;
}

function splitList(text: string): string[] {
  return Array.from(
    new Set(
      text
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    )
  );
}

function toStringArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x));
  if (typeof v === 'string' && v.trim()) return [v.trim()];
  return [];
}

export function ModelEditor({
  kind,
  open,
  modelo,
  modeloOriginal,
  onApply,
  onClose,
}: ModelEditorProps) {
  const [mode, setMode] = useState<'fields' | 'json'>('fields');
  const [draft, setDraft] = useState<Record<string, unknown>>(modelo);
  const [jsonText, setJsonText] = useState(() => JSON.stringify(modelo, null, 2));
  const [err, setErr] = useState<string | null>(null);

  // Text buffers for comma-separated list inputs so typing commas feels natural
  const [estadosStr, setEstadosStr] = useState('');
  const [alfabetoStr, setAlfabetoStr] = useState('');
  const [extraAlfabetoStr, setExtraAlfabetoStr] = useState('');

  const syncFromModel = (m: Record<string, unknown>) => {
    const clone = JSON.parse(JSON.stringify(m)) as Record<string, unknown>;
    setDraft(clone);
    setJsonText(JSON.stringify(clone, null, 2));
    setEstadosStr(toStringArray(clone.estados).join(', '));
    setAlfabetoStr(toStringArray(clone.alfabeto).join(', '));
    if (kind === 'ap') {
      setExtraAlfabetoStr(toStringArray(clone.alfabeto_pilha).join(', '));
    } else if (kind === 'mt') {
      setExtraAlfabetoStr(toStringArray(clone.alfabeto_fita).join(', '));
    }
    setErr(null);
  };

  useEffect(() => {
    syncFromModel(modelo);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelo, kind]);

  if (!open) return null;

  const updateDraft = (next: Record<string, unknown>) => {
    setDraft(next);
    setJsonText(JSON.stringify(next, null, 2));
    setErr(null);
  };

  const handleSwitchMode = (nextMode: 'fields' | 'json') => {
    if (nextMode === 'fields' && mode === 'json') {
      try {
        const parsed = JSON.parse(jsonText) as Record<string, unknown>;
        syncFromModel(parsed);
        setMode('fields');
      } catch (e) {
        setErr(e instanceof Error ? `JSON inválido: ${e.message}` : 'JSON inválido');
      }
      return;
    }
    setJsonText(JSON.stringify(draft, null, 2));
    setErr(null);
    setMode(nextMode);
  };

  const handleApply = () => {
    if (mode === 'json') {
      try {
        const parsed = JSON.parse(jsonText) as Record<string, unknown>;
        setErr(null);
        onApply(parsed);
      } catch (e) {
        setErr(e instanceof Error ? `JSON inválido: ${e.message}` : 'JSON inválido');
      }
      return;
    }

    // Normalize any comma-separated transition fields before sending to Python
    const normalized = JSON.parse(JSON.stringify(draft)) as Record<string, unknown>;
    if (Array.isArray(normalized.transicoes)) {
      normalized.transicoes = (normalized.transicoes as Array<Record<string, unknown>>).map(
        (t) => {
          const row = { ...t };
          if (kind === 'af') {
            const isAfn = String(normalized.tipo ?? 'AFD').toUpperCase() !== 'AFD';
            if (isAfn && typeof row.para === 'string') {
              row.para = splitList(row.para);
            } else if (!isAfn && Array.isArray(row.para)) {
              row.para = row.para[0] ?? '';
            }
          } else if (kind === 'mt' && typeof row.le === 'string' && row.le.includes(',')) {
            const parts = splitList(row.le);
            row.le = parts.length > 1 ? parts : parts[0] ?? '';
          }
          return row;
        }
      );
    }
    updateDraft(normalized);
    onApply(normalized);
  };

  const handleReset = () => {
    syncFromModel(modeloOriginal);
    onApply(modeloOriginal);
  };

  const estados = toStringArray(draft.estados);
  const transicoes = Array.isArray(draft.transicoes)
    ? (draft.transicoes as Array<Record<string, unknown>>)
    : [];

  const updateEstados = (raw: string) => {
    setEstadosStr(raw);
    const list = splitList(raw);
    updateDraft({ ...draft, estados: list });
  };

  const updateAlfabeto = (raw: string) => {
    setAlfabetoStr(raw);
    updateDraft({ ...draft, alfabeto: splitList(raw) });
  };

  const updateExtraAlfabeto = (raw: string, fieldName: 'alfabeto_pilha' | 'alfabeto_fita') => {
    setExtraAlfabetoStr(raw);
    updateDraft({ ...draft, [fieldName]: splitList(raw) });
  };

  const toggleFinal = (state: string, key: 'estados_finais' | 'estados_aceitacao') => {
    const current =
      key === 'estados_aceitacao'
        ? toStringArray(draft.estados_aceitacao ?? draft.estado_aceita)
        : toStringArray(draft.estados_finais);
    const next = current.includes(state)
      ? current.filter((s) => s !== state)
      : [...current, state];
    if (key === 'estados_aceitacao') {
      const updated: Record<string, unknown> = { ...draft, estados_aceitacao: next };
      delete updated.estado_aceita;
      updateDraft(updated);
    } else {
      updateDraft({ ...draft, estados_finais: next });
    }
  };

  const updateTransition = (idx: number, patch: Record<string, unknown>) => {
    const next = transicoes.map((t, i) => (i === idx ? { ...t, ...patch } : t));
    updateDraft({ ...draft, transicoes: next });
  };

  const removeTransition = (idx: number) => {
    const next = transicoes.filter((_, i) => i !== idx);
    updateDraft({ ...draft, transicoes: next });
  };

  const addTransition = () => {
    const q0 = String(draft.estado_inicial ?? estados[0] ?? 'q0');
    const a0 = toStringArray(draft.alfabeto)[0] ?? 'a';
    let item: Record<string, unknown>;
    if (kind === 'af') {
      const isAfd = String(draft.tipo ?? 'AFD').toUpperCase() === 'AFD';
      item = { de: q0, simbolo: a0, para: isAfd ? q0 : [q0] };
    } else if (kind === 'ap') {
      const z0 = String(draft.simbolo_inicial_pilha ?? 'Z');
      item = { de: q0, le: a0, desempilha: z0, para: q0, empilha: z0 };
    } else {
      item = { de: q0, le: a0, escreve: a0, move: 'R', para: q0 };
    }
    updateDraft({ ...draft, transicoes: [...transicoes, item] });
  };

  const finaisAfAp = toStringArray(draft.estados_finais);
  const finaisMt = toStringArray(draft.estados_aceitacao ?? draft.estado_aceita);

  return (
    <section className="section-card">
      <div className="section-header">
        <h2 className="section-title">Editar modelo e JSON</h2>
        <div className="editor-tabs">
          <button
            type="button"
            className={`editor-tab ${mode === 'fields' ? 'active' : ''}`}
            onClick={() => handleSwitchMode('fields')}
          >
            Campos
          </button>
          <button
            type="button"
            className={`editor-tab ${mode === 'json' ? 'active' : ''}`}
            onClick={() => handleSwitchMode('json')}
          >
            JSON
          </button>
        </div>
      </div>

      <div className="section-body">
        {mode === 'fields' ? (
          <>
            <div className="editor-form-grid">
              {kind === 'af' && (
                <div className="field">
                  <label>Tipo</label>
                  <select
                    value={String(draft.tipo ?? 'AFD').toUpperCase()}
                    onChange={(e) => updateDraft({ ...draft, tipo: e.target.value })}
                  >
                    <option value="AFD">AFD</option>
                    <option value="AFN">AFN</option>
                  </select>
                </div>
              )}

              {kind === 'mt' && (
                <div className="field">
                  <label>Modo</label>
                  <select
                    value={String(draft.modo ?? 'reconhecedor')}
                    onChange={(e) => updateDraft({ ...draft, modo: e.target.value })}
                  >
                    <option value="reconhecedor">Reconhecedor</option>
                    <option value="transdutor">Transdutor</option>
                  </select>
                </div>
              )}

              <div className="field">
                <label>Estados Q (separados por vírgula)</label>
                <input
                  type="text"
                  className="mono"
                  value={estadosStr}
                  onChange={(e) => updateEstados(e.target.value)}
                />
              </div>

              <div className="field">
                <label>Alfabeto Σ (separados por vírgula)</label>
                <input
                  type="text"
                  className="mono"
                  value={alfabetoStr}
                  onChange={(e) => updateAlfabeto(e.target.value)}
                />
              </div>

              {kind === 'ap' && (
                <div className="field">
                  <label>Alfabeto da pilha Γ</label>
                  <input
                    type="text"
                    className="mono"
                    value={extraAlfabetoStr}
                    onChange={(e) => updateExtraAlfabeto(e.target.value, 'alfabeto_pilha')}
                  />
                </div>
              )}

              {kind === 'mt' && (
                <div className="field">
                  <label>Alfabeto da fita Γ</label>
                  <input
                    type="text"
                    className="mono"
                    value={extraAlfabetoStr}
                    onChange={(e) => updateExtraAlfabeto(e.target.value, 'alfabeto_fita')}
                  />
                </div>
              )}

              <div className="field">
                <label>Estado inicial (q₀)</label>
                <select
                  value={String(draft.estado_inicial ?? '')}
                  onChange={(e) =>
                    updateDraft({ ...draft, estado_inicial: e.target.value })
                  }
                >
                  {estados.map((q) => (
                    <option key={q} value={q}>
                      {q}
                    </option>
                  ))}
                </select>
              </div>

              {kind === 'ap' && (
                <>
                  <div className="field">
                    <label>Símbolo inicial da pilha (Z₀)</label>
                    <input
                      type="text"
                      className="mono"
                      value={String(draft.simbolo_inicial_pilha ?? 'Z')}
                      onChange={(e) =>
                        updateDraft({ ...draft, simbolo_inicial_pilha: e.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <label>Critério de aceitação</label>
                    <select
                      value={String(draft.aceitacao ?? 'estado_final')}
                      onChange={(e) =>
                        updateDraft({ ...draft, aceitacao: e.target.value })
                      }
                    >
                      <option value="estado_final">Estado final</option>
                      <option value="pilha_vazia">Pilha vazia</option>
                    </select>
                  </div>
                </>
              )}

              {kind === 'mt' && (
                <>
                  <div className="field">
                    <label>Símbolo branco</label>
                    <input
                      type="text"
                      className="mono"
                      value={String(draft.branco ?? '_')}
                      onChange={(e) => updateDraft({ ...draft, branco: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label>Estado de rejeição (opcional)</label>
                    <select
                      value={String(draft.estado_rejeita ?? '')}
                      onChange={(e) => {
                        const val = e.target.value;
                        const next = { ...draft };
                        if (val) next.estado_rejeita = val;
                        else delete next.estado_rejeita;
                        updateDraft(next);
                      }}
                    >
                      <option value="">(implícito)</option>
                      {estados.map((q) => (
                        <option key={q} value={q}>
                          {q}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </div>

            <div className="field" style={{ marginBottom: 14 }}>
              <label>
                {kind === 'mt'
                  ? 'Estados de aceitação (clique para marcar/desmarcar)'
                  : 'Estados finais F (clique para marcar/desmarcar)'}
              </label>
              <div className="finals-picker">
                {estados.map((q) => {
                  const selected =
                    kind === 'mt' ? finaisMt.includes(q) : finaisAfAp.includes(q);
                  return (
                    <button
                      key={q}
                      type="button"
                      className={`state-toggle ${selected ? 'selected' : ''}`}
                      onClick={() =>
                        toggleFinal(
                          q,
                          kind === 'mt' ? 'estados_aceitacao' : 'estados_finais'
                        )
                      }
                    >
                      {selected ? `★ ${q}` : q}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="field">
              <label>Transições (δ)</label>
              <div className="trans-editor-wrap">
                <table className="trans-editor-table">
                  <thead>
                    {kind === 'af' && (
                      <tr>
                        <th>De</th>
                        <th>Símbolo (ε se vazio)</th>
                        <th>Para {String(draft.tipo ?? 'AFD') === 'AFN' ? '(vírgula p/ vários)' : ''}</th>
                        <th style={{ width: 76 }}>Ação</th>
                      </tr>
                    )}
                    {kind === 'ap' && (
                      <tr>
                        <th>De</th>
                        <th>Lê</th>
                        <th>Desempilha</th>
                        <th>Para</th>
                        <th>Empilha (topo à esq.)</th>
                        <th style={{ width: 76 }}>Ação</th>
                      </tr>
                    )}
                    {kind === 'mt' && (
                      <tr>
                        <th>De</th>
                        <th>Lê (vírgula p/ vários)</th>
                        <th>Escreve</th>
                        <th>Move</th>
                        <th>Para</th>
                        <th style={{ width: 76 }}>Ação</th>
                      </tr>
                    )}
                  </thead>
                  <tbody>
                    {transicoes.map((t, idx) => (
                      <tr key={idx}>
                        {kind === 'af' && (
                          <>
                            <td>
                              <input
                                type="text"
                                value={String(t.de ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { de: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.simbolo ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { simbolo: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={
                                  Array.isArray(t.para)
                                    ? t.para.join(', ')
                                    : String(t.para ?? '')
                                }
                                onChange={(e) =>
                                  updateTransition(idx, { para: e.target.value })
                                }
                              />
                            </td>
                          </>
                        )}

                        {kind === 'ap' && (
                          <>
                            <td>
                              <input
                                type="text"
                                value={String(t.de ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { de: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.le ?? 'ε')}
                                onChange={(e) =>
                                  updateTransition(idx, { le: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.desempilha ?? 'ε')}
                                onChange={(e) =>
                                  updateTransition(idx, { desempilha: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.para ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { para: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.empilha ?? 'ε')}
                                onChange={(e) =>
                                  updateTransition(idx, { empilha: e.target.value })
                                }
                              />
                            </td>
                          </>
                        )}

                        {kind === 'mt' && (
                          <>
                            <td>
                              <input
                                type="text"
                                value={String(t.de ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { de: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={
                                  Array.isArray(t.le)
                                    ? t.le.join(', ')
                                    : String(t.le ?? '')
                                }
                                onChange={(e) =>
                                  updateTransition(idx, { le: e.target.value })
                                }
                              />
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.escreve ?? '')}
                                placeholder="(mantém)"
                                onChange={(e) => {
                                  const v = e.target.value;
                                  const copy = { ...t };
                                  if (v === '') delete copy.escreve;
                                  else copy.escreve = v;
                                  const next = transicoes.map((row, i) =>
                                    i === idx ? copy : row
                                  );
                                  updateDraft({ ...draft, transicoes: next });
                                }}
                              />
                            </td>
                            <td>
                              <select
                                value={String(t.move ?? 'R').toUpperCase()}
                                onChange={(e) =>
                                  updateTransition(idx, { move: e.target.value })
                                }
                              >
                                <option value="R">R</option>
                                <option value="L">L</option>
                                <option value="S">S</option>
                              </select>
                            </td>
                            <td>
                              <input
                                type="text"
                                value={String(t.para ?? '')}
                                onChange={(e) =>
                                  updateTransition(idx, { para: e.target.value })
                                }
                              />
                            </td>
                          </>
                        )}

                        <td>
                          <button
                            type="button"
                            className="btn btn-xs btn-danger-outline"
                            onClick={() => removeTransition(idx)}
                          >
                            Remover
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={addTransition}
                >
                  + Adicionar transição
                </button>
              </div>
            </div>
          </>
        ) : (
          <textarea
            className="json-textarea"
            value={jsonText}
            onChange={(e) => {
              setJsonText(e.target.value);
              setErr(null);
            }}
            spellCheck={false}
          />
        )}

        {err && (
          <div className="error-msg" style={{ marginTop: 10 }}>
            {err}
          </div>
        )}

        <div className="editor-actions">
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleApply}
            >
              Aplicar e simular
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleReset}
            >
              Restaurar original
            </button>
          </div>
          <button type="button" className="btn btn-sm" onClick={onClose}>
            Fechar editor
          </button>
        </div>
      </div>
    </section>
  );
}
