#!/usr/bin/env python3

import argparse
import signal
from lib.xAppBase import xAppBase


class MyXapp(xAppBase):
    def __init__(self, config, http_server_port, rmr_port):
        super(MyXapp, self).__init__(config, http_server_port, rmr_port)

    def my_subscription_callback(self, e2_agent_id, subscription_id, indication_hdr, indication_msg):
        print("\nRIC Indication Received from {} for Subscription ID: {}".format(e2_agent_id, subscription_id))
        indication_hdr = self.e2sm_kpm.extract_hdr_info(indication_hdr)
        meas_data = self.e2sm_kpm.extract_meas_data(indication_msg)

        print("E2SM_KPM RIC Indication Content:")
        print("-ColletStartTime: ", indication_hdr['colletStartTime'])
        print("-Measurements Data:")

        granulPeriod = meas_data.get("granulPeriod", None)
        if granulPeriod is not None:
            print("-granulPeriod: {}".format(granulPeriod))

        for metric_name, value in meas_data["measData"].items():
                print("--Metric: {}, Value: {}".format(metric_name, value))

    # Mark the function as xApp start function using xAppBase.start_function decorator.
    # It is required to start the internal msg receive loop.
    @xAppBase.start_function
    def start(self, e2_node_id, metric_names):
        print("Subscribe to E2 node ID: {}, RAN func: e2sm_kpm for metrics {}".format(e2_node_id, metrics))
        report_period = 1000
        granul_period = 100
        self.e2sm_kpm.subscribe_report_service_style_1(e2_node_id, report_period, metric_names, granul_period, self.my_subscription_callback)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='My example xApp')
    parser.add_argument("--config", type=str, default='', help="xApp config file path")
    parser.add_argument("--http_server_port", type=int, default=8091, help="HTTP server listen port")
    parser.add_argument("--rmr_port", type=int, default=4561, help="RMR port")
    parser.add_argument("--e2_node_id", type=str, default='gnbd_001_001_00019b_0', help="E2 Node ID")
    parser.add_argument("--ran_func_id", type=int, default=2, help="RAN function ID")
    parser.add_argument("--metrics", type=str, default='DRB.UEThpDl', help="Metrics name as comma-separated string")

    args = parser.parse_args()
    config = args.config
    e2_node_id = args.e2_node_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    ran_func_id = args.ran_func_id # TODO: get available E2 nodes from SubMgr, now the id has to be given.
    metrics = args.metrics.split(",")

    # Create MyXapp.
    myXapp = MyXapp(config, args.http_server_port, args.rmr_port)
    myXapp.e2sm_kpm.set_ran_func_id(ran_func_id)

    # Connect exit signals.
    signal.signal(signal.SIGQUIT, myXapp.signal_handler)
    signal.signal(signal.SIGTERM, myXapp.signal_handler)
    signal.signal(signal.SIGINT, myXapp.signal_handler)

    # Start xApp.
    myXapp.start(e2_node_id, metrics)
    # Note: xApp will unsubscribe all active subscriptions at exit.
