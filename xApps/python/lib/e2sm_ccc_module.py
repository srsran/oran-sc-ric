import json
import datetime
from enum import Enum
from .utils import plmn_string_to_bcd, plmn_to_bytes
from .asn1.nr_cgi_packer import nr_cgi_packer


def encode_length(length: int):
    """Encode length using 1 byte if possible, else 2 bytes (big-endian)"""
    if length < 256:
        return [length]
    else:
        b = list(length.to_bytes(2, byteorder='big'))
        b[0] = (b[0] & 0b00111111) | 0b10000000  # force top 2 bits to 10
        return b

class e2sm_ccc_module(object):
    def __init__(self, parent):
        super(e2sm_ccc_module, self).__init__()
        self.parent = parent
        self.ran_func_id = 4

        # helper variables
        self.requestorID = 0

    def set_ran_func_id(self, ran_func_id):
        self.ran_func_id = ran_func_id

    def get_requestor_id(self):
        self.requestorID += 1
        self.requestorID %= 255
        return self.requestorID

    def _build_ric_control_request(self, control_header, control_msg, ack_request):
        requestorID = [0x00, self.get_requestor_id()]
        ran_func_id = [0x00, self.ran_func_id]
        control_header_len = len(control_header)
        control_msg_len = len(control_msg)
        ric_control_ack_request = ack_request
        # asn1tools has some issue to generate RIC-Control-Request from asn1 files, therefore we need to build it manually
        total_len = 32 + control_header_len + control_msg_len + 1 + 2
        msg = [0x00, 0x04, 0x00, *encode_length(total_len), 0x00, 0x00, 0x05, 0x00, 0x1d,
               0x00, 0x05, 0x00, *requestorID, 0x00, 0x00,
               0x00, 0x05, 0x00, 0x02, *ran_func_id,
               0x00, 0x16, 0x00, *encode_length(control_header_len+1),*encode_length(control_header_len), *control_header,
               0x00, 0x17, 0x00, *encode_length(control_msg_len+2), *encode_length(control_msg_len), *control_msg,
               0x00, 0x15, 0x00, 0x01, ric_control_ack_request << 6]

        payload = bytes(hex_num for hex_num in msg)
        return payload

    def send_control_request_style_2_o_rrm_policy_ratio(self, e2_node_id, min_prb_ratio, max_prb_ratio, dedicated_prb_ratio, ack_request=1):
        mcc = "001"
        mnc = "01"
        nr_cgi = "00066C000"
        sst = 1
        sd = "000000"

        # PRB ratio limits, i.e., [0-100]
        min_prb_ratio = max(0, min(min_prb_ratio, 100))
        max_prb_ratio = max(0, min(max_prb_ratio, 100))
        dedicated_prb_ratio = max(0, min(dedicated_prb_ratio, 100))

        if (max_prb_ratio < min_prb_ratio):
            print("ERROR: E2SM-CCC Control Request - Slice Level PRB Quota: max_prb_ratio ({}) cannot be smaller than min_prb_ratio ({})".format(max_prb_ratio, min_prb_ratio))
            return


        control_header_json = {
              "controlHeaderFormat": {
                "ricStyleType": 2
              }
            }

        control_msg_json = {
              "controlMessageFormat": {
                "listOfCellsControlled": [
                  {
                    "cellGlobalId": {
                      "plmnIdentity": {
                        "mcc": mcc,
                        "mnc": mnc
                      },
                      "nRCellIdentity": nr_cgi
                    },
                    "listOfConfigurationStructures": [
                      {
                        "ranConfigurationStructureName": "O-RRMPolicyRatio",
                        "oldValuesOfAttributes": {
                          "ranConfigurationStructure": {
                            "resourceType": "PRB",
                            "rRMPolicyMemberList": [
                              {
                                "plmnId": {
                                  "mcc": mcc,
                                  "mnc": mnc
                                },
                                "snssai": {
                                  "sst": sst,
                                  #"sd": sd
                                }
                              }
                            ],
                            "rRMPolicyMaxRatio": max_prb_ratio,
                            "rRMPolicyMinRatio": min_prb_ratio,
                            "rRMPolicyDedicatedRatio": dedicated_prb_ratio
                          }
                        },
                        "newValuesOfAttributes": {
                          "ranConfigurationStructure": {
                            "resourceType": "PRB_DL",
                            "rRMPolicyMemberList": [
                              {
                                "plmnId": {
                                  "mcc": mcc,
                                  "mnc": mnc
                                },
                                "snssai": {
                                  "sst": sst,
                                  #"sd": sd
                                }
                              }
                            ],
                            "rRMPolicyMaxRatio": max_prb_ratio,
                            "rRMPolicyMinRatio": min_prb_ratio,
                            "rRMPolicyDedicatedRatio": dedicated_prb_ratio
                          }
                        }
                      }
                    ]
                  }
                ]
              }
            }

        ccc_control_hdr = json.dumps(control_header_json).encode('utf-8')
        ccc_control_msg = json.dumps(control_msg_json).encode('utf-8')
        e2_ctrl_msg = self._build_ric_control_request(ccc_control_hdr, ccc_control_msg, ack_request)
        self.parent.rmr_send(e2_node_id, e2_ctrl_msg, 12040, retries=1)

    # Alias with a nice name
    control_o_rrm_policy_ratio = send_control_request_style_2_o_rrm_policy_ratio
