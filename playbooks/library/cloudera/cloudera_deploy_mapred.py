  # !/usr/bin/python  # This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# This is a DOCUMENTATION stub specific to this module, it extends
# a documentation fragment located in ansible.utils.module_docs_fragments
import socket, sys, time, ConfigParser, csv, pprint, urllib2
from subprocess import Popen, PIPE, STDOUT
from math import log as ln
from cm_api.api_client import ApiResource
from cm_api.api_client import ApiException
from cm_api.endpoints.services import ApiService
from cm_api.endpoints.services import ApiServiceSetupInfo

DOCUMENTATION = '''
---
module: cloudera_deploy_mapred
short_description: deploy mapreduce / delete a Cloudera cluster
description:
     - deploy mapreduce / deletes a Cloudera cluster using Cloudera Manager.
version_added: "2.1"
options:
  name:
    description:
      - Name to be given to the cluster
    default: null
  fullVersion:
    description:
      - Full version of the cluster
    default: 5.6.0
  admin_password:
    description:
      - Password of the admin account for the cluster
    default: admin
  cm_host:
    description:
      - Hostname of the node running Cloudera Manager
    default: localhost
  cluster_hosts:
    description:
      - Comma separated hostnames of the nodes forming the cluster
    default: null
  state:
    description:
      - Indicate desired state of the resource
    choices:
      - present
      - absent
    default: present
author: David Grier
'''

EXAMPLES = '''
- name: Build a Cloudera cluster
  gather_facts: False
  hosts: local
  connection: local
  tasks:
    - name: Cloudera cluster create request
      local_action:
        module: cloudera_init
        name: my-test-cluster
        fullVersion: 5.6.0
        admin_password: admin
        cm_host: localhost
        cluster_hosts: localhost
        state: present
      register: my_cdh

    - debug: var=my_cdh
'''


def find_cluster(module, api, name):
    try:
        cluster = api.get_cluster(name)
        if not cluster:
            return None

    except ApiException as e:
        if e.code == 404:
            return None
        module.fail_json(msg='Failed to get cluster.\nError is %s' % e)

    return cluster


def build_mapred_config(CLUSTER_HOSTS, HDFS_SERVICE_NAME, HADOOP_DATA_DIR_PREFIX, HDFS_DATANODE_HOSTS)
    ### MapReduce ###
    MAPRED_SERVICE_NAME = "MAPRED"
    MAPRED_SERVICE_CONFIG = {
        'hdfs_service': HDFS_SERVICE_NAME,
    }
    MAPRED_JT_HOST = CLUSTER_HOSTS[0]
    MAPRED_JT_CONFIG = {
        'mapred_jobtracker_restart_recover': 'true',
        'mapred_job_tracker_handler_count': 30,  # int(ln(len(DATANODES))*20),
        # 'jobtracker_mapred_local_dir_list': '/data01/hadoop/mapred',
        'jobtracker_mapred_local_dir_list': HADOOP_DATA_DIR_PREFIX + '/mapred',
        # 'mapreduce_jobtracker_staging_root_dir': '/data01/hadoop/staging',
        'mapreduce_jobtracker_staging_root_dir': HADOOP_DATA_DIR_PREFIX + '/staging',
        'mapreduce_jobtracker_split_metainfo_maxsize': '100000000',
    }
    MAPRED_TT_HOSTS = list(CLUSTER_HOSTS)
    MAPRED_TT_CONFIG = {
        # 'tasktracker_mapred_local_dir_list': '/data01/hadoop/mapred,/data02/hadoop/mapred,/data03/hadoop/mapred,/data04/hadoop/mapred,/data05/hadoop/mapred,/data06/hadoop/mapred,/data07/hadoop/mapred,/data08/hadoop/mapred',
        'tasktracker_mapred_local_dir_list': HADOOP_DATA_DIR_PREFIX + '/mapred',
        'mapred_tasktracker_map_tasks_maximum': 6,
        'mapred_tasktracker_reduce_tasks_maximum': 3,
        'override_mapred_child_java_opts_base': '-Xmx4g -Djava.net.preferIPv4Stack=true',
        'override_mapred_child_ulimit': 8388608,
        'override_mapred_reduce_parallel_copies': 5,
        'tasktracker_http_threads': 40,
        'override_mapred_output_compress': 'true',
        'override_mapred_output_compression_type': 'BLOCK',
        'override_mapred_output_compression_codec': 'org.apache.hadoop.io.compress.SnappyCodec',
        'override_mapred_compress_map_output': 'true',
        'override_mapred_map_output_compression_codec': 'org.apache.hadoop.io.compress.SnappyCodec',
        'override_io_sort_record_percent': '0.15',
    }
    MAPRED_GW_HOSTS = list(CLUSTER_HOSTS)
    MAPRED_GW_CONFIG = {
        'mapred_reduce_tasks': int(
            MAPRED_TT_CONFIG['mapred_tasktracker_reduce_tasks_maximum'] * len(HDFS_DATANODE_HOSTS) / 2),
        'mapred_submit_replication': 3,
    }

    return (MAPRED_SERVICE_NAME, MAPRED_SERVICE_CONFIG, MAPRED_JT_HOST, MAPRED_JT_CONFIG, MAPRED_TT_HOSTS, MAPRED_TT_CONFIG, MAPRED_GW_HOSTS, MAPRED_GW_CONFIG)

