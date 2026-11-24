interface InputStripProps {
  cadeia: string;
  posEntrada: number;
  simboloLido?: string | null;
}

export function InputStrip({ cadeia, posEntrada, simboloLido }: InputStripProps) {
  const chars = Array.from(cadeia);

  return (
    <div className="word-bar">
      <span className="word-label">Entrada</span>
      <div className="word-cells">
        {chars.length === 0 ? (
          <span className="word-empty">ε (vazia)</span>
        ) : (
          chars.map((ch, idx) => {
            const done = idx < posEntrada;
            const now =
              simboloLido !== null && simboloLido !== 'ε' && idx === posEntrada - 1;
            return (
              <div
                key={`${idx}-${ch}`}
                className={`word-cell ${now ? 'now' : done ? 'done' : ''}`}
              >
                {ch}
              </div>
            );
          })
        )}
      </div>
      <span className="word-meta">
        lido: <strong>{cadeia.slice(0, posEntrada) || 'ε'}</strong> · resta:{' '}
        <strong>{cadeia.slice(posEntrada) || 'ε'}</strong>
        {simboloLido === 'ε' ? ' · transição ε' : ''}
      </span>
    </div>
  );
}
