from probe_hdrs import *
import os
import re
import subprocess 
import time
import sched
import re
from time import sleep
import random
import datetime
import numpy as np

result=""

def expand(x):
    yield x
    while x.payload:
        x = x.payload
        yield x

def makedata2(data_layers):
        global result
        result=""
        bedelay=data_layers[0].cur_time
        thput=data_layers[0].pckcont
        result=result+str(thput)+" "
        for i in range(1,len(data_layers)):
            utilization = 0 if data_layers[i].cur_time == data_layers[i].last_time else 8.0*data_layers[i].byte_cnt/(data_layers[i].cur_time - data_layers[i].last_time)
            length=data_layers[i].qdepth
            droppkt=data_layers[i].enpckcont-data_layers[i-1].pckcont     
            delay= bedelay-data_layers[i].cur_time
            bedelay= data_layers[i].cur_time 
            resut="Switch {}: delay:{}us bw:{} Mbps  droppkt:{} q-Length:{} \n".format(data_layers[i].swid, delay, utilization, droppkt, length)  
            result=result+"{} {} {} {} ".format(delay, utilization, droppkt, length)       
            print resut 

def makedata3(data_layers):
        global result
        bedelay=data_layers[1].cur_time
        for i in range(2,len(data_layers)-1):
            utilization = 0 if data_layers[i].cur_time == data_layers[i].last_time else 8.0*data_layers[i].byte_cnt/(data_layers[i].cur_time - data_layers[i].last_time)
            length=data_layers[i].qdepth
            droppkt=data_layers[i].enpckcont-data_layers[i-1].pckcont     
            delay= bedelay-data_layers[i].cur_time
            bedelay= data_layers[i].cur_time 
            resut="Switch {}: delay:{}us bw:{} Mbps  droppkt:{} q-Length:{}\n".format(data_layers[i].swid, delay, utilization, droppkt, length)  
            result=result+"{} {} {} {} ".format(delay, utilization, droppkt, length)      
            print resut
        print result
        f1 = "/home/p4/tutorials/exercises/linkmonitor/message/lsbepath.txt"
        with open(f1,"w") as file:   
              #file.write(str(state)+" "+str(action)+" "+str(reward)+" "+str(r)+'\n')        
              file.write(result)
        result=""

def handle_pkt(pkt):
    if ProbeData in pkt:
        data_layers = [l for l in expand(pkt) if l.name=='ProbeData']
        probelen = [s for s in expand(pkt) if s.name=='Probe']
        if(probelen[0].learn==2):
            makedata2(data_layers)
        else:
            makedata3(data_layers)
             

def main():
    iface = 'eth0'
    print "sniffing on {}".format(iface)
    sniff(iface = iface,
          prn = lambda x: handle_pkt(x))

if __name__ == '__main__':
    main()
