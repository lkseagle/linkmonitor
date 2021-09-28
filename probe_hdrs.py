from scapy.all import *

TYPE_PROBE = 0x812

class Probe(Packet):
   fields_desc = [ ByteField("hop_cnt", 0),
                   ByteField("learn", 0)] #0 - INT, 1-learning set

class ProbeData(Packet):
   fields_desc = [ BitField("bos", 0, 1),
                   BitField("swid", 0, 7),
                   ByteField("port", 0),
                   IntField("byte_cnt", 0),
                   IntField("pckcont", 0),
                   IntField("enpckcont", 0),
                   BitField("last_time", 0, 48),
                   BitField("cur_time", 0, 48),
                   BitField("qdepth", 0, 32)  ]

class ProbeFwd(Packet):
   fields_desc = [ ByteField("egress_spec", 0),
                  ByteField("swid", 0),
                  ByteField("percent", 0)]

bind_layers(Ether, Probe, type=TYPE_PROBE)
bind_layers(Probe, ProbeFwd, hop_cnt=0)
bind_layers(Probe, ProbeData)
bind_layers(ProbeData, ProbeData, bos=0)
bind_layers(ProbeData, ProbeFwd, bos=1)
bind_layers(ProbeFwd, ProbeFwd)

