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
import requests
import re

from ansible.module_utils.basic import *

''' Reserved for OS + DN + NM,  Map: dnmemory => Reservation '''
reservedStack = { 4:1, 8:2, 16:2, 24:4, 48:6, 64:8, 72:8, 96:12,
                   128:24, 256:32, 512:64}
''' Reserved for HBase. Map: dnmemory => Reservation '''

reservedHBase = {4:1, 8:1, 16:2, 24:4, 48:8, 64:8, 72:8, 96:16,
                   128:24, 256:32, 512:64}
GB = 1024


def getMinContainerSize(dnmemory):
  if (dnmemory <= 4):
    return 256
  elif (dnmemory <= 8):
    return 512
  elif (dnmemory <= 24):
    return 1024
  else:
    return 2048
  pass

def getReservedStackdnmemory(dnmemory):
  if ('dnmemory' in reservedStack):
    return reservedStack[dnmemory]
  if (dnmemory <= 4):
    ret = 1
  elif (dnmemory >= 512):
    ret = 64
  else:
    ret = 1
  return ret

def getReservedHBaseMem(dnmemory):
  if ('dnmemory' in reservedHBase):
    return reservedHBase[dnmemory]
  if (dnmemory <= 4):
    ret = 1
  elif (dnmemory >= 512):
    ret = 64
  else:
    ret = 2
  return ret

def clip(lo, x, hi):
    return lo if x <= lo else hi if x >= hi else x

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

def core_site_facts():
    core_site=dict()
    
    core_site['fs_trash_interval']="4320"

    return core_site

def hive_site_facts(dnmemory):
    hive_site=dict()

    if (dnmemory > 87):
        hive_site['hive_tez_container_size']="8192"
    elif (dnmemory > 24):
        hive_site['hive_tez_container_size']="4096"
    else:
        hive_site['hive_tez_container_size']="2048"

    hive_site['fs_file_impl_disable_cache'] = "true"
    hive_site['fs_hdfs_impl_disable_cache'] = "true"
    hive_site['hive_plan_serialization_format'] = "kryo"
    hive_site['hive_execution_engine'] = "tez"
    hive_site['hive_exec_compress_intermediate'] = "true"
    hive_site['hive_exec_compress_output'] = "true"
    hive_site['hive_merge_mapfiles'] = "false"
    hive_site['hive_default_fileformat_managed'] = "ORC"
    hive_site['hive_compute_query_using_stats'] = "true"
    hive_site['hive_cbo_enable'] = "true"
    hive_site['hive_stats_fetch_column_stats'] = "true"
    hive_site['hive_stats_fetch_partition_stats'] = "true"
    hive_site['hive_vectorized_execution_reduce_enabled'] = "true"
    hive_site['hive_server2_tez_initialize_default_sessions'] = "true"

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

def hbase_site_facts():
    hbase_site=dict()

    hbase_site['hbase_master_wait_on_regionservers_timeout'] = "30000"
    hbase_site['hbase_master_namespace_init_timeout'] = "2400000"
    hbase_site['hbase_regionserver_executor_openregion_threads'] = "20"

    return hbase_site
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
        spark_defaults['spark_yarn_executor_memoryOverhead']="384"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384"
        spark_defaults['spark_yarn_am_memoryOverhead']="384"
    elif (dnmemory > 57):
        spark_defaults['spark_yarn_executor_memory']="7808m"
        spark_defaults['spark_driver_memory']="3712m"
        spark_defaults['spark_yarn_am_memory']="3712m"
        spark_defaults['spark_yarn_executor_memoryOverhead']="384"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384"
        spark_defaults['spark_yarn_am_memoryOverhead']="384"
    else:
        spark_defaults['spark_yarn_executor_memory']="7808m"
        spark_defaults['spark_driver_memory']="3712m"
        spark_defaults['spark_yarn_am_memory']="3712m"
        spark_defaults['spark_yarn_executor_memoryOverhead']="384"
        spark_defaults['spark_yarn_driver_memoryOverhead']="384"
        spark_defaults['spark_yarn_am_memoryOverhead']="384"

    return spark_defaults

def mapred_site_facts(map_memory,reduce_memory,am_memory):

    mapred_site=dict()
    mapred_site['mapreduce_map_memory_mb']=clip(1028, map_memory, 4096)
    mapred_site['mapreduce_map_java_opts']="-Xmx" + str(clip(1028, int(0.8 * map_memory), 8192))  +"m"
    mapred_site['mapreduce_reduce_memory_mb']=clip(1028, reduce_memory, 4096)
    mapred_site['mapreduce_reduce_java_opts']="-Xmx" + str(clip(1028, int(0.8 * reduce_memory), 8192)) + "m"
    mapred_site['mapreduce_task_io_sort_mb']=clip(1028, int(0.4 * map_memory), 8192)
    mapred_site['yarn_app_mapreduce_am_resource_mb']=clip(1028, am_memory, 4096)
    mapred_site['yarn_app_mapreduce_am_command_opts']="-Xmx" + str(clip(1028, int(0.8*am_memory), 8192)) + "m"

    mapred_site['mapreduce_output_fileoutputformat_compress'] = "true"
    mapred_site['mapreduce_map_output_compress'] = "true"
    mapred_site['mapreduce_job_reduce_slowstart_completedmaps'] = "0.7"

    return mapred_site

