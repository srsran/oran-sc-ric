#!/usr/bin/env python3

import time
import datetime
import argparse
import signal
from lib.xAppBase import xAppBase


class MyXapp(xAppBase):
    def __init__(self, http_server_port, rmr_port):
        super(MyXapp, self).__init__('', http_server_port, rmr_port)
        self.ue_dl_tx_data = {}
        self.min_prb_ratio = 1
        self.max_prb_ratio1 = 10
        self.max_prb_ratio2 = 100
        self.cur_ue_max_prb_ratio = {}
        self.dl_tx_data_threshold_mb = 20

    def my_subscription_callback(self, e2_agent_id, subscription_id, indication_hdr, indication_msg, kpm_report_style, ue_id):
        indication_hdr = self.e2sm_kpm.extract_hdr_info(indication_hdr)
        meas_data = self.e2sm_kpm.extract_meas_data(indication_msg)

        print("Data Monitoring:")
        print("  E2SM_KPM RIC Indication Content:")
        print("  -ColletStartTime: ", indication_hdr['colletStartTime'])
        print("  -Measurements Data:")

        for ue_id, ue_meas_data in meas_data["ueMeasData"].items():
            print("  --UE_id: {}".format(ue_id))
            granulPeriod = ue_meas_data.get("granulPeriod", None)
            if granulPeriod is not None:
                print("  ---granulPeriod: {}".format(granulPeriod))

            for metric_name, values in ue_meas_data["measData"].items():
                print("  ---Metric: {}, Value: {:.1f} [MB]".format(metric_name, sum(values)/8/1000))

                if (metric_name == "DRB.RlcSduTransmittedVolumeDL"):
                    if ue_id in self.ue_dl_tx_data:
                        # Reported in kbits, convert to MBs.
                        self.ue_dl_tx_data[ue_id] += sum(values)/8/1000
                    else:
                        self.ue_dl_tx_data[ue_id] = sum(values)/8/1000

        print("")
        print("Control Logic:")
        print(" Tx Data Stats:")
        for ue_id, value in self.ue_dl_tx_data.items():
            cur_ue_max_prb_ratio = self.cur_ue_max_prb_ratio.get(ue_id, 0)
            if cur_ue_max_prb_ratio:
                print(f'  UE ID: {ue_id}, Max PRB Ratio: {cur_ue_max_prb_ratio}, Total TXed Data [MB]: {value:.1f}')
            else:
                print(f'  UE ID: {ue_id}, Max PRB Ratio: n/a, TXed Data [MB]: {value:.1f}')

            if (value > self.dl_tx_data_threshold_mb):
                print(f"    {value:.1f} MB of data transmitted to UE --> Switch Max PRB limit")
                cur_ue_max_prb_ratio = self.cur_ue_max_prb_ratio.get(ue_id, self.max_prb_ratio2)
                new_ue_max_prb_ratio = self.max_prb_ratio2 if cur_ue_max_prb_ratio == self.max_prb_ratio1 else self.max_prb_ratio1
                # Reset collected TX data volume.
                self.ue_dl_tx_data[ue_id] = 0
                self.cur_ue_max_prb_ratio[ue_id] = new_ue_max_prb_ratio
                print("    --->Send RIC Control Request to E2 node ID: {} for UE ID: {}, PRB_min: {}, PRB_max: {}".format(e2_agent_id, ue_id, self.min_prb_ratio, new_ue_max_prb_ratio))
                self.e2sm_rc.control_slice_level_prb_quota(e2_agent_id, ue_id, min_prb_ratio=self.min_prb_ratio, max_prb_ratio=new_ue_max_prb_ratio, dedicated_prb_ratio=100, ack_request=1)
        print("------------------------------------------------------------------")
        print("")


    # Mark the function as xApp start function using xAppBase.start_function decorator.
    # It is required to start the internal msg receive loop.
    @xAppBase.start_function
    def start(self, e2_node_id, kpm_report_style, ue_ids, metric_names):
        report_period = 1000
        granul_period = 1000

        subscription_callback = lambda agent, sub, hdr, msg: self.my_subscription_callback(agent, sub, hdr, msg, kpm_report_style, None)

        # Dummy condition that is always satisfied
        matchingUeConds = [{'testCondInfo': {'testType': ('ul-rSRP', 'true'), 'testExpr': 'lessthan', 'testValue': ('valueInt', 1000)}}]
        
        print("Subscribe to E2 node ID: {}, RAN func: e2sm_kpm, Report Style: {}, metrics: {}".format(e2_node_id, kpm_report_style, metric_names))
        self.e2sm_kpm.subscribe_report_service_style_4(e2_node_id, report_period, matchingUeConds, metric_names, granul_period, subscription_callback)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='My example xApp')
    parser.add_argument("--http_server_port", type=int, default=8090, help="HTTP server listen port")
    parser.add_argument("--rmr_port", type=int, default=4560, help="RMR port")
    parser.add_argument("--e2_node_id", type=str, default='gnbd_001_001_00019b_0', help="E2 Node ID")
    parser.add_argument("--ran_func_id", type=int, default=2, help="RAN function ID")
    parser.add_argument("--kpm_report_style", type=int, default=4, help="KPM Report Style ID")
    parser.add_argument("--ue_ids", type=str, default='0', help="UE ID")
    parser.add_argument("--metrics", type=str, default='DRB.RlcSduTransmittedVolumeDL', help="Metrics name as comma-separated string")

    args = parser.parse_args()
    e2_node_id = args.e2_node_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    ran_func_id = args.ran_func_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    ue_ids = list(map(int, args.ue_ids.split(","))) # Note: the UE id has to exist at E2 node!
    kpm_report_style = args.kpm_report_style
    metrics = args.metrics.split(",")

    # Create MyXapp.
    myXapp = MyXapp(args.http_server_port, args.rmr_port)
    myXapp.e2sm_kpm.set_ran_func_id(ran_func_id)

    # Connect exit signals.
    signal.signal(signal.SIGQUIT, myXapp.signal_handler)
    signal.signal(signal.SIGTERM, myXapp.signal_handler)
    signal.signal(signal.SIGINT, myXapp.signal_handler)

    # Start xApp.
    myXapp.start(e2_node_id, kpm_report_style, ue_ids, metrics)
    # Note: xApp will unsubscribe all active subscriptions at exit.
