"""API HTTP do OM Veículos Leves (FastAPI).

Também serve a interface web compilada (``OMVeiculos/frontend/dist``), de modo
que um único processo atende tudo em http://localhost:8000.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, catalogo, modelica, workflow
from .erros import ErroOMVeiculos

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class No(BaseModel):
    id: str
    tipo: str
    rotulo: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class Aresta(BaseModel):
    origem: str
    destino: str
    entrada: str
    id: str | None = None


class Workflow(BaseModel):
    nos: list[No] = Field(default_factory=list)
    arestas: list[Aresta] = Field(default_factory=list)


class PedidoSimulacao(BaseModel):
    workflow: Workflow
    motor: Literal["rapido", "openmodelica"] = "rapido"


def criar_app() -> FastAPI:
    app = FastAPI(title="OM Veículos Leves", version=__version__)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/status")
    def status():
        return {"versao": __version__, "openmodelica": modelica.status()}

    @app.get("/api/catalogo")
    def obter_catalogo():
        return catalogo.catalogo()

    @app.post("/api/simular")
    def simular(pedido: PedidoSimulacao):
        wf = pedido.workflow.model_dump()
        if pedido.motor == "openmodelica":
            try:
                motor = modelica.MotorOpenModelica()
            except ErroOMVeiculos as e:
                raise HTTPException(status_code=409, detail=str(e)) from None
            return workflow.executar(wf, motor)
        return workflow.executar(wf)

    @app.post("/api/modelica")
    def codigo_modelica(wf: Workflow):
        plano = workflow.planejar(wf.model_dump())
        saida = modelica.gerar_pacote(plano.pedidos_ciclo, plano.pedidos_des)
        saida["erros"] = plano.diag.erros
        return saida

    @app.get("/api/biblioteca")
    def biblioteca():
        return {"arquivos": modelica.arquivos_biblioteca()}

    if FRONTEND.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

        @app.get("/{caminho:path}", include_in_schema=False)
        def interface(caminho: str):
            alvo = (FRONTEND / caminho).resolve()
            if caminho and alvo.is_file() and FRONTEND in alvo.parents:
                return FileResponse(alvo)
            return FileResponse(FRONTEND / "index.html")

    return app


app = criar_app()
