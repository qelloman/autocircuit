# autocircuit: Docker environment with ngspice + SkyWater SKY130 PDK
#
# Build:  docker build -t autocircuit .
# Run:    docker run --rm -v $(pwd):/work autocircuit
#
# Uses volare to download pre-built SKY130 PDK (~2 min, no source compilation).

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install ngspice
RUN apt-get update && apt-get install -y \
    ngspice \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install volare and download pre-built SKY130 PDK
# Version hash from: volare ls-remote --pdk sky130
RUN pip install --no-cache-dir volare && \
    volare enable --pdk-root=/opt/pdk --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b

# Set PDK environment variables
ENV PDK_ROOT=/opt/pdk
ENV PDK=sky130A

WORKDIR /work

ENTRYPOINT ["uv", "run", "python", "optimize.py"]
