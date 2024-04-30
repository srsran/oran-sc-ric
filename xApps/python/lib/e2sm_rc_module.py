import datetime
from enum import Enum
from .asn1.e2sm_rc_packer import e2sm_rc_packer


class e2sm_rc_module(object):
    def __init__(self, parent):
        super(e2sm_rc_module, self).__init__()
        self.parent = parent
        self.ran_func_id = 3;
        self.e2sm_rc_compiler = e2sm_rc_packer()

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
        control_mgs_len = len(control_msg)
        ric_control_ack_request = ack_request
        # asn1tools has some issue to generate RIC-Control-Request from asn1 files, therefore we need to build it manually
        total_len = 33 + control_header_len + control_mgs_len
        msg = [0x00, 0x04, 0x00, total_len, 0x00, 0x00, 0x05, 0x00, 0x1d, 0x00, 0x05, 0x00, *requestorID, 0x00, 0x00, 0x00, 0x05,
               0x00, 0x02, *ran_func_id, 
               0x00, 0x16, 0x00, control_header_len+1, control_header_len, *control_header, 
               0x00, 0x17, 0x00, control_mgs_len+1, control_mgs_len, *control_msg,
               0x00, 0x15, 0x00, 0x01, ric_control_ack_request  << 6]

        payload = bytes(hex_num for hex_num in msg)
        return payload

    def send_control_request_style_2_action_6(self, e2_node_id, ue_id, min_prb_ratio, max_prb_ratio, dedicated_prb_ratio, ack_request=1):
        PLMN = b'00101' # currently not exposed as parameter
        # S-NSSAI
        sst = b'1'  # currently not exposed as parameter
        sd = b'0'   # currently not exposed as parameter
        # ratios
        min_prb_policy_ratio = max(0, min(min_prb_ratio, 100))
        max_prb_policy_ratio = max(0, min(max_prb_ratio, 100))
        dedicated_prb_policy_ratio = max(0, min(dedicated_prb_ratio, 100))

        ue_id = ('gNB-DU-UEID', {'gNB-CU-UE-F1AP-ID': ue_id})
        control_header = self.e2sm_rc_compiler.pack_ric_control_header_f1(style_type=2, control_action_id=6, ue_id_tuple=ue_id)

        control_msg_dict = {'ric-controlMessage-formats': ('controlMessage-Format1',
                                {'ranP-List': [
                                    {'ranParameter-ID': 1, 'ranParameter-valueType': ('ranP-Choice-List', {'ranParameter-List': {'list-of-ranParameter': [{'sequence-of-ranParameters': [
                                        {'ranParameter-ID': 3, 'ranParameter-valueType': ('ranP-Choice-Structure', {'ranParameter-Structure': {'sequence-of-ranParameters': [
                                            {'ranParameter-ID': 4, 'ranParameter-valueType': ('ranP-Choice-List', {'ranParameter-List': {'list-of-ranParameter': [{'sequence-of-ranParameters': [
                                                {'ranParameter-ID': 6, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueOctS', PLMN)})},
                                                {'ranParameter-ID': 7, 'ranParameter-valueType': ('ranP-Choice-Structure', {'ranParameter-Structure':
                                                    {'sequence-of-ranParameters': [
                                                        {'ranParameter-ID': 8, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueOctS', sst)})},
                                                        {'ranParameter-ID': 9, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueOctS', sd)})}]
                                                    }})}]}]}})}]}})},
                                                    {'ranParameter-ID': 10, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueInt', min_prb_policy_ratio)})},
                                                    {'ranParameter-ID': 11, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueInt', max_prb_policy_ratio)})},
                                                    {'ranParameter-ID': 12, 'ranParameter-valueType': ('ranP-Choice-ElementFalse', {'ranParameter-value': ('valueInt', dedicated_prb_policy_ratio)})}]}]}})}]})}

        control_msg = self.e2sm_rc_compiler.pack_ric_control_msg(control_msg_dict)
        payload = self._build_ric_control_request(control_header, control_msg, ack_request)
        self.parent.rmr_send(e2_node_id, payload, 12040, retries=1)

    # Alias with a nice name
    control_slice_level_prb_quota = send_control_request_style_2_action_6
