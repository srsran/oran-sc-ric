#!/usr/bin/env python3

import time
import datetime
import argparse
import signal
from lib.xAppBase import xAppBase

def parse_nr_cell_id(value):
    """
    Parse NR Cell ID from either hex string or integer.
    
    Args:
        value (str or int): NR Cell ID as hex string (e.g. "0x19B1") or integer
        
    Returns:
        int: NR Cell ID as integer
    """
    if isinstance(value, int):
        return value
    try:
        # Try parsing as hex string
        if value.startswith('0x'):
            return int(value, 16)
        # Try parsing as regular integer
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"NR Cell ID must be an integer or hex string (e.g. '0x19B1'), got '{value}'")

class MyHOXapp(xAppBase):
    def __init__(self, config, http_server_port, rmr_port):
        super(MyHOXapp, self).__init__(config, http_server_port, rmr_port)
        pass

    @xAppBase.start_function
    def start(self, e2_node_id, amf_ue_ngap_id, gnb_cu_ue_f1ap_id, plmn, target_nr_cell_id):
        current_time = datetime.datetime.now()
        print(f"{current_time.strftime('%H:%M:%S')} Sending HO command to E2 node ID: {e2_node_id}, PLMN: {plmn}, AMF UE NGAP ID: {amf_ue_ngap_id}, UE F1AP ID: {gnb_cu_ue_f1ap_id}, Target NR Cell ID: {target_nr_cell_id}")
        self.e2sm_rc.control_handover(
            e2_node_id,
            amf_ue_ngap_id,
            gnb_cu_ue_f1ap_id,
            plmn,
            target_nr_cell_id
        )
        self.running = False
        return

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple RC HO xApp')
    parser.add_argument("--config", type=str, default='', help="xApp config file path")
    parser.add_argument("--http_server_port", type=int, default=8090, help="HTTP server listen port")
    parser.add_argument("--rmr_port", type=int, default=4560, help="RMR port")
    parser.add_argument("--e2_node_id", type=str, default='gnbd_001_001_00019b_0', help="E2 Node ID")
    parser.add_argument("--ran_func_id", type=int, default=3, help="E2SM RC RAN function ID")
    parser.add_argument("--plmn", type=str, default='00101', help="PLMN (e.g., 00101)")
    parser.add_argument("--amf_ue_ngap_id", type=int, default=1, help="AMF UE NGAP ID")
    parser.add_argument("--gnb_cu_ue_f1ap_id", type=int, default=1, help="gNB CU UE F1AP ID")
    parser.add_argument("--target_nr_cell_id", type=parse_nr_cell_id, default=1, help="Target NR Cell ID (integer or hex string, e.g. 6577 or 0x19B1)")

    args = parser.parse_args()
    config = args.config
    e2_node_id = args.e2_node_id
    ran_func_id = args.ran_func_id
    amf_ue_ngap_id = args.amf_ue_ngap_id
    gnb_cu_ue_f1ap_id = args.gnb_cu_ue_f1ap_id
    plmn = args.plmn
    target_nr_cell_id = args.target_nr_cell_id

    myXapp = MyHOXapp(config, args.http_server_port, args.rmr_port)
    myXapp.e2sm_rc.set_ran_func_id(ran_func_id)

    # Connect exit signals.
    signal.signal(signal.SIGQUIT, myXapp.signal_handler)
    signal.signal(signal.SIGTERM, myXapp.signal_handler)
    signal.signal(signal.SIGINT, myXapp.signal_handler)

    # Start xApp.
    myXapp.start(e2_node_id, amf_ue_ngap_id, gnb_cu_ue_f1ap_id, plmn, target_nr_cell_id)
