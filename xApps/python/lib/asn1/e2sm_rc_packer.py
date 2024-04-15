import os
import asn1tools

class e2sm_rc_packer(object):
    def __init__(self):
        super(e2sm_rc_packer, self).__init__()
        self.my_dir = os.path.dirname(os.path.abspath(__file__))
        asn1_files = [self.my_dir+'/e2sm-v5.00.asn', self.my_dir+'/e2sm-rc-v5.00.asn']
        self.asn1_compiler = asn1tools.compile_files(asn1_files,'per')

    def pack_ric_control_header_f1(self, style_type, control_action_id, ue_id_tuple):
        control_header = {'ric-controlHeader-formats': ('controlHeader-Format1', {'ueID': ue_id_tuple, 'ric-Style-Type': style_type, 'ric-ControlAction-ID': control_action_id})}
        control_header = self.asn1_compiler.encode('E2SM-RC-ControlHeader', control_header)
        return control_header

    def pack_ric_control_msg(self, control_msg_dict):
        control_header = self.asn1_compiler.encode('E2SM-RC-ControlMessage', control_msg_dict)
        return control_header
