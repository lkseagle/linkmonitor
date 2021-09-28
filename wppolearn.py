# -*- coding: utf-8 -*-
#############################################################

####################################################################################
# -*- coding: utf-8 -*-
#############################################################

####################################################################################
import sys
import time

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
import tensorflow as tf
from tensorflow.python.training import checkpoint_management
#import pyinotify

from numpy import array as matrix, arange
from send import sender
from numpy import array as matrix, arange
from probe_hdrs import *

np.random.seed(1)
tf.set_random_seed(1)

schedule = sched.scheduler(time.time,time.sleep)

EP_MAX = 100
EP_LEN = 200
N_WORKER = 4                # parallel workers
GAMMA = 0.9                 # reward discount factor
A_LR = 0.0001               # learning rate for actor
C_LR = 0.0002               # learning rate for critic
MIN_BATCH_SIZE = 64         # minimum batch size for updating PPO
UPDATE_STEP = 100            # loop update operation n-steps
EPSILON = 0.2               # for clipping surrogate objective
GAME = 'Pendulum-v0'
S_DIM, A_DIM = 44, 4         # state and action dimension

class PPO(object):
    def __init__(self):
        
        self.tfs = tf.compat.v1.placeholder(tf.float32, [None, S_DIM], name='state')
        self.tfdc_r = tf.compat.v1.placeholder(tf.float32, [None, 1], name='discounted_r')
        # ##########################critic
        with tf.compat.v1.variable_scope('advatege_l1',reuse=tf.AUTO_REUSE):
            l1 = tf.layers.dense(self.tfs, 100, tf.nn.relu)
        with tf.compat.v1.variable_scope('advatege_v',reuse=tf.AUTO_REUSE):
            self.v = tf.layers.dense(l1, 1)
            self.advantage = self.tfdc_r - self.v
        with tf.compat.v1.variable_scope('closs',reuse=tf.AUTO_REUSE):
            self.closs = tf.reduce_mean(tf.square(self.advantage))
        with tf.compat.v1.variable_scope('ctrain_op',reuse=tf.AUTO_REUSE):
            self.ctrain_op = tf.train.AdamOptimizer(C_LR).minimize(self.closs)

        # ############################actor
        pi, pi_params = self._build_anet('pi', trainable=True)
        oldpi, oldpi_params = self._build_anet('oldpi', trainable=False)
        self.sample_op = tf.squeeze(pi.sample(1), axis=0)  # operation of choosing action
        self.update_oldpi_op = [oldp.assign(p) for p, oldp in zip(pi_params, oldpi_params)]

        self.tfa = tf.compat.v1.placeholder(tf.float32, [None, A_DIM], name='action')
        self.tfadv = tf.compat.v1.placeholder(tf.float32, [None, 1], name='advantage')
        # ratio = tf.exp(pi.log_prob(self.tfa) - oldpi.log_prob(self.tfa))
        ratio = pi.prob(self.tfa) / (oldpi.prob(self.tfa) + 1e-5)
        surr = ratio * self.tfadv                       # surrogate loss
        with tf.compat.v1.variable_scope('aloss',reuse=tf.AUTO_REUSE):
            self.aloss = -tf.reduce_mean(tf.minimum(        # clipped surrogate objective
                surr,
                tf.clip_by_value(ratio, 1. - EPSILON, 1. + EPSILON) * self.tfadv))
        with tf.compat.v1.variable_scope('atrain_op',reuse=tf.AUTO_REUSE):
            self.atrain_op = tf.train.AdamOptimizer(A_LR).minimize(self.aloss)
        
        self.sess = tf.compat.v1.Session()
        self.sess.run(tf.compat.v1.global_variables_initializer())
        self.saver = tf.compat.v1.train.Saver(tf.compat.v1.global_variables())
        
        #self.sess = tf.Session()
        #self.sess.run(tf.global_variables_initializer())
        #self.saver = tf.train.Saver(tf.global_variables())

    def update(self,data):
        #UPDATE_EVENT.wait()
        #global GLOBAL_UPDATE_COUNTER#  wait until get batch of data
        self.sess.run(self.update_oldpi_op)     # copy pi to old pi
        #data = [QUEUE.get() for _ in range(QUEUE.qsize())]      # collect data from all workers
        #data=QUEUE.get()
        data = np.vstack(data)
        s, a, r = data[:, :S_DIM], data[:, S_DIM: S_DIM + A_DIM], data[:, -1:]
        adv = self.sess.run(self.advantage, {self.tfs: s, self.tfdc_r: r})
        # update actor and critic in a update loop
        [self.sess.run(self.atrain_op, {self.tfs: s, self.tfa: a, self.tfadv: adv}) for _ in range(UPDATE_STEP)]
        [self.sess.run(self.ctrain_op, {self.tfs: s, self.tfdc_r: r}) for _ in range(UPDATE_STEP)]
        #UPDATE_EVENT.clear()        # updating finished
        #GLOBAL_UPDATE_COUNTER = 0   # reset counter
        #ROLLING_EVENT.set()         # set roll-out available

    def learnandupdate(self,restate2,buffer_s,buffer_a,buffer_r):
        buffer_s, buffer_a, buffer_r = [], [], []
        v_s_ = GLOBAL_PPO.get_v(restate2)
        discounted_r = []                           # compute discounted reward
        for r in buffer_r[::-1]:
            v_s_ = r + GAMMA * v_s_
            discounted_r.append(v_s_)
        discounted_r.reverse()
        bs, ba, br = np.vstack(buffer_s), np.vstack(buffer_a), np.array(discounted_r)[:, np.newaxis]
        QUEUE.put(np.hstack((bs, ba, br)))
        data=QUEUE.get()
        #print('alldatas: {}'.format(data))
        for j in range(100):
            GLOBAL_PPO.update(data)
        GLOBAL_PPO.save()
        print('learning Finished!!!')

    def _build_anet(self, name, trainable):
        with tf.compat.v1.variable_scope(name,reuse=tf.AUTO_REUSE):
            l1 = tf.layers.dense(self.tfs, 200, tf.nn.relu, trainable=trainable)
            mu = 2 * tf.layers.dense(l1, A_DIM, tf.nn.relu, trainable=trainable)
            sigma = tf.layers.dense(l1, A_DIM, tf.nn.softplus, trainable=trainable)
            norm_dist = tf.distributions.Normal(loc=mu, scale=sigma)
        params = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope=name)
        return norm_dist, params

    def choose_action(self, s):
        s = s[np.newaxis, :]
        a = self.sess.run(self.sample_op, {self.tfs: s})[0]
        actions=np.clip(a, 0, 100)
        return actions

    def get_v(self, s):
        if s.ndim < 2: s = s[np.newaxis, :]
        return self.sess.run(self.v, {self.tfs: s})[0, 0]

    def save(self, ckpt_file='ckpt/dqn.ckpt'):
        if not checkpoint_management.checkpoint_exists(os.path.dirname(ckpt_file)):
            os.makedirs(os.path.dirname(ckpt_file))
        self.saver.save(self.sess, ckpt_file)

    def load(self, ckpt_dir='ckpt'):
        ckpt = tf.train.get_checkpoint_state(ckpt_dir)
        if ckpt:
            ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
            self.saver.restore(self.sess, os.path.join(ckpt_dir, ckpt_name))
            #print '[SUCCESS] Checkpoint loaded.'
        else:
            print ('[WARNING] No checkpoint found.')



