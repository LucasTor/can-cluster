# Dockerfile
FROM ubuntu:22.04

# Install CAN tools and Python packages
RUN apt-get update && \
    apt-get install -y \
    iproute2 \
    can-utils \
    python3 \
    python3-pip \
    python3-can \
    && apt-get clean