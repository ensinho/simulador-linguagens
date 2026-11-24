import { useEffect, useState } from 'react';
import { carregarExemplos } from './api';
import { AutomatoFinitoView } from './components/AutomatoFinitoView';
import { AutomatoPilhaView } from './components/AutomatoPilhaView';
import { MaquinaTuringView } from './components/MaquinaTuringView';
import type { ExemplosResponse } from './types';

type TabKey = 'af' | 'ap' | 'mt';

export function App() {
  const [tab, setTab] = useState<TabKey>('af');
  const [exemplos, setExemplos] = useState<ExemplosResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    carregarExemplos()
      .then(setExemplos)
      .catch((e) =>
        setErro(
          e instanceof Error
            ? e.message
            : 'Sem conexão com o servidor Python (python api.py).'
        )
      );
  }, []);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">Simulador de Autômatos</div>
          <nav className="nav-tabs" aria-label="Modelos">
            <button
              type="button"
              className={`nav-tab ${tab === 'af' ? 'active' : ''}`}
              onClick={() => setTab('af')}
            >
              Estados (AFD / AFN)
            </button>
            <button
              type="button"
              className={`nav-tab ${tab === 'ap' ? 'active' : ''}`}
              onClick={() => setTab('ap')}
            >
              Pilha (AP)
            </button>
            <button
              type="button"
              className={`nav-tab ${tab === 'mt' ? 'active' : ''}`}
              onClick={() => setTab('mt')}
            >
              Fita (Máquina de Turing)
            </button>
          </nav>
        </div>
      </header>

      <div className="page">
        {erro && (
          <div className="error-msg">
            {erro} — inicie o servidor na raiz do projeto com <code>python api.py</code>.
          </div>
        )}

        {!erro && !exemplos && (
          <div className="section-card empty-msg">Carregando modelos...</div>
        )}

        {exemplos && (
          <>
            {tab === 'af' && <AutomatoFinitoView exemplos={exemplos.af} />}
            {tab === 'ap' && <AutomatoPilhaView exemplos={exemplos.ap} />}
            {tab === 'mt' && <MaquinaTuringView exemplos={exemplos.mt} />}
          </>
        )}
      </div>
    </>
  );
}

export default App;