def deploy_mapreduce(module, api, name, mapred_service_name, mapred_service_config, mapred_jt_host, mapred_jt_config, mapred_tt_hosts, mapred_tt_config, mapred_gw_hosts, mapred_gw_config ):

    changed = False
    cluster = find_cluster(module, api, name)

    mapred_service = cluster.create_service(mapred_service_name, "MAPREDUCE")
    mapred_service.update_config(mapred_service_config)

    jt = mapred_service.get_role_config_group("{0}-JOBTRACKER-BASE".format(mapred_service_name))
    jt.update_config(mapred_jt_config)
    mapred_service.create_role("{0}-jt".format(mapred_service_name), "JOBTRACKER", mapred_jt_host)

    tt = mapred_service.get_role_config_group("{0}-TASKTRACKER-BASE".format(mapred_service_name))
    tt.update_config(mapred_tt_config)

    gw = mapred_service.get_role_config_group("{0}-GATEWAY-BASE".format(mapred_service_name))
    gw.update_config(mapred_gw_config)

    tasktracker = 0
    for host in mapred_tt_hosts:
        tasktracker += 1
        mapred_service.create_role("{0}-tt-".format(mapred_service_name) + str(tasktracker), "TASKTRACKER", host)

    gateway = 0
    for host in mapred_gw_hosts:
        gateway += 1
        mapred_service.create_role("{0}-gw-".format(mapred_service_name) + str(gateway), "GATEWAY", host)

    return mapred_service


result = dict(changed=changed, cluster=cluster.name)
module.exit_json(**result)



def delete_cluster(module, api, name):

    changed = False
    cluster = find_cluster(module, api, name)
    if cluster:
        try:
            api.delete_cluster(name)
            changed = True
            time.sleep(5)
        except ApiException as e:
            module.fail_json(msg='Failed to delete cluster.\nError is %s' % e)
    else:
        module.fail_json(msg='Cluster does not exist.')

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)


def main():
    argument_spec = dict(
        name=dict(type='str'),
        fullVersion=dict(type='str', default='5.6.0'),
        admin_password=dict(type='str', default='admin'),
        state=dict(default='present', choices=['present', 'absent']),
        cm_host=dict(type='str', default='localhost'),
        cluster_hosts=dict(type='str', default='locahost'),
        hdfs_service_name=dict(type='str', default='HDFS'),
        hadoop_data_dir_prefix=dict(type='str', default='/grid'),
        hdfs_datanode_hosts=dict(type='str', default='localhost'),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(default=30)
    )

    module = AnsibleModule(
        argument_spec=argument_spec
    )

    name = module.params.get('name')
    fullVersion = module.params.get('fullVersion')
    admin_password = module.params.get('admin_password')
    state = module.params.get('state')
    cm_host = module.params.get('cm_host')
    cluster_hosts = module.params.get('hosts')
    hdfs_service_name = module.params.get('hdfs_service_name')
    hadoop_data_dir_prefix = module.params.get('hadoop_data_dir_prefix')
    hdfs_datanode_hosts = module.params.get('hdfs_datanode_hosts')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_mapred_config(cluster_hosts, hdfs_service_name, hadoop_data_dir_prefix, hdfs_datanode_hosts)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        try:
        mapred_service =  deploy_mapreduce(CLUSTER, MAPRED_SERVICE_NAME, MAPRED_SERVICE_CONFIG, MAPRED_JT_HOST, MAPRED_JT_CONFIG, MAPRED_TT_HOSTS, MAPRED_TT_CONFIG, MAPRED_GW_HOSTS, MAPRED_GW_CONFIG)

        except: ApiException as e:
            module.fail_json(msg='Failed to deploy mapreduce.\nError is %s' % e)



# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
