FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-lang-italian \
    latexmk \
    python3 \
    python3-pip \
    lmodern \
  && rm -rf /var/lib/apt/lists/*