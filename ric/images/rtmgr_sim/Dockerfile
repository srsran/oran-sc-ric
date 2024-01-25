FROM nexus3.o-ran-sc.org:10002/o-ran-sc/bldr-ubuntu20-c-go:1.1.1 as ubuntu

WORKDIR /opt/rmsimulator
ENV PATH=$PATH:/usr/local/go/bin:/usr/lib/go-1.12/bin

ARG SC_RIC_VERSION=i-release

# Clone e2mgr that contains rtmgr_sim
RUN git clone --depth 1 --branch ${SC_RIC_VERSION} https://github.com/o-ran-sc/ric-plt-e2mgr.git e2mgr

# Copy only Routing Manager Simulator
RUN cp -r ./e2mgr/tools/RoutingManagerSimulator/* ./

RUN go build main.go

FROM ubuntu:16.04
COPY --from=ubuntu /opt/rmsimulator/main /opt/rmsimulator/main
COPY --from=ubuntu /opt/rmsimulator/resources /opt/rmsimulator/resources

WORKDIR /opt/rmsimulator
CMD exec ./main
