#!/bin/bash

# Load default parameters (IP, ports, etc).
source .env

OUTPUT_DIRECTORY=`pwd`/ric/configs
ROUTING_TABLE_FILE=${OUTPUT_DIRECTORY}/routes.rtg

# Create a static routing table for all RIC components.
ROUTING_TABLE_FILE=${OUTPUT_DIRECTORY}/routes.rtg
cat << EOF > $ROUTING_TABLE_FILE
newrt|start
rte|1080|$E2MGR_IP:3801    # RIC_SCTP_CONNECTION_FAILURE
rte|1090|$E2TERM_IP:38000   # RIC_SCTP_CLEAR_ALL
rte|1100|$E2MGR_IP:3801    # E2_TERM_INIT
rte|1101|$E2TERM_IP:38000   # E2_TERM_KEEP_ALIVE_REQ
rte|1102|$E2MGR_IP:3801    # E2_TERM_KEEP_ALIVE_RESP
rte|12001|$E2MGR_IP:3801   # RIC_E2_SETUP_REQ
rte|12002|$E2TERM_IP:38000  # RIC_E2_SETUP_RESP
rte|12003|$E2TERM_IP:38000  # RIC_E2_SETUP_FAILURE
rte|12010|$E2TERM_IP:38000  # RIC_SUB_REQ
rte|12011|$SUBMGR_IP:4560   # RIC_SUB_RESP
rte|12012|$SUBMGR_IP:4560   # RIC_SUB_FAILURE
rte|12020|$E2TERM_IP:38000  # RIC_SUB_DEL_REQ
rte|12021|$SUBMGR_IP:4560   # RIC_SUB_DEL_RESP
rte|12022|$SUBMGR_IP:4560   # RIC_SUB_DEL_FAILURE
rte|12050|$XAPP_PY_RUNNER_IP:4560   # RIC_INDICATION
rte|12040|$E2TERM_IP:38000  # RIC_CONTROL_REQ
rte|12041|$XAPP_PY_RUNNER_IP:4560   # RIC_CONTROL_ACK
rte|12042|$XAPP_PY_RUNNER_IP:4560   # RIC_CONTROL_FAILURE
newrt|end
EOF

# Create E2 Routing Manager (simulator) config file.
E2TERM_CONFFILE=${OUTPUT_DIRECTORY}/rtmgr.yaml
cat <<EOF >$E2TERM_CONFFILE
http:
  port: $RTMGR_SIM_PORT
EOF

# Create E2 Termination point config file.
E2TERM_CONFFILE=${OUTPUT_DIRECTORY}/e2term.conf
cat <<EOF >$E2TERM_CONFFILE
nano=38000
loglevel=info
volume=log
#the key name of the environment holds the local ip address
#ip address of the E2T in the RMR
local-ip=$E2TERM_IP
#trace is start, stop
trace=stop
external-fqdn=e2t.com
#put pointer to the key that point to pod name
pod_name=POD_NAME
sctp-port=$E2TERM_SCTP_PORT
EOF


# Create E2 Manager config file.
E2MGR_CONFFILE=${OUTPUT_DIRECTORY}/e2mgr.yaml
cat <<EOF >$E2MGR_CONFFILE
logging:
  logLevel: debug
http:
  port: 3800
rmr:
  port: 3801
  maxMsgSize: 65536
routingManager:
  baseUrl: http://${RTMGR_SIM_IP}:${RTMGR_SIM_PORT}/ric/v1/handles/
notificationResponseBuffer: 100
bigRedButtonTimeoutSec: 5
maxRnibConnectionAttempts: 3
rnibRetryIntervalMs: 10
keepAliveResponseTimeoutMs: 4500
keepAliveDelayMs: 1500
e2tInstanceDeletionTimeoutMs: 15000
e2ResetTimeOutSec: 10
globalRicId:
  ricId: "AACCE"
  mcc: "001"
  mnc: "01"
rnibWriter:
  stateChangeMessageChannel: RAN_CONNECTION_STATUS_CHANGE
  ranManipulationMessageChannel: RAN_MANIPULATION
EOF

# Create Subscription Manager config file.
SUBMGR_CONFFILE=${OUTPUT_DIRECTORY}/submgr.yaml
cat <<EOF >$SUBMGR_CONFFILE
"local":
  "host": "${SUBMGR_IP}:8080"
"logger":
  "level": 1
"rmr":
  "protPort" : "tcp:4560"
  "maxSize": 8192
  "numWorkers": 1
"rtmgr":
  "hostAddr": "${RTMGR_SIM_IP}"
  "port"    : "${RTMGR_SIM_PORT}"
  "baseUrl" : "/ric/v1"
"db":
  "sessionNamespace": "XMSession"
  "host": "${DBAAS_IP}:${DBAAS_PORT}"
  "prot": "tcp"
  "maxIdle": 80
  "maxActive": 12000
"controls":
  "e2tSubReqTimeout_ms": 2000
  "e2tSubDelReqTime_ms": 2000
  "e2tRecvMsgTimeout_ms": 2000
  "e2tMaxSubReqTryCount": 2
  "e2tMaxSubDelReqTryCount": 2
  "checkE2State": "true"
  "readSubsFromDb": "true"
  "dbTryCount": 200
  "dbRetryForever": "true"
  "checkE2IEOrder": 1
EOF


# Create xApp Manager config file.
APPMGR_CONFFILE=${OUTPUT_DIRECTORY}/appmgr.yaml
cat <<EOF >$APPMGR_CONFFILE
"helm":
  #"host": "192.168.0.12:31807"
  #"repo": "http://192.168.0.6/charts"
  #"repo-name": "helm-repo"
  #"secrets":
  #  "username": "admin"
  #  "password": "ric"
  #"helm-username-file": "./helm_repo_username"
  #"helm-password-file": "./helm_repo_password"
  #"retry": 1
"xapp":
  "namespace": "ricxapp"
  "tarDir": "/tmp"
  "schema": "descriptors/schema.json"
  "config": "config/config-file.json"
  "tmpConfig": "/tmp/config-file.json"
"db":
  "sessionNamespace": "XMSession"
  "host": "${DBAAS_IP}:${DBAAS_PORT}"
  "prot": "tcp"
  "maxIdle": 80
  "maxActive": 12000
EOF