#!/usr/bin/env python
'''
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

# This file is part of Ansible

import math
import json

from ansible.module_utils.basic import *

''' Reserved for OS + DN + NM,  Map: dnmemory => Reservation '''
reservedStack = { 4:1, 8:2, 16:2, 24:4, 48:6, 64:8, 72:8, 96:12,
                   128:24, 256:32, 512:64}
''' Reserved for HBase. Map: dnmemory => Reservation '''

reservedHBase = {4:1, 8:1, 16:2, 24:4, 48:8, 64:8, 72:8, 96:16,
                   128:24, 256:32, 512:64}
GB = 1024

def getMinContainerSize(dndnmemory):
  if (dndnmemory <= 4):
    return 256
  elif (dndnmemory <= 8):
    return 512
  elif (dndnmemory <= 24):
    return 1024
  else:
    return 2048
  pass

def getReservedStackdnmemory(dnmemory):
  if (reservedStack.has_key(dnmemory)):
    return reservedStack[dnmemory]
  if (dnmemory <= 4):
    ret = 1
  elif (dnmemory >= 512):
    ret = 64
  else:
    ret = 1
  return ret

def getReservedHBaseMem(dnmemory):
  if (reservedHBase.has_key(dnmemory)):
    return reservedHBase[dnmemory]
  if (dnmemory <= 4):
    ret = 1
  elif (dnmemory >= 512):
    ret = 64
  else:
    ret = 2
  return ret


def ams_hbase_env_facts(mnmemory,dnmemory):
    ams_hbase_env=dict()

    if (mnmemory > 87):
        ams_hbase_env['hbase_master_xmn_size']="512m"
        ams_hbase_env['hbase_master_heapsize']="4096m"
    elif (mnmemory > 24):
        ams_hbase_env['hbase_master_xmn_size']="512m"
        ams_hbase_env['hbase_master_heapsize']="2048m"
    else:
        ams_hbase_env['hbase_master_xmn_size']="384m"
        ams_hbase_env['hbase_master_heapsize']="1024m"

    if (dnmemory > 87):
        ams_hbase_env['regionserver_xmn_size']="512m"
        ams_hbase_env['hbase_regionserver_heapsize']="4094m"
    elif (dnmemory > 24):
        ams_hbase_env['regionserver_xmn_size']="512m"
        ams_hbase_env['hbase_regionserver_heapsize']="2048m"
    else:
        ams_hbase_env['regionserver_xmn_size']="384m"
        ams_hbase_env['hbase_regionserver_heapsize']="1024m"

    return ams_hbase_env

def ams_env_facts(mnmemory):
    ams_env=dict()

    if (mnmemory > 87):
        ams_env['metrics_collector_heapsize']="4096m"
    elif (mnmemory > 24):
        ams_env['metrics_collector_heapsize']="2048m"
    else:
        ams_env['metrics_collector_heapsize']="1024m"

    return ams_env

def hive_site_facts(dnmemory):
    hive_site=dict()

    if (dnmemory > 87):
        hive_site['hive_tez_container_size']="8192"
    elif (dnmemory > 24):
        hive_site['hive_tez_container_size']="4096"
    else:
        hive_site['hive_tez_container_size']="2048"
    return hive_site

def hive_env_facts(mnmemory):
    hive_env=dict()
    if (mnmemory > 87):
        hive_env['hive_heapsize']="8192"
        hive_env['hive_metastore_heapsize']="8192"
        hive_env['hive_client_heapsize']="2048"
    elif (mnmemory > 24):
        hive_env['hive_heapsize']="4096"
        hive_env['hive_metastore_heapsize']="1024"
        hive_env['hive_client_heapsize']="1024"
    else:
        hive_env['hive_heapsize']="1024"
        hive_env['hive_metastore_heapsize']="1024"
        hive_env['hive_client_heapsize']="1024"
    return hive_env
    
def hbase_env_facts(mnmemory,dnmemory):
    hbase_env=dict()

    if (mnmemory > 87):
        hbase_env['hbase_master_heapsize']="8192m"
    elif (mnmemory > 24):
        hbase_env['hbase_master_heapsize']="4096m"
    else:
        hbase_env['hbase_master_heapsize']="1024m"

 
    if (dnmemory > 110):
        hbase_env['hbase_regionserver_heapsize']="16384m"
        hbase_env['hbase_regionserver_xmn_max']="2048m"
    elif (dnmemory > 58):
        hbase_env['hbase_regionserver_heapsize']="8192m"
        hbase_env['hbase_regionserver_xmn_max']="1538m"
    else:
        hbase_env['hbase_regionserver_heapsize']="4096m"
        hbase_env['hbase_regionserver_xmn_max']="768m"
       
    return hbase_env

def hadoop_env_facts(mnmemory,dnmemory):
      hadoop_env=dict()
      if (mnmemory > 87):
          hadoop_env['namenode_heapsize']="8192m"
          hadoop_env['namenode_opt_maxnewsize']="512m"
          hadoop_env['namenode_opt_newsize']="512m"
      elif (mnmemory > 24):
          hadoop_env['namenode_heapsize']="4096m"
          hadoop_env['namenode_opt_maxnewsize']="512m"
          hadoop_env['namenode_opt_newsize']="512m"
      else:
          hadoop_env['namenode_heapsize']="2048m"
          hadoop_env['namenode_opt_maxnewsize']="384m"
          hadoop_env['namenode_opt_newsize']="384m"
                
      if (dnmemory > 110):
          hadoop_env['dtnode_heapsize']="4096m"
      elif (dnmemory > 57):
          hadoop_env['dtnode_heapsize']="2048m"
      else:
          hadoop_env['dtnode_heapsize']="1024m"
    
      return hadoop_env

def spark_defaults_facts(dnmemory):
    spark_defaults=dict()

    if (dnmemory > 110):
        spark_defaults['spark_yarn_executor_memory']="7808m"            
        spark_defaults['spark_driver_memory']="7808m"
        spark_defaults['spark_yarn_am_memory']="7808m"
        spark_defaults['spark_yarn_executor_memoryOverhead']="384m"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384m"
        spark_defaults['spark_yarn_am_memoryOverhead']="384m"       
    elif (dnmemory > 57):
        spark_defaults['spark_yarn_executor_memory']="7808m"            
        spark_defaults['spark_driver_memory']="3712m"
        spark_defaults['spark_yarn_am_memory']="3712m"
        spark_defaults['spark_yarn_executor_memoryOverhead']="384m"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384m"    
        spark_defaults['spark_yarn_am_memoryOverhead']="384m"
    else:
        spark_defaults['spark_yarn_executor_memory']="7808m"            
        spark_defaults['spark_driver_memory']="3712m"
        spark_defaults['spark_yarn_am_memory']="3712m"
        spark_defaults['spark_yarn_executor_memoryOverhead']="384m"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384m"    
        spark_defaults['spark_yarn_am_memoryOverhead']="384m"

    return spark_defaults    

def mapred_site_facts(map_memory,reduce_memory,am_memory):

    mapred_site=dict()
    mapred_site['mapreduce_map_memory_mb']=map_memory
    mapred_site['mapreduce_map_java_opts']="-Xmx" + str(int(0.8 * map_memory)) +"m"
    mapred_site['mapreduce_reduce_memory_mb']=reduce_memory
    mapred_site['mapreduce_reduce_java_opts']="-Xmx" + str(int(0.8 * reduce_memory)) + "m"
    mapred_site['mapreduce_task_io_sort_mb']=int(0.4 * map_memory)
    mapred_site['yarn_app_mapreduce_am_resource_mb']=am_memory
    mapred_site['yarn_app_mapreduce_am_command_opts']="-Xmx" + str(int(0.8*am_memory)) + "m"

    return mapred_site
 
def hdfs_site_facts():
    hdfs_site=dict()

    hdfs_site['dfs_datanode_balance_bandwidthPerSec']="12500000"
    hdfs_site['dfs_datanode_balance_trafnsfer_threads']="4096"

    return hdfs_site 

def yarn_site_facts(container_ram,containers):
    yarn_site=dict()

    yarn_site['yarn_scheduler_minimum_allocation_mb']=container_ram
    yarn_site['yarn_scheduler_maximum_allocation_mb']=(containers*container_ram)
    yarn_site['yarn_nodemanager_resource_memory_mb']=(containers*container_ram)

    return yarn_site
    
def tez_site_facts(dnmemory):
    tez_site=dict()

    if (dnmemory > 110):
        tez_site['tez_am_resource_memory_mb']="8192"
        tez_site['tez_task_resource_memory_mb']="8192"
    elif (dnmemory > 57):
        tez_site['tez_am_resource_memory_mb']="4096"
        tez_site['tez_task_resource_memory_mb']="4096"
    else:
        tez_site['tez_am_resource_memory_mb']="2048"
        tez_site['tez_task_resource_memory_mb']="2048"

    return tez_site
    
def zeppelin_env_facts(mnmemory):
    zeppelin_env=dict()

    if (mnmemory > 110):
        zeppelin_env['zeppelin_executor_memory']="4096m"
    elif (mnmemory > 57):
        zeppelin_env['zeppelin_executor_memory']="2048m"
    else:
        zeppelin_env['zeppelin_executor_memory']="1024m"

    return zeppelin_env

def main():

  module = None

  #Number of cores on each host
  #Amount of dnmemory on each host in GB
  #Number of disks on each host


  module = AnsibleModule(
      argument_spec = dict(
        cores =  dict(default=16, type='str'),
        mnmemory = dict(default=64, type='float'),
        dnmemory = dict(default=64, type='float'),
        disks = dict(default=4, type='str'),
        hbaseEnabled = dict(default='True', type='bool')
      )
    )

  cores = int(module.params.get('cores'))
  mnmemory = int(round(module.params.get('mnmemory')))
  dnmemory = int(round(module.params.get('dnmemory')))
  disks = int(module.params.get('disks'))
  hbaseEnabled = module.params.get('hbaseEnabled')


  minContainerSize = getMinContainerSize(dnmemory)
  reservedStackdnmemory = getReservedStackdnmemory(dnmemory)
  reservedHBasednmemory = 0
  if (hbaseEnabled):
    reservedHBasednmemory = getReservedHBaseMem(dnmemory)
  reservedMem = reservedStackdnmemory + reservedHBasednmemory
  usableMem = dnmemory - reservedMem
  dnmemory -= (reservedMem)
  if (dnmemory < 2):
    dnmemory = 2
    reservedMem = max(0, dnmemory - reservedMem)

  dnmemory *= GB

  containers = int (min(2 * cores,
                         min(math.ceil(1.8 * float(disks)),
                              dnmemory/minContainerSize)))
  if (containers <= 2):
    containers = 3

  container_ram =  abs(dnmemory/containers)
  if (container_ram > GB):
    container_ram = int(math.floor(container_ram / 512)) * 512

  map_memory = container_ram
  reduce_memory = 2*container_ram if (container_ram <= 2048) else container_ram
  am_memory = max(map_memory, reduce_memory)


  ams_hbase_env = ams_hbase_env_facts(mnmemory,dnmemory)
  ams_env = ams_env_facts(mnmemory)
  hive_site = hive_site_facts(dnmemory)
  hive_env = hive_env_facts(mnmemory)
  hbase_env = hbase_env_facts(mnmemory,dnmemory)
  hadoop_env = hadoop_env_facts(mnmemory,dnmemory)
  spark_defaults = spark_defaults_facts(dnmemory)
  mapred_site = mapred_site_facts(map_memory,reduce_memory,am_memory)
  hdfs_site = hdfs_site_facts()
  yarn_site = yarn_site_facts(container_ram,containers)
  tez_site = tez_site_facts(dnmemory)
  zeppelin_env = zeppelin_env_facts(mnmemory)
  
#  print json.dumps({"Num Container" : str(containers),
#                    "Container Ram MB" : str(container_ram),
#                    "Used Ram GB" : str(int (containers*container_ram/float(GB))),
#                    "Unused Ram GB" : str(reservedMem),

  module.exit_json(changed=True,
                   ansible_facts=dict(
                   ams_hbase_env=dict(ams_hbase_env),
                   ams_env=dict(ams_env),
                   hive_site=dict(zeppelin_env),
                   hive_env=dict(hive_env),
                   hbase_env=dict(zeppelin_env),
                   hadoop_env=dict(zeppelin_env),
                   spark_defaults=dict(spark_defaults),
                   mapred_site=dict(mapred_site),
                   hdfs_site=dict(hdfs_site),
                   yarn_site=dict(yarn_site),
                   tez_site=dict(tez_site),
                   zeppelin_env=dict(zeppelin_env)
                   ))

if __name__ == '__main__':
    main()

