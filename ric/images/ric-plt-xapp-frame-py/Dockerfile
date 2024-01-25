FROM python:3.8-slim as stretch

RUN apt-get clean -y && apt-get update -y && \
    apt-get install -y git wget curl less nano \
    nmap mtr net-tools tcpdump apt-utils sudo jq tree iproute2 iputils-ping traceroute

# Install RMR
ARG RMR_VERSION=4.9.4
ARG RMR_LIB_URL=https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/rmr_${RMR_VERSION}_amd64.deb/download.deb
ARG RMR_DEV_URL=https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/rmr-dev_${RMR_VERSION}_amd64.deb/download.deb
RUN wget --content-disposition ${RMR_LIB_URL} && dpkg -i rmr_${RMR_VERSION}_amd64.deb
RUN wget --content-disposition ${RMR_DEV_URL} && dpkg -i rmr-dev_${RMR_VERSION}_amd64.deb
RUN rm -f rmr_${RMR_VERSION}_amd64.deb rmr-dev_${RMR_VERSION}_amd64.deb

# Install E2AP
ARG E2AP_VERSION=1.1.0
ARG E2AP_LIB_URL=https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/riclibe2ap_${E2AP_VERSION}_amd64.deb/download.deb
ARG E2AP_DEV_URL=https://packagecloud.io/o-ran-sc/release/packages/debian/stretch/riclibe2ap-dev_${E2AP_VERSION}_amd64.deb/download.deb
RUN wget --content-disposition ${E2AP_LIB_URL} && dpkg -i riclibe2ap_${E2AP_VERSION}_amd64.deb
RUN wget --content-disposition ${E2AP_DEV_URL} && dpkg -i riclibe2ap-dev_${E2AP_VERSION}_amd64.deb
RUN rm -f riclibe2ap_${E2AP_VERSION}_amd64.deb riclibe2ap-dev_${E2AP_VERSION}_amd64.deb

FROM python:3.8-slim

RUN apt-get clean -y && apt-get update -y && \
    apt-get install -y git wget curl less nano

ARG RMR_VERSION=4.9.4
ARG E2AP_VERSION=1.1.0

COPY --from=stretch /usr/local/lib/librmr_si.so.${RMR_VERSION} /usr/local/lib/librmr_si.so
COPY --from=stretch /usr/local/lib/libriclibe2ap.so.${E2AP_VERSION} /usr/local/lib/libriclibe2ap.so
COPY --from=stretch /usr/local/bin/rmr_probe /opt/e2/rmr_probe
RUN chmod -R 755 /usr/local/lib/librmr_si.so
RUN chmod -R 755 /usr/local/lib/libriclibe2ap.so

# Install required Python modules
RUN pip install --upgrade pip && pip install certifi six python_dateutil setuptools urllib3 logger requests inotify_simple mdclogpy google-api-python-client msgpack ricsdl asn1tools

RUN mkdir -p /opt/xApps && chmod -R 755 opt/xApps
RUN mkdir -p /opt/ric/config && chmod -R 755 /opt/ric/config

WORKDIR /opt/

# Clone xApp Python Framework repo
ARG SC_RIC_VERSION=i-release
RUN git clone --depth 1 --branch ${SC_RIC_VERSION} https://github.com/o-ran-sc/ric-plt-xapp-frame-py.git

# Patch xApp Python Framework
WORKDIR /opt/ric-plt-xapp-frame-py
COPY ./ric-plt-xapp-frame-py.patch .
RUN git apply ./ric-plt-xapp-frame-py.patch

WORKDIR /opt/

# Install xApp Python Framework
RUN pip install -e ./ric-plt-xapp-frame-py

ENV LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib
RUN chmod +x /opt/e2/rmr_probe


WORKDIR /opt/xApps

CMD ["/bin/bash"]
