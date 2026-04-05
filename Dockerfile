# autocircuit: Docker environment with ngspice + SkyWater SKY130 PDK
#
# Build:  docker build -t autocircuit .
# Run:    docker run --rm -v $(pwd):/work autocircuit
#
# Multi-stage build to minimize final image size.

# ============================================================
# Stage 1: Build open_pdks (SKY130 ngspice models only)
# ============================================================
FROM ubuntu:22.04 AS pdk-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    python3 \
    m4 \
    make \
    gcc \
    tcsh \
    && rm -rf /var/lib/apt/lists/*

# Clone and build open_pdks — minimal install (ngspice models only, no standard cells)
RUN cd /tmp && \
    git clone --depth=1 https://github.com/RTimothyEdwards/open_pdks.git && \
    cd open_pdks && \
    ./configure --prefix=/opt/pdk \
        --enable-sky130-pdk \
        --disable-sc-hs-sky130 \
        --disable-sc-ms-sky130 \
        --disable-sc-ls-sky130 \
        --disable-sc-lp-sky130 \
        --disable-sc-hd-sky130 \
        --disable-sc-hdll-sky130 \
        --disable-sc-hvl-sky130 \
        --disable-magic \
        --disable-netgen \
        --disable-irsim \
        --disable-klayout \
        --disable-qflow && \
    make -j$(nproc) && \
    make install && \
    cd /tmp && rm -rf open_pdks

# ============================================================
# Stage 2: Final runtime image
# ============================================================
FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install ngspice
RUN apt-get update && apt-get install -y \
    ngspice \
    && rm -rf /var/lib/apt/lists/*

# Copy PDK from builder stage
COPY --from=pdk-builder /opt/pdk /opt/pdk

# Set PDK environment variables
ENV PDK_ROOT=/opt/pdk/share/pdk
ENV PDK=sky130A

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /work

# Default: run optimize.py
ENTRYPOINT ["uv", "run", "python", "optimize.py"]
