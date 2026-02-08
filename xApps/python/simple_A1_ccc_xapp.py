#!/usr/bin/env python3

"""A1-triggered CCC xApp that mirrors simple_ccc_xapp ratios and uses RTS replies."""

import argparse
import json
import signal
import threading
import time

from lib.xAppBase import xAppBase
from ricxappframe.xapp_frame import rmr


# A1 message types
A1_POLICY_REQ = 20010
A1_POLICY_RESP = 20011
A1_POLICY_FAILURE = 20012
A1_POLICY_QUERY = 20020
A1_POLICY_QUERY_RESP = 20021


class A1CccTriggerXapp(xAppBase):
    """Simple CCC xApp that starts/stops control traffic via A1 policy triggers."""

    def __init__(self, config, http_server_port, rmr_port, policy_type_id):
        super(A1CccTriggerXapp, self).__init__(config, http_server_port, rmr_port)
        self.policy_type_id = policy_type_id
        self.policy_instance_id = None
        self.policy_active = threading.Event()

        # Fixed values to mirror simple_ccc_xapp behavior.
        self.min_prb_ratio = 10
        self.max_prb_choices = [25, 50, 75, 100]
        self.dedicated_prb_ratio = 100
        self.control_period = 5
        self.e2_node_id = None

    @xAppBase.start_function
    def start(self, e2_node_id):
        self.e2_node_id = e2_node_id
        print("[INFO] A1 trigger CCC xApp started. Waiting for A1 policy trigger...")
        while self.running:
            if not self.policy_active.wait(timeout=1):
                continue

            while self.running and self.policy_active.is_set():
                min_prb_ratio = 10
                max_prb_ratio = 25
                now = time.strftime("%H:%M:%S")
                print(
                    f"{now} Send RIC Control Request to E2 node ID: {self.e2_node_id} "
                    f"E2SM-CCC:O-RRMPolicyRatio, PRB_min_ratio: {min_prb_ratio}, "
                    f"PRB_max_ratio: {max_prb_ratio}"
                )
                self.e2sm_ccc.control_o_rrm_policy_ratio(
                    self.e2_node_id,
                    min_prb_ratio,
                    max_prb_ratio,
                    dedicated_prb_ratio=100,
                )
                time.sleep(5)
                if not self.policy_active.is_set():
                    break

                min_prb_ratio = 10
                max_prb_ratio = 50
                now = time.strftime("%H:%M:%S")
                print(
                    f"{now} Send RIC Control Request to E2 node ID: {self.e2_node_id} "
                    f"E2SM-CCC:O-RRMPolicyRatio, PRB_min_ratio: {min_prb_ratio}, "
                    f"PRB_max_ratio: {max_prb_ratio}"
                )
                self.e2sm_ccc.control_o_rrm_policy_ratio(
                    self.e2_node_id,
                    min_prb_ratio,
                    max_prb_ratio,
                    dedicated_prb_ratio=100,
                )
                time.sleep(5)
                if not self.policy_active.is_set():
                    break

                min_prb_ratio = 10
                max_prb_ratio = 75
                now = time.strftime("%H:%M:%S")
                print(
                    f"{now} Send RIC Control Request to E2 node ID: {self.e2_node_id} "
                    f"E2SM-CCC:O-RRMPolicyRatio, PRB_min_ratio: {min_prb_ratio}, "
                    f"PRB_max_ratio: {max_prb_ratio}"
                )
                self.e2sm_ccc.control_o_rrm_policy_ratio(
                    self.e2_node_id,
                    min_prb_ratio,
                    max_prb_ratio,
                    dedicated_prb_ratio=100,
                )
                time.sleep(5)
                if not self.policy_active.is_set():
                    break

                min_prb_ratio = 10
                max_prb_ratio = 100
                now = time.strftime("%H:%M:%S")
                print(
                    f"{now} Send RIC Control Request to E2 node ID: {self.e2_node_id} "
                    f"E2SM-CCC:O-RRMPolicyRatio, PRB_min_ratio: {min_prb_ratio}, "
                    f"PRB_max_ratio: {max_prb_ratio}"
                )
                self.e2sm_ccc.control_o_rrm_policy_ratio(
                    self.e2_node_id,
                    min_prb_ratio,
                    max_prb_ratio,
                    dedicated_prb_ratio=100,
                )
                time.sleep(5)

    def _handle_a1_policy_message(self, summary, sbuf):
        payload = rmr.get_payload(sbuf).decode("utf-8", errors="ignore").rstrip("\x00")
        mtype = summary["message type"]
        print(f"[A1] received mtype={mtype} payload={payload}")
        try:
            msg = json.loads(payload)
        except json.JSONDecodeError:
            self._send_policy_failure_rts(sbuf, None, summary, "invalid_json", payload)
            return

        outer = dict(msg)
        inner_payload = msg.get("payload")
        if isinstance(inner_payload, str) and inner_payload.strip():
            try:
                msg = json.loads(inner_payload)
            except json.JSONDecodeError:
                self._send_policy_failure_rts(sbuf, None, summary, "invalid_inner_json", inner_payload)
                return
            for key in ("policy_type_id", "policyTypeId", "policy_instance_id", "policyId", "operation"):
                if key not in msg and key in outer:
                    msg[key] = outer[key]

        policy_type_id = msg.get("policy_type_id") or msg.get("policyTypeId")
        if isinstance(policy_type_id, str):
            try:
                policy_type_id = int(policy_type_id)
            except ValueError:
                pass
        policy_instance_id = msg.get("policy_instance_id") or msg.get("policyId")
        operation = (msg.get("operation") or msg.get("action") or outer.get("operation") or "CREATE").upper()

        if policy_type_id != self.policy_type_id:
            self._send_policy_failure_rts(sbuf, policy_instance_id, summary, "unsupported_type", msg)
            return

        if mtype == A1_POLICY_QUERY:
            self._send_policy_query_response_rts(sbuf, policy_instance_id)
            return

        if policy_instance_id is None:
            self._send_policy_failure_rts(sbuf, policy_instance_id, summary, "missing_policy_id", msg)
            return

        if operation in ("CREATE", "UPDATE"):
            self.policy_instance_id = policy_instance_id
            self.policy_active.set()
            print(f"[A1] Triggering control loop via policy {policy_instance_id}")
            self._send_policy_success_rts(sbuf, policy_instance_id, summary)
        elif operation == "DELETE":
            print(f"[A1] Deleting policy {policy_instance_id} -> stopping xApp")
            self._send_policy_success_rts(sbuf, policy_instance_id, summary)
            self.policy_active.clear()
            self.stop()
        else:
            self._send_policy_failure_rts(sbuf, policy_instance_id, summary, "unsupported_operation", msg)

    # ------------------------------------------------------------------
    # RTS responses
    # ------------------------------------------------------------------
    def _send_policy_success_rts(self, sbuf, policy_instance_id, summary):
        handler_id = summary.get("subscription id")
        if handler_id is None:
            handler_id = "unknown"
        else:
            handler_id = str(handler_id)
        payload = json.dumps(
            {
                "policy_type_id": self.policy_type_id,
                "policy_instance_id": policy_instance_id,
                "handler_id": handler_id,
                "status": "OK",
            }
        ).encode("utf-8")
        rmr.set_payload_and_length(payload, sbuf)
        sbuf.contents.mtype = A1_POLICY_RESP
        rmr.rmr_rts_msg(self.rmr_client, sbuf)

    def _send_policy_failure_rts(self, sbuf, policy_instance_id, summary, reason, details):
        handler_id = summary.get("subscription id")
        if handler_id is None:
            handler_id = "unknown"
        else:
            handler_id = str(handler_id)
        payload = json.dumps(
            {
                "policy_type_id": self.policy_type_id,
                "policy_instance_id": policy_instance_id,
                "handler_id": handler_id,
                "status": "FAIL",
                "reason": reason,
                "details": details,
            },
            default=str,
        ).encode("utf-8")
        rmr.set_payload_and_length(payload, sbuf)
        sbuf.contents.mtype = A1_POLICY_FAILURE
        rmr.rmr_rts_msg(self.rmr_client, sbuf)

    def _send_policy_query_response_rts(self, sbuf, policy_instance_id):
        payload = json.dumps(
            {
                "policy_type_id": self.policy_type_id,
                "policy_instance_id": policy_instance_id or self.policy_instance_id or "latest",
                "policy_instance": {
                    "min_prb_ratio": self.min_prb_ratio,
                    "max_prb_ratio": self.max_prb_choices,
                    "dedicated_prb_ratio": self.dedicated_prb_ratio,
                    "control_period": self.control_period,
                },
            }
        ).encode("utf-8")
        rmr.set_payload_and_length(payload, sbuf)
        sbuf.contents.mtype = A1_POLICY_QUERY_RESP
        rmr.rmr_rts_msg(self.rmr_client, sbuf)

    def _run(self):
        while self.running:
            try:
                sbuf = rmr.rmr_torcv_msg(self.rmr_client, None, 100)
                summary = rmr.message_summary(sbuf)
            except Exception:
                continue

            if summary[rmr.RMR_MS_MSG_STATE] == 0:
                mtype = summary["message type"]
                if mtype == 12050:
                    print("Received RIC_INDICATION (ignored)")
                    rmr.rmr_free_msg(sbuf)
                elif mtype == 12041:
                    print("Received RIC_CONTROL_ACK")
                    rmr.rmr_free_msg(sbuf)
                elif mtype == 12042:
                    print("Received RIC_CONTROL_FAILURE")
                    rmr.rmr_free_msg(sbuf)
                elif mtype in (A1_POLICY_REQ, A1_POLICY_QUERY):
                    # Handler will decide RTS and not free sbuf
                    self._handle_a1_policy_message(summary, sbuf)
                else:
                    print(f"[RMR] unhandled mtype={mtype}")
                    rmr.rmr_free_msg(sbuf)
            else:
                rmr.rmr_free_msg(sbuf)


def main():
    parser = argparse.ArgumentParser(description="A1-triggered CCC xApp (RTS replies)")
    parser.add_argument("--config", type=str, default='', help="xApp config file path")
    parser.add_argument("--http_server_port", type=int, default=8090)
    parser.add_argument("--rmr_port", type=int, default=4560)
    parser.add_argument("--e2_node_id", type=str, default='gnbd_001_001_00019b_0')
    parser.add_argument("--ran_func_id", type=int, default=4)
    parser.add_argument("--policy_type_id", type=int, default=20010)

    args = parser.parse_args()
    xapp = A1CccTriggerXapp(args.config, args.http_server_port, args.rmr_port, args.policy_type_id)
    xapp.e2sm_ccc.set_ran_func_id(args.ran_func_id)

    def _handle_signal(sig, frame):
        xapp.signal_handler(sig, frame)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    xapp.start(args.e2_node_id)


if __name__ == "__main__":
    main()
