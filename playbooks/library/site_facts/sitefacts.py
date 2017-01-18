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

''' Reserved for OS + DN + NM,  Map: Memory => Reservation '''
reservedStack = { 4:1, 8:2, 16:2, 24:4, 48:6, 64:8, 72:8, 96:12,
                   128:24, 256:32, 512:64}
''' Reserved for HBase. Map: Memory => Reservation '''

reservedHBase = {4:1, 8:1, 16:2, 24:4, 48:8, 64:8, 72:8, 96:16,
                   128:24, 256:32, 512:64}
GB = 1024

def getMinContainerSize(memory):
  if (memory <= 4):
    return 256
  elif (memory <= 8):
    return 512
  elif (memory <= 24):
    return 1024
  else:
    return 2048
  pass

def getReservedStackMemory(memory):
  if (reservedStack.has_key(memory)):
    return reservedStack[memory]
  if (memory <= 4):
    ret = 1
  elif (memory >= 512):
    ret = 64
  else:
    ret = 1
  return ret

def getReservedHBaseMem(memory):
  if (reservedHBase.has_key(memory)):
    return reservedHBase[memory]
  if (memory <= 4):
    ret = 1
  elif (memory >= 512):
    ret = 64
  else:
    ret = 2
  return ret

def main():

  module = None

  #Number of cores on each host
  #Amount of Memory on each host in GB
  #Number of disks on each host

  
  module = AnsibleModule(
      argument_spec = dict(
        cores =  dict(default=16, type='int'),
        memory = dict(default=64, type='int'),
        disks = dict(default=4, type='int'),
        hbaseEnabled = dict(default='True', type='bool')
      )
    )

  cores = module.params.get('cores')
  memory = module.params.get('memory')
  disks = module.params.get('disks')
  hbaseEnabled = module.params.get('hbaseEnabled')


  minContainerSize = getMinContainerSize(memory)
  reservedStackMemory = getReservedStackMemory(memory)
  reservedHBaseMemory = 0
  if (hbaseEnabled):
    reservedHBaseMemory = getReservedHBaseMem(memory)
  reservedMem = reservedStackMemory + reservedHBaseMemory
  usableMem = memory - reservedMem
  memory -= (reservedMem)
  if (memory < 2):
    memory = 2
    reservedMem = max(0, memory - reservedMem)

  memory *= GB

  containers = int (min(2 * cores,
                         min(math.ceil(1.8 * float(disks)),
                              memory/minContainerSize)))
  if (containers <= 2):
    containers = 3

#  print json.dumps({"Profile" : "this",
#                    "cores" : str(cores),
#                    "memory" : str(memory),
#                    "reserved" : str(reservedMem),
#                    "usableMem" : str(usableMem),
#                    "disks": str(disks)})
#
  container_ram =  abs(memory/containers)
  if (container_ram > GB):
    container_ram = int(math.floor(container_ram / 512)) * 512

  map_memory = container_ram
  reduce_memory = 2*container_ram if (container_ram <= 2048) else container_ram
  am_memory = max(map_memory, reduce_memory)

#  print json.dumps({"Num Container" : str(containers),
#                    "Container Ram MB" : str(container_ram),
#                    "Used Ram GB" : str(int (containers*container_ram/float(GB))),
#                    "Unused Ram GB" : str(reservedMem),
#                    "yarn.scheduler.minimum-allocation-mb" : str(container_ram),
#                    "yarn.scheduler.maximum-allocation-mb" : str(containers*container_ram),
#                    "yarn.nodemanager.resource.memory-mb" : str(containers*container_ram),
#                    "mapreduce.map.memory.mb" : str(map_memory),
#                    "mapreduce.map.java.opts" : "-Xmx" + str(int(0.8 * map_memory)) +"m",
#                    "mapreduce.reduce.memory.mb" : str(reduce_memory),
#                    "mapreduce.reduce.java.opts" : "-Xmx" + str(int(0.8 * reduce_memory)) + "m",
#                    "yarn.app.mapreduce.am.resource.mb" : str(am_memory),
#                    "yarn.app.mapreduce.am.command-opts" : "-Xmx" + str(int(0.8*am_memory)) + "m",
#                    "mapreduce.task.io.sort.mb" : str(int(0.4 * map_memory))})
#
  module.exit_json(changed=True, 
                   ansible_facts=dict(
                   yarn_scheduler_minimum_allocation_mb=container_ram, 
                   yarn_scheduler_maximum_allocation_mb=(containers*container_ram),
                   yarn_nodemanager_resource_memory_mb=(containers*container_ram),
                   mapreduce_map_memory_mb=map_memory,
                   mapreduce_map_java_opts="-Xmx" + str(int(0.8 * map_memory)) +"m", 
                   mapreduce_reduce_memory_mb=reduce_memory,
                   mapreduce_reduce_java_opts="-Xmx" + str(int(0.8 * reduce_memory)) + "m",
                   yarn_app_mapreduce_am_resource_mb=am_memory,
                   yarn_app_mapreduce_am_command_opts="-Xmx" + str(int(0.8*am_memory)) + "m",
                   mapreduce_task_io_sort_mb=int(0.4 * map_memory)
                   ))

if __name__ == '__main__':
    main()