def hdfs_site_facts():
    hdfs_site=dict()

    hdfs_site['dfs_datanode_balance_bandwidthPerSec']="12500000"
    hdfs_site['dfs_datanode_max_transfer_threads']="4096"
    hdfs_site['dfs_replication'] = "3"
    
    return hdfs_site

def yarn_site_facts(container_ram,containers):
    yarn_site=dict()

    yarn_site['yarn_scheduler_minimum_allocation_mb']=clip(1024, container_ram, 8192)
    yarn_site['yarn_scheduler_maximum_allocation_mb']=clip(1024, (containers*container_ram), 8192)
    yarn_site['yarn_nodemanager_resource_memory_mb']=clip(1024, (containers*container_ram), 8192)

    yarn_site['yarn_timeline-service_store-class'] = "org.apache.hadoop.yarn.server.timeline.RollingLevelDBTimelineStore"
    yarn_site['yarn_timeline-service_generic-application-history_save-non-am-container-meta-info'] = "false"

    return yarn_site

def tez_site_facts(dnmemory):
    tez_site=dict()

    if (dnmemory > 110):
        tez_site['tez_am_resource_memory_mb']="8192"
        tez_site['tez_task_resource_memory_mb']="8192"
        memopts="4096"
    elif (dnmemory > 57):
        tez_site['tez_am_resource_memory_mb']="4096"
        tez_site['tez_task_resource_memory_mb']="4096"
        memopts="2048"
    else:
        tez_site['tez_am_resource_memory_mb']="2048"
        tez_site['tez_task_resource_memory_mb']="2048"
        memopts="1024"

    tez_site['tez_am_launch_cmd-opts']="-XX:+PrintGCDetails -verbose:gc -XX:+PrintGCTimeStamps -XX:+UseNUMA -XX:+UseParallelGC -Xmx" + memopts + "m"

    return tez_site

def zeppelin_env_facts(mnmemory):
    zeppelin_env=dict()

    if (mnmemory > 110):
        zeppelin_env['zeppelin_executor_memory']="4096m"
    elif (mnmemory > 57):
        zeppelin_env['zeppelin_executor_memory']="2048m"
    else:
        zeppelin_env['zeppelin_executor_memory']="1024m"

    zeppelin_env['zeppelin_executor_instances'] = "2"
    
    return zeppelin_env

def get_config_property(ambari_server, cluster_name, ambari_pass, params, config):

        curr_conf = dict()
        url='http://' + ambari_server + ':8080/api/v1/clusters/' + cluster_name
        desired_config=requests.get(url + '?fields=Clusters/desired_configs/' + config, auth=('admin', ambari_pass))
        this=desired_config.json()
        
        tag=this['Clusters']['desired_configs'][config]['tag']
        
        desired_conf = requests.get(url + '/configurations?type=' + config + '&tag=' + str(tag), auth=('admin', ambari_pass))
        this=desired_conf.json()
    
        for key in params.iterkeys():
                            
            try:
                property  = key.replace('_', '.', 10).replace('-','.')
                re_obj = re.compile(property)
                for my_key in this['items'][0]['properties']:
                  if re.match(re_obj, my_key):
                      property = this['items'][0]['properties'][my_key]
            except KeyError:
                property = this['items'][0]['properties'][key]
                
            curr_conf[key]=property 

        return curr_conf

