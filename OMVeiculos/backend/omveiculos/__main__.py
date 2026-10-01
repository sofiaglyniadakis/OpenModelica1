"""Inicia o servidor:  python -m omveiculos [--porta 8000] [--host 127.0.0.1]"""

__author__ = "Sofia Glyniadakis"

import argparse
import os
import webbrowser


def main() -> None:
    ap = argparse.ArgumentParser(prog="omveiculos", description="OM Veículos Leves")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8000)
    ap.add_argument("--omc", help="caminho do executável omc do OpenModelica")
    ap.add_argument("--abrir", action="store_true", help="abre o navegador")
    args = ap.parse_args()
    if args.omc:
        os.environ["OMVEICULOS_OMC"] = args.omc
    import uvicorn

    if args.abrir:
        webbrowser.open(f"http://{args.host}:{args.porta}")
    uvicorn.run("omveiculos.api:app", host=args.host, port=args.porta)


if __name__ == "__main__":
    main()
