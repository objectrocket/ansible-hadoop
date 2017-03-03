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

from datetime import datetime
import hashlib
import os
import six
import sys

from ambariclient.client import Ambari


GB = 1024


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

def matchconfigs(curr_params, rec_params, config):

    compared_cur = dict()
    compared_rec = dict()

    for key in rec_params.iterkeys:
       update_config[key] = rec_params[key] 
       if ('site' in config):
          key = param.replace('_', '.', 10)
       compared_cur[param] = curr_params[key]
 
    return (compared_cur, compared_rec)



def update_config(cluster, config_name, new_properties):
    """Update configuration for an Ambari service"""
    tag = max(
        (config.version, config.tag)
        for config in cluster.configurations(type=config_name)
    )[-1]

    try:
        config = six.next(cluster.refresh().configurations(type=config_name, tag=tag))
    except StopIteration:
        print 'No configuration found for config {} at tag {}'.format(config_name, tag)
        sys.exit(1)

    properties = config.properties
    original_sha = hashlib.sha256(json.dumps(properties)).hexdigest()

    """Sanitise new properties"""
   for key in new_properties.iterkeys():

new_conf=dict()

for key in new_properties.iterkeys():
      
    property = key.replace('_', '.', 10).replace('-','.')
    re_obj = re.compile(property)
    new_conf = dict()
    for my_key in properties:
        my_key = str(my_key)
        if re.match(re_obj, my_key):
            property = new_properties[key]
            new_conf[my_key]=property

    properties.update(new_conf)
    new_sha = hashlib.sha256(json.dumps(properties)).hexdigest()

    if original_sha == new_sha:
      print "Nothing to update"
      sys.exit(0)

    timestamp = int((datetime.now() - datetime.fromtimestamp(0)).total_seconds()) * 1000
    new_version = 'version{}'.format(timestamp)

    data = {
        'desired_config': {
            'type': config_name,
            'tag': new_version,
            'properties': properties
        }
    }
    cluster.update(Clusters=data)


def main():

  module = None

  module = AnsibleModule(
      argument_spec = dict(
        ambari_server = dict(default='localhost', type='str'), 
        ambari_pass = dict(default='admin', type='str'),
        cluster_name = dict(default='hadoop-poc',type='str'),
        config_name = dict(type='str'),
        properties = dict(type='dict')
      )
    )

  ambari_server = module.params.get('ambari_server')
  ambari_pass = module.params.get('ambari_pass')
  cluster_name = module.params.get('cluster_name')
  config_name = module.params.get('config_name')
  properties = module.params.get('properties')



    client = Ambari(ambari_server,  port=8080, username=ambari_user, password=ambari_pass)

    update_config(next(client.clusters), config_name, properties)



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