def compare_configs(curr_params, rec_params, config):

    compared_cur = dict()
    compared_rec = dict()

    for key in rec_params.iterkeys:
       compared_rec[key] = rec_params[key] 
       if ('site' in config):
          key = param.replace('_', '.', 10)
       compared_cur[param] = curr_params[key]
 
    return (compared_cur, compared_rec)

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
        hbaseEnabled = dict(default='True', type='bool'),
        ambari_server = dict(default='localhost', type='str'), 
        ambari_pass = dict(default='admin', type='str'),
        cluster_name = dict(default='hadoop-poc',type='str'),
        compare = dict(default='True', type='bool'),
        current_facts = dict(default='True', type='bool')
      )
    )

  cores = int(module.params.get('cores'))
  mnmemory = int(round(module.params.get('mnmemory')))
  dnmemory = int(round(module.params.get('dnmemory')))
  disks = int(module.params.get('disks'))
  hbaseEnabled = module.params.get('hbaseEnabled')
  ambari_server = module.params.get('ambari_server')
  ambari_pass = module.params.get('ambari_pass')
  cluster_name = module.params.get('cluster_name')
  compare = module.params.get('compare')
  current_facts = module.params.get('compare')

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
  core_site = core_site_facts()
  hive_site = hive_site_facts(dnmemory)
  hive_env = hive_env_facts(mnmemory)
  hbase_env = hbase_env_facts(mnmemory,dnmemory)
  hbase_site = hbase_site_facts()
  hadoop_env = hadoop_env_facts(mnmemory,dnmemory)
  spark_defaults = spark_defaults_facts(dnmemory)
  mapred_site = mapred_site_facts(map_memory,reduce_memory,am_memory)
  hdfs_site = hdfs_site_facts()
  yarn_site = yarn_site_facts(container_ram,containers)
  tez_site = tez_site_facts(dnmemory)
  zeppelin_env = zeppelin_env_facts(mnmemory)
  if current_facts:    
    curr_ams_hbase_env = get_config_property(ambari_server, cluster_name, ambari_pass, ams_hbase_env, 'ams-hbase-env') 
    curr_ams_env = get_config_property(ambari_server, cluster_name, ambari_pass, ams_env, 'ams-env') 
    curr_core_site =  get_config_property(ambari_server, cluster_name, ambari_pass, core_site, 'core-site') 
    curr_hive_site = get_config_property(ambari_server, cluster_name, ambari_pass, hive_site, 'hive-site') 
    curr_hive_env = get_config_property(ambari_server, cluster_name, ambari_pass, hive_env, 'hive-env') 
    curr_hbase_env = get_config_property(ambari_server, cluster_name, ambari_pass, hbase_env, 'hbase-env') 
    curr_hbase_site = get_config_property(ambari_server, cluster_name, ambari_pass, hbase_site, 'hbase-site') 
    curr_hadoop_env = get_config_property(ambari_server, cluster_name, ambari_pass, hadoop_env, 'hadoop-env') 
    curr_spark_defaults = get_config_property(ambari_server, cluster_name, ambari_pass, spark_defaults, 'spark-defaults') 
    curr_mapred_site = get_config_property(ambari_server, cluster_name, ambari_pass, mapred_site, 'mapred-site') 
    curr_hdfs_site = get_config_property(ambari_server, cluster_name, ambari_pass, hdfs_site, 'hdfs-site') 
    curr_yarn_site = get_config_property(ambari_server, cluster_name, ambari_pass, yarn_site, 'yarn-site') 
    curr_tez_site = get_config_property(ambari_server, cluster_name, ambari_pass, tez_site, 'tez-site') 
#    curr_zeppelin_env = get_config_property(ambari_server, cluster_name, ambari_pass, zeppelin_env, 'zeppelin-env') 

#  print json.dumps({"Num Container" : str(containers),
#                    "Container Ram MB" : str(container_ram),
#                    "Used Ram GB" : str(int (containers*container_ram/float(GB))),
#                    "Unused Ram GB" : str(reservedMem),

  if current_facts:
    module.exit_json(changed=True,
         ansible_facts=dict(
         ams_hbase_env=dict(ams_hbase_env),
         ams_env=dict(ams_env),
         core_site=dict(core_site),
         hive_site=dict(hive_site),
         hive_env=dict(hive_env),
         hbase_env=dict(hbase_env),
         hbase_site=dict(hbase_site),
         hadoop_env=dict(hadoop_env),
         spark_defaults=dict(spark_defaults),
         mapred_site=dict(mapred_site),
         hdfs_site=dict(hdfs_site),
         yarn_site=dict(yarn_site),
         tez_site=dict(tez_site),
         zeppelin_env=dict(zeppelin_env),
         curr_ams_hbase_env=dict(curr_ams_hbase_env),
         curr_ams_env=dict(curr_ams_env), 
         curr_core_site=dict(curr_core_site),
         curr_hive_site=dict(curr_hive_site),
         curr_hive_env=dict(curr_hive_env),
         curr_hbase_env=dict(curr_hbase_env),
         curr_hbase_site=dict(curr_hbase_site),
         curr_hadoop_env=dict(curr_hadoop_env),
         curr_spark_defaults=dict(curr_spark_defaults),
         curr_mapred_site=dict(curr_mapred_site),
         curr_hdfs_site=dict(curr_hdfs_site),
         curr_yarn_site=dict(curr_yarn_site),
         curr_tez_site=dict(curr_tez_site)
         ))
  else:
                   module.exit_json(changed=True,
                           ansible_facts=dict(
                           ams_hbase_env=dict(ams_hbase_env),
                           ams_env=dict(ams_env),
                           core_site=dict(core_site),
                           hive_site=dict(hive_site),
                           hive_env=dict(hive_env),
                           hbase_env=dict(hbase_env),
                           hbase_site=dict(hbase_site),
                           hadoop_env=dict(hadoop_env),
                           spark_defaults=dict(spark_defaults),
                           mapred_site=dict(mapred_site),
                           hdfs_site=dict(hdfs_site),
                           yarn_site=dict(yarn_site),
                           tez_site=dict(tez_site),
                           zeppelin_env=dict(zeppelin_env) 
                           ))

if __name__ == '__main__':
    main()
