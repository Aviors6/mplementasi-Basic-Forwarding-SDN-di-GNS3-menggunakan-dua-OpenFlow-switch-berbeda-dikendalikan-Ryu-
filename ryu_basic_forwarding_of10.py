#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SDN Basic Forwarding — OpenFlow 1.0
Ryu Controller untuk OVS (DPID=1) dan MikroTik CHR (DPID=2)

Cara menjalankan:
  ryu-manager --ofp-tcp-listen-port 6633 ryu_basic_forwarding_of10.py

Sesuaikan MAC address di bawah dengan environment GNS3 Anda:
  H1: ip addr show eth0 | grep ether
  H2: ip addr show eth0 | grep ether
"""

import struct
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

# ============================================================
# SESUAIKAN DENGAN MAC ADDRESS DI ENVIRONMENT GNS3 ANDA
H1_MAC = '02:42:99:39:3a:00'   # AlpineLinux-1 eth0
H2_MAC = '02:42:36:01:7b:00'   # AlpineLinux-2 eth0
# ============================================================


def mac_to_bin(mac_str):
    return struct.pack('!6B', *[int(x, 16) for x in mac_str.split(':')])


class BasicForwardingOF10(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    FLOW_PRIORITY = 100

    def __init__(self, *args, **kwargs):
        super(BasicForwardingOF10, self).__init__(*args, **kwargs)
        self.known_switches = set()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        dpid = datapath.id
        self.logger.info("=" * 60)
        self.logger.info("Switch terhubung -> DPID=%s", dpid)
        for port_no, port in ev.msg.ports.items():
            self.logger.info("  PORT_NO=%s  NAME=%s  MAC=%s",
                             port_no, port.name, port.hw_addr)

        if dpid == 1:
            # OVS: forward biasa tanpa rewrite MAC
            self._add_flow_output(datapath, 1, 2)
            self._add_flow_output(datapath, 2, 1)
        elif dpid == 2:
            # MikroTik: rewrite dst MAC agar NIC mau terima frame unicast
            # (MikroTik CHR 6.49 tidak aktifkan promisc di OpenFlow port)
            self._add_flow_rewrite(datapath, 1, H2_MAC, 2)
            self._add_flow_rewrite(datapath, 2, H1_MAC, 1)
        else:
            self.logger.warning("DPID=%s tidak dikenal, flow tidak diinstall.", dpid)
            return

        self.known_switches.add(dpid)

    def _add_flow_output(self, datapath, in_port, out_port):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        match = parser.OFPMatch(in_port=in_port)
        actions = [parser.OFPActionOutput(out_port)]
        self._send_flow_mod(datapath, match, actions)
        self.logger.info("  FLOW DPID=%s: in_port=%s -> output:%s",
                         datapath.id, in_port, out_port)

    def _add_flow_rewrite(self, datapath, in_port, dst_mac, out_port):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        match = parser.OFPMatch(in_port=in_port)
        actions = [
            parser.OFPActionSetDlDst(mac_to_bin(dst_mac)),
            parser.OFPActionOutput(out_port),
        ]
        self._send_flow_mod(datapath, match, actions)
        self.logger.info("  FLOW DPID=%s: in_port=%s -> SET_DL_DST=%s output:%s",
                         datapath.id, in_port, dst_mac, out_port)

    def _send_flow_mod(self, datapath, match, actions):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        mod = parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD,
            idle_timeout=0, hard_timeout=0,
            priority=self.FLOW_PRIORITY, actions=actions)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPErrorMsg,
                [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def error_msg_handler(self, ev):
        msg = ev.msg
        self.logger.warning(
            "OFPErrorMsg DPID=%s: type=0x%02x code=0x%02x (diabaikan)",
            msg.datapath.id, msg.type, msg.code)

    @set_ev_cls(ofp_event.EventOFPStateChange, DEAD_DISPATCHER)
    def switch_disconnect_handler(self, ev):
        datapath = ev.datapath
        if datapath is None:
            return
        if datapath.id in self.known_switches:
            self.logger.warning("Switch DPID=%s terputus.", datapath.id)
            self.known_switches.discard(datapath.id)
