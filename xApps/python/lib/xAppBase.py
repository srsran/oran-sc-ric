import sys
import time
import json
import logging
import threading

import ricxappframe
from ricxappframe.xapp_frame import rmr
import ricxappframe.xapp_subscribe as subscribe
import ricxappframe.xapp_rest as ricrest
from ricxappframe.e2ap.asn1 import IndicationMsg
from .e2sm_kpm_module import e2sm_types, e2sm_kpm_module
from .e2sm_rc_module import e2sm_rc_module


class SubscriptionWrapper(object):
    def __init__(self):
        super(SubscriptionWrapper, self).__init__()
        self.e2sm_type = e2sm_types.E2SM_UNKNOWN
        self.subscription_id = None
        self.e2_event_instance_id = None  # Subscription ID used in RIC indication msgs
        self.callback_func = None

class xAppBase(object):
    def __init__(self, config=None, http_server_port=8090, rmr_port=4560, rmr_flags=0x00):
        super(xAppBase, self).__init__()
        # Default Config
        self.xAPP_IP = "10.0.2.20"
        self.MY_HTTP_SERVER_ADDRESS = "0.0.0.0"     # bind to all interfaces
        self.MY_HTTP_SERVER_PORT = http_server_port # web server listen port
        self.MY_RMR_PORT = rmr_port
        self.SUB_MGR_URI = "http://10.0.2.13:8088/ric/v1"
        self.xapp_thread = None

        if config is not None:
            # TODO: read config
            pass

        self.e2sm_kpm = e2sm_kpm_module(self)
        self.e2sm_rc = e2sm_rc_module(self)
        # dict to store active subscriptions
        self.my_subscriptions = {}

        # helper variables
        self.running = False
        
        # Initialize RMR client.
        initbind = str(self.MY_RMR_PORT).encode('utf-8')
        self.rmr_client = rmr.rmr_init(initbind, rmr.RMR_MAX_RCV_BYTES, rmr_flags) # flag: do not start an additional route collector thread
        while rmr.rmr_ready(self.rmr_client) == 0:
            time.sleep(1)

        rmr.rmr_set_stimeout(self.rmr_client, 1)
        self.rmr_sbuf = rmr.rmr_alloc_msg(self.rmr_client, 2000)
        time.sleep(0.1)

        # Initialize Subscriber to talk to Subscription Manager over REST API
        self.subscriber = subscribe.NewSubscriber(self.SUB_MGR_URI)

        # Initialize subEndPoint with my IP and ports
        self.subEndPoint = self.subscriber.SubscriptionParamsClientEndpoint(self.xAPP_IP, self.MY_HTTP_SERVER_PORT, self.MY_RMR_PORT)

        # Create a HTTP server and set the URI handler callbacks
        self.httpServer = ricrest.ThreadedHTTPServer(self.MY_HTTP_SERVER_ADDRESS, self.MY_HTTP_SERVER_PORT)
        if self.subscriber.ResponseHandler(self._subscription_response_callback, self.httpServer) is not True:
            print("Error when trying to set the subscription reponse callback")
        self.httpServer.start()

    @classmethod
    def start_function(cls, fun):
        def wrapper(self, *args, **kwargs):
            self.running = True
            self.xapp_thread = threading.Thread(target=fun, args=(self, *args), kwargs=kwargs)
            self.xapp_thread.start()
            self._run()
        return wrapper

    def _create_http_response(self,status=200, response="OK"):
        return {'response': response, 'status': status, 'payload': None, 'ctype': 'application/json', 'attachment': None, 'mode': 'plain'}

    def _subscription_response_callback(self, name, path, data, ctype):
        data = json.loads(data)
        SubscriptionId = data['SubscriptionId']
        E2EventInstanceId = data['SubscriptionInstances'][0]["E2EventInstanceId"]  # subscription ID used in RIC indication
        print("Received Subscription ID to E2EventInstanceId mapping: {} -> {}".format(SubscriptionId, E2EventInstanceId))
        if SubscriptionId in self.my_subscriptions:
            self.my_subscriptions[SubscriptionId].e2_event_instance_id = E2EventInstanceId
            # update the key, as it is more convenient to use E2EventInstanceId that is used in RIC indication msgs
            self.my_subscriptions[E2EventInstanceId]= self.my_subscriptions.pop(SubscriptionId)

        response = self._create_http_response()
        response['payload'] = ("{}")
        return response

    def subscribe(self, e2_node_id, ran_function_id, event_trigger_def, action_def, indication_callback, e2sm_type=e2sm_types.E2SM_UNKNOWN):
        action_id = 1 # Now only 1 action in a Subscription Request
        # Need to transform byte data for the REST request
        action_def = [action_def[i] for i in range (0, len(action_def))]
        actionDefinitionList = self.subscriber.ActionToBeSetup(action_id, "report", action_def)

        # Need to transform byte data for the REST request
        event_trigger_def = [event_trigger_def[i] for i in range (0, len(event_trigger_def))]

        xapp_event_instance_id = 1234 # TODO: what is this?
        subsDetail = self.subscriber.SubscriptionDetail(xapp_event_instance_id, event_trigger_def, [actionDefinitionList])

        # Create and send RIC Subscription Request
        subReq = self.subscriber.SubscriptionParams(None, self.subEndPoint, e2_node_id, ran_function_id, None, [subsDetail])
        data, reason, status  = self.subscriber.Subscribe(subReq)

        # Decode RIC Subscription Response
        subResponse = json.loads(data)
        subscription_id = subResponse['SubscriptionId']
        print("Successfully subscribed with Subscription ID: ", subscription_id)

        subscriptionObj = SubscriptionWrapper()
        subscriptionObj.e2sm_type = e2sm_type
        subscriptionObj.subscription_id = subscription_id
        subscriptionObj.callback_func = indication_callback
        # Store active subscription in the dict
        self.my_subscriptions[subscription_id] = subscriptionObj

    def unsubscribe(self, subscription_id):
        print("Unsubscribe Subscription ID: ", subscription_id)
        data, reason, status  = self.subscriber.UnSubscribe(subscription_id)
        if (status == 204):
            print("Successfully unsubscribed from Subscription ID: ", subscription_id)
        else:
            print("Error during unsubscribing from Subscription ID: ", subscription_id)

    def unsubscribe_all(self):
        for e2_event_instance_id, subscriptionObj in self.my_subscriptions.items():
            self.unsubscribe(subscriptionObj.subscription_id)

    def rmr_send(self, e2_node_id, payload, mtype, retries=1):
        sbuf = rmr.rmr_alloc_msg(self.rmr_client, len(payload), mtype=mtype)
        rmr.set_payload_and_length(payload, sbuf)
        rmr.generate_and_set_transaction_id(sbuf)
        sbuf.contents.state = 0
        sbuf.contents.mtype = mtype
        sbuf.contents.sub_id = -1
        rmr.rmr_set_meid(sbuf, e2_node_id.encode("utf8"))
        #print("Pre send summary: {}".format(rmr.message_summary(sbuf)))
        sbuf = rmr.rmr_send_msg(self.rmr_client, sbuf)

    def _run(self):
        while self.running:
            try:
                sbuf = rmr.rmr_torcv_msg(self.rmr_client, None, 100)
                summary = rmr.message_summary(sbuf)
            except Exception as e:
                continue

            if summary[rmr.RMR_MS_MSG_STATE] == 0: # RMR_OK
                # Check if RIC INDICATION message
                if (summary['message type'] == 12050):
                    e2_agent_id = str(summary['meid'].decode('utf-8'))
                    data = rmr.get_payload(sbuf)
                    try:
                        E2EventInstanceId = summary['subscription id']
                        ric_indication = IndicationMsg()
                        ric_indication.decode(data)
                        subscriptionObj = self.my_subscriptions.get(E2EventInstanceId, None)
                        if subscriptionObj is None:
                            rmr.rmr_free_msg(sbuf)
                            continue

                        callback_func =  subscriptionObj.callback_func
                        subscription_id = E2EventInstanceId
                        if callback_func is not None:
                            if (subscriptionObj.e2sm_type == e2sm_types.E2SM_KPM):
                                # if RIC Indication from E2SM_KPM then decode
                                indication_hdr, indication_msg = self.e2sm_kpm.unpack_ric_indication(ric_indication)
                                callback_func(e2_agent_id, subscription_id, indication_hdr, indication_msg)
                            else:
                                # in other cases just pass undecoded byte data
                                callback_func(e2_agent_id, subscription_id, ric_indication.indication_header, ric_indication.indication_message)
                    except Exception as e:
                        print("Error during RIC indication decoding: {}".format(e))
                        pass
                if (summary['message type'] == 12041):
                    print("Received RIC_CONTROL_ACK")
                if (summary['message type'] == 12042):
                    print("Received RIC_CONTROL_FAILURE")

            rmr.rmr_free_msg(sbuf)

    def stop(self):
        self.unsubscribe_all()
        self.httpServer.stop()
        rmr.rmr_close(self.rmr_client)
        self.running = False
        if (self.xapp_thread is not None):
            self.xapp_thread.join()
        sys.exit(0)

    def signal_handler(self, sig, frame):
        self.stop()
