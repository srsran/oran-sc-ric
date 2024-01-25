import datetime
from enum import Enum
from .asn1.e2sm_kpm_packer import e2sm_kpm_packer

class e2sm_types(Enum):
    E2SM_UNKNOWN = 0
    E2SM_KPM = 1
    E2SM_RC = 2

def ntp_ts_to_datetime(ntp_timestamp):
    # Offset between NTP and Unix epochs (1900-1970 in seconds)
    ntp_epoch_offset = 2208988800

    # Subtract the NTP epoch offset to get Unix timestamp
    unix_timestamp = (ntp_timestamp >> 32) - ntp_epoch_offset

    # Convert Unix timestamp to datetime
    return datetime.datetime.utcfromtimestamp(unix_timestamp)

class e2sm_kpm_module(object):
    def __init__(self, parent):
        super(e2sm_kpm_module, self).__init__()
        self.parent = parent
        self.ran_func_id = 2;
        self.e2sm_kpm_compiler = e2sm_kpm_packer()

    def set_ran_func_id(self, ran_func_id):
        self.ran_func_id = ran_func_id

    def subscribe_report_service_style_1(self, e2_node_id, reportingPeriod, metric_names, granulPeriod, indication_callback):
        event_trigger_def = self.e2sm_kpm_compiler.pack_event_trigger_def(reportingPeriod)
        action_def = self.e2sm_kpm_compiler.pack_action_def_format1(metric_names, granulPeriod)
        self.parent.subscribe(e2_node_id, self.ran_func_id, event_trigger_def, action_def, indication_callback, e2sm_types.E2SM_KPM)

    def subscribe_report_service_style_2(self, e2_node_id, reportingPeriod, ue_id, metric_names, granulPeriod, indication_callback):
        event_trigger_def = self.e2sm_kpm_compiler.pack_event_trigger_def(reportingPeriod)
        action_def = self.e2sm_kpm_compiler.pack_action_def_format2(ue_id, metric_names, granulPeriod)
        self.parent.subscribe(e2_node_id, self.ran_func_id, event_trigger_def, action_def, indication_callback, e2sm_types.E2SM_KPM)

    def subscribe_report_service_style_3(self, e2_node_id, reportingPeriod, matchingConds, metric_names, granulPeriod, indication_callback):
        event_trigger_def = self.e2sm_kpm_compiler.pack_event_trigger_def(reportingPeriod)
        action_def = self.e2sm_kpm_compiler.pack_action_def_format3(matchingConds, metric_names, granulPeriod)
        self.parent.subscribe(e2_node_id, self.ran_func_id, event_trigger_def, action_def, indication_callback, e2sm_types.E2SM_KPM)

    def subscribe_report_service_style_4(self, e2_node_id, reportingPeriod, matchingUeConds, metric_names, granulPeriod, indication_callback):
        event_trigger_def = self.e2sm_kpm_compiler.pack_event_trigger_def(reportingPeriod)
        action_def = self.e2sm_kpm_compiler.pack_action_def_format4(matchingUeConds, metric_names, granulPeriod)
        self.parent.subscribe(e2_node_id, self.ran_func_id, event_trigger_def, action_def, indication_callback, e2sm_types.E2SM_KPM)

    def subscribe_report_service_style_5(self, e2_node_id, reportingPeriod, ue_ids, metric_names, granulPeriod, indication_callback):
        event_trigger_def = self.e2sm_kpm_compiler.pack_event_trigger_def(reportingPeriod)
        action_def = self.e2sm_kpm_compiler.pack_action_def_format5(ue_ids, metric_names, granulPeriod)
        self.parent.subscribe(e2_node_id, self.ran_func_id, event_trigger_def, action_def, indication_callback, e2sm_types.E2SM_KPM)

    def unpack_ric_indication(self, ric_indication):
        indication_hdr = self.e2sm_kpm_compiler.unpack_indication_header(ric_indication.indication_header)
        indication_msg = self.e2sm_kpm_compiler.unpack_indication_message(ric_indication.indication_message)
        return indication_hdr, indication_msg

    def extract_hdr_info(self, indication_hdr):
        timestamp = int.from_bytes(indication_hdr['colletStartTime'], "big")
        dt_object = ntp_ts_to_datetime(timestamp)
        indication_hdr['colletStartTime'] = dt_object
        return indication_hdr

    def _extract_meas_data_ind_msg_f1(self, indication_msg_content):
        indication_dict = {}
        metric_names = []
        meas_data_dict = {}
        measData = indication_msg_content["measData"]
        measInfoList = indication_msg_content["measInfoList"]
        granulPeriod = indication_msg_content.get("granulPeriod", None)

        # extract metric names
        # TODO: extract metric labels as well
        for measInfoItem in measInfoList:
            metric_name = measInfoItem["measType"][1]
            metric_names.append(metric_name)
            meas_data_dict[metric_name] = []

        # extract measurements data
        ## map measData to metrics
        for measDataItem in measData:
            measRecord = measDataItem['measRecord']
            idx = 0
            for measRecordItem in measRecord:
                valueType = measRecordItem[0]
                value = measRecordItem[1]
                metric_name = metric_names[idx]
                meas_data_dict[metric_name].append(value)
                idx += 1

        indication_dict["measData"] = meas_data_dict
        # add granulPeriod to dict
        if (granulPeriod is not None):
            indication_dict['granulPeriod'] = granulPeriod

        return indication_dict

    def _extract_content_ind_msg_f1(self, indication_msg):
        '''
        # example content
        {'indicationMessage-formats': ('indicationMessage-Format1', {
            'measData': [{'measRecord': [('integer', 8), ('integer', 8)]}],
            'measInfoList': [{'measType': ('measName', 'DRB.UEThpDl'), 'labelInfoList': [{'measLabel': {'noLabel': 'true'}}]}, 
                             {'measType': ('measName', 'DRB.UEThpUl'), 'labelInfoList': [{'measLabel': {'noLabel': 'true'}}]}],
            'granulPeriod': 1000})}
        '''
        meas_data_dict = self._extract_meas_data_ind_msg_f1(indication_msg["indicationMessage-formats"][1])
        return meas_data_dict

    def _extract_content_ind_msg_f2(self, indication_msg):
        '''
        # example content
        {'indicationMessage-formats': ('indicationMessage-Format2',
            {
            'measData': [{'measRecord': [('integer', 0)]}], 
            'measCondUEidList': [{
                                'measType': ('measName', 'DRB.UEThpDl'), 
                                'matchingCond': [{'matchingCondChoice': ('testCondInfo', {'testType': ('ul-rSRP', 'true'), 'testExpr': 'lessthan', 'testValue': ('valueInt', 1000)})}], 
                                'matchingUEidList': [{'ueID': ('gNB-DU-UEID', {'gNB-CU-UE-F1AP-ID': 0})}]}],
            'granulPeriod': 1000
            }
        )}
        '''
        indication_dict = {}
        metric_names = []
        ue_ids = []
        meas_data_dict = {}
        indication_msg_content = indication_msg["indicationMessage-formats"][1]
        measData = indication_msg_content["measData"]
        measCondUEidList = indication_msg_content["measCondUEidList"]
        granulPeriod = indication_msg_content.get("granulPeriod", None)

        # extract metric names
        # Note: currently only 1 metric in indication msg format 2 is supported
        for measInfoItem in measCondUEidList:
            metric_name = measInfoItem["measType"][1]
            matchingCond = measInfoItem["matchingCond"] # copy of the matchingCond from Subscription Request
            matchingUEidList = measInfoItem.get("matchingUEidList", None) # list of UEs that satisfy the matchingCond
            matchingUEidPerGP = measInfoItem.get("matchingUEidPerGP", None)
            metric_names.append(metric_name)

        if matchingUEidList is None:
            return meas_data_dict

        for matchingUE in matchingUEidList:
            ueID = list(matchingUE["ueID"][1].values())[0]
            ue_ids.append(ueID)
            meas_data_dict[ueID] = {"measData" : {}}
            # for each UE create an entry for each metric_name
            for metric_name in metric_names:
                meas_data_dict[ueID]["measData"] = {metric_name : []}

        # map measData to UE and Metric name
        for measDataItem in measData:
            measRecord = measDataItem['measRecord']
            idx = 0
            for measRecordItem in measRecord:
                ueID = ue_ids[idx]
                metric_name = metric_names[0]  # currently only 1 metric supported in format 2
                valueType = measRecordItem[0]
                value = measRecordItem[1]
                meas_data_dict[ueID]["measData"][metric_name].append(value)
                idx += 1

        indication_dict["ueMeasData"] = meas_data_dict
        indication_dict["matchingCond"] = matchingCond
        # add granulPeriod to dict
        if (granulPeriod is not None):
            indication_dict['granulPeriod'] = granulPeriod

        return indication_dict

    def _extract_content_ind_msg_f3(self, indication_msg):
        '''
        # example content
        {'indicationMessage-formats': ('indicationMessage-Format3', {
            'ueMeasReportList': [{
                   'ueID': ('gNB-DU-UEID', {'gNB-CU-UE-F1AP-ID': 0}), 
                   'measReport': {
                                'measData': [{'measRecord': [('integer', 0), ('integer', 0)]}], 
                                'measInfoList': [{'measType': ('measName', 'DRB.UEThpDl'), 'labelInfoList': [{'measLabel': {'noLabel': 'true'}}]},
                                                 {'measType': ('measName', 'DRB.UEThpUl'), 'labelInfoList': [{'measLabel': {'noLabel': 'true'}}]}],
                                'granulPeriod': 1000
                   }}]
            })
        }
        '''
        indication_dict = {}
        meas_data_dict = {}
        ueMeasReportList = indication_msg["indicationMessage-formats"][1]["ueMeasReportList"]
        for ueMeasReport in ueMeasReportList:
            ueID = list(ueMeasReport["ueID"][1].values())[0]
            measReport = ueMeasReport['measReport']
            meas_data_dict[ueID] = self._extract_meas_data_ind_msg_f1(measReport)

        indication_dict["ueMeasData"] = meas_data_dict
        return indication_dict

    def extract_meas_data(self, indication_msg):
        meas_data = {}
        indication_msg_format = indication_msg["indicationMessage-formats"][0]
        if indication_msg_format == "indicationMessage-Format1":
            meas_data = self._extract_content_ind_msg_f1(indication_msg)
        elif indication_msg_format == "indicationMessage-Format2":
            meas_data = self._extract_content_ind_msg_f2(indication_msg)
        elif indication_msg_format == "indicationMessage-Format3":
            meas_data = self._extract_content_ind_msg_f3(indication_msg)
        return meas_data