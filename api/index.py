"""
Função serverless da Vercel que expõe a API do simulador.

Na Vercel não existe um processo `python api.py` rodando o tempo todo: cada
requisição a `/api/...` é redirecionada (ver `vercel.json`) para esta função,
que reaproveita o mesmo `SimuladorHandler` do `api.py` da raiz. Assim a lógica
continua em um único lugar e o console, a API local e a Vercel dão a mesma
resposta.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Carregamos o arquivo api.py da raiz pelo caminho, com outro nome de módulo.
_spec = importlib.util.spec_from_file_location("simulador_api", RAIZ / "api.py")
_api = importlib.util.module_from_spec(_spec)
sys.modules["simulador_api"] = _api
_spec.loader.exec_module(_api)


class handler(_api.SimuladorHandler):
    """Restaura a rota original (/api/<rota>) antes de despachar."""

    def _restaurar_rota(self) -> None:
        url = urlparse(self.path)
        if not url.path.rstrip("/").endswith("/api/index"):
            return  # a Vercel já entregou o caminho original
        params = parse_qs(url.query)
        rota = params.pop("rota", [""])[0]
        query = urlencode(params, doseq=True)
        self.path = f"/api/{rota}" + (f"?{query}" if query else "")

    def do_GET(self) -> None: 
        self._restaurar_rota()
        super().do_GET()

    def do_POST(self) -> None: 
        self._restaurar_rota()
        super().do_POST()
