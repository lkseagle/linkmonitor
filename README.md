#######################################Introduction#############################

This experiment relies on the P4 and tensorflow experimental environment by Linux system. The auther should implement P4 by https://github.com/p4lang/tutorials.
Install tensorflow by https://github.com/tensorflow/tensorflow. Then, copy our project into /home/p4/exercise/ for working. 

#############----Doing the follow steps for simulation---####### 

1. open a terminal: 
 sudo make-> xterm s1-> simple_switch_CLI --thrift-port 9094 ->set_queue_rate  200 (This for congestion queueing simulation).
2. xterm h1->python3 wppolearn.py  xterm h3->python h3receive.py   xterm h4->python h4receive.py (This for INT monitoring).
3. xterm h1 ->iperf -c 10.0.4.4 -i 1 -t 200  xterm h4 ->iperf -s -i 1  (This for congestion simulation).
4. xterm s1 ->tcpdump -i s1-eth1 -w s1-eth1.pcap (This for monitoring the flows).
