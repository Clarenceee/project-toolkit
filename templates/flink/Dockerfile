ARG FLINK_VERSION
FROM flink:${FLINK_VERSION}

USER root

ARG FLINK_VERSION
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/flink/venv

ENV PATH="/opt/flink/venv/bin:${PATH}"
ENV PYTHONPATH="/opt/flink/usrlib"

COPY requirements.txt /opt/flink/usrlib/requirements.txt
RUN pip install --no-cache-dir "apache-flink==${FLINK_VERSION}" \
    -r /opt/flink/usrlib/requirements.txt

COPY service /opt/flink/usrlib/service
COPY conf/flink-conf.yaml /opt/flink/conf/flink-conf.yaml

RUN chown -R flink:flink /opt/flink/venv /opt/flink/usrlib/service
USER flink
WORKDIR /opt/flink/usrlib
