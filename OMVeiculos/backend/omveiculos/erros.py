"""Exceções do OM Veículos Leves."""

__author__ = "Sofia Glyniadakis"


class ErroOMVeiculos(Exception):
    """Erro com mensagem destinada ao usuário (exibida na interface)."""


class ErroWorkflow(ErroOMVeiculos):
    """Workflow incompleto ou com parâmetros inválidos."""


class ErroOpenModelica(ErroOMVeiculos):
    """Falha ao localizar, compilar ou simular com o OpenModelica."""
