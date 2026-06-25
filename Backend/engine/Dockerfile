# Image du moteur DMN Mojo.
#
# Résout l'incompatibilité binaire constatée sur les postes Windows : un
# `evaluator` compilé via WSL est un ELF Linux, inexécutable depuis un
# interpréteur Python Windows natif (WinError 193). Voir le commentaire
# correspondant dans Backend/bridge/engine_bridge.py.
#
# Build : docker build -t dmn-mojo-engine Backend/engine
#         (ou : docker compose build mojo-engine, depuis la racine du repo)
# Run   : docker run --rm -i dmn-mojo-engine
#         Le binaire lit le protocole texte sur stdin et répond sur stdout
#         (format documenté dans Backend/engine/main.mojo).

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates clang \
    && rm -rf /var/lib/apt/lists/*

# Pixi est l'outil d'installation recommandé par Modular pour Mojo
# (https://docs.modular.com/pixi/).
RUN curl -fsSL https://pixi.sh/install.sh | sh
ENV PATH="/root/.pixi/bin:${PATH}"

# Version épinglée sur celle utilisée en local par l'équipe (WSL : `mojo --version`).
# Mojo >= 1.0 a supprimé le mot-clé `fn` (remplacé par `def`) : prendre la
# dernière version casserait la compilation du code existant.
ARG MOJO_VERSION=0.26.2.0

WORKDIR /app
RUN pixi init . -c https://conda.modular.com/max/ -c conda-forge && pixi add mojo==${MOJO_VERSION}

COPY evaluator.mojo hit_first.mojo hit_collect_sum.mojo main.mojo ./
RUN pixi run mojo build main.mojo -o evaluator

ENTRYPOINT ["pixi", "run", "./evaluator"]
