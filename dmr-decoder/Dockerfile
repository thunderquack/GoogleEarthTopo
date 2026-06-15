FROM ubuntu:24.04 AS build

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    cmake \
    git \
    libcodec2-dev \
    libfftw3-dev \
    libitpp-dev \
    libncurses-dev \
    libpulse-dev \
    librtlsdr-dev \
    libsamplerate0-dev \
    libsndfile1-dev \
    libssl-dev \
    libusb-1.0-0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch audio_work https://github.com/lwvmobile/dsd-fme.git /src/dsd-fme

WORKDIR /src/dsd-fme

RUN mkdir build \
    && cd build \
    && cmake .. \
    && make -j"$(nproc)" \
    && make install

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    ca-certificates \
    libcodec2-1.2 \
    libfftw3-double3 \
    libitpp8v5 \
    libncurses6 \
    libpulse0 \
    librtlsdr2 \
    libsamplerate0 \
    libsndfile1 \
    libssl3 \
    libusb-1.0-0 \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/ /usr/local/
COPY dmr-decoder/entrypoint.sh /usr/local/bin/dmr-decoder-entrypoint.sh

RUN chmod +x /usr/local/bin/dmr-decoder-entrypoint.sh \
    && mkdir -p /data/dmr

WORKDIR /data

ENTRYPOINT ["/usr/local/bin/dmr-decoder-entrypoint.sh"]