mark=1
def reshapes(shapes):  ###actions(4)+states(10)
    drop=0
    queue=0
    global mark ##mark
    mark=1
    for k in range(4,44):
         if(mark==1):
            shapes[k]=shapes[k]/10000
            mark=2
         elif(mark==2):
            shapes[k]=shapes[k]/10
            mark=3
         elif(mark==3):
            drop=drop+shapes[k]
            shapes[k]=shapes[k]/10
            mark=4
         elif(mark==4):
            queue=queue+shapes[k]
            shapes[k]=shapes[k]/10
            mark=1
    shapes[0:4]=shapes[0:4]/10
    dropandqueue=drop*10+queue*100
    return shapes,dropandqueue


def learnmake(restate1,oldaction,reward):
    global buffer_s, buffer_a, buffer_r
    global GLOBAL_UPDATE_COUNTER
    buffer_s.append(restate1)
    buffer_a.append(oldaction)
    buffer_r.append(reward)
    GLOBAL_UPDATE_COUNTER += 1
    if(GLOBAL_UPDATE_COUNTER>MIN_BATCH_SIZE):
          t = threading.Thread(target=GLOBAL_PPO.learnandupdate(restate1,buffer_s,buffer_a,buffer_r), args=())
          t.start()
          buffer_s, buffer_a, buffer_r = [], [], []
          GLOBAL_UPDATE_COUNTER=0

def main(learnn):
    original=np.array([[3,1],[2,3],[3,2],[2,4]])
    learnss=np.array(learnn).reshape(4,1)
    learnlist=np.hstack((original,learnss))
    print(learnlist)
    i = 0
    probe_pkt = Ether(dst='ff:ff:ff:ff:ff:ff', src=get_if_hwaddr('eth0'))/Probe(hop_cnt=0,learn=1)
    for i in range(4):
        try:
            probe_pkt = probe_pkt / ProbeFwd(egress_spec=int(learnlist[i][0]),swid=int(learnlist[i][1]),percent=int(learnlist[i][2]))
        except ValueError:
            pass
    try:
        sendp(probe_pkt/ProbeFwd(egress_spec=2,swid=1,percent=int(learnlist[i][2])), iface='eth0')
    except KeyboardInterrupt:
        sys.exit()
       
     
if __name__ == "__main__":
    senders=sender()
    GLOBAL_PPO = PPO()
    GLOBAL_PPO.load()
    oldstate=np.ones((1,44))[0]
    oldaction=(np.ones((1,4))*25)[0]
    #global GLOBAL_UPDATE_COUNTER
    act=(np.ones((1,4))*25)[0]
    for i in range(100):
          f1 = "/home/p4/tutorials/exercises/linkmonitor/message/pponew.txt"
          fo = open("/home/p4/tutorials/exercises/linkmonitor/message/singledata.txt", "r")
          for line in fo.readlines():
              if line.strip()=='':
                continue
              line = line.strip().split(' ')
              line=list(map(eval, line))
              #print(line)
          if(len(line)!=42):
                act=oldaction
          else:
                try:
                      linesa=np.array(line).reshape(1,42)[0]
                       #print(linesa)
                      s=np.hstack((oldaction,linesa[1:21],linesa[22:42]))
                      restate1,dropque1=reshapes(s)
                      act=GLOBAL_PPO.choose_action(restate1)
                      reward =(linesa[0]+linesa[21]) if dropque1<0 else linesa[0]+linesa[21]-dropque1
                      #stortransmission(oldstate,oldaction,reward)
                      saction=' '.join(str(i) for i in act)
                      sstates=' '.join(str(j) for j in restate1)
                      with open(f1,"a") as file:
                          #file.write(str(state)+" "+str(action)+" "+str(reward)+" "+str(r)+'\n')
                          file.write(str(saction)+" "+str(sstates)+'\n')
                      oldstate=restate1
                      oldaction=act
                      fo.close()
                except KeyboardInterrupt:
                     act=oldaction
          main(act)  ###make the tuple<action,states>
          senders.sendpak() ####collect next states.
          time.sleep(2)

