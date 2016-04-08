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
module: cloudera_deploy_hdfs
short_description: deploy hdfs / delete a Cloudera cluster
description:
     - deploy hdfs / deletes a Cloudera cluster using Cloudera Manager.
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


def build_hdfs_config(module, api, cm_host, CLUSTER_HOSTS)
    ### HDFS ###
    HDFS_SERVICE_NAME = "HDFS"
    HDFS_SERVICE_CONFIG = {
        'dfs_replication': 3,
        'dfs_permissions': 'false',
        'dfs_block_local_path_access_user': 'impala,hbase,mapred,spark',
    }
    HDFS_NAMENODE_SERVICE_NAME = "nn"
    HDFS_NAMENODE_HOST = CLUSTER_HOSTS[0]
    HDFS_NAMENODE_CONFIG = {
        # 'dfs_name_dir_list': '/data01/hadoop/namenode',
        'dfs_name_dir_list': HADOOP_DATA_DIR_PREFIX + '/grid/',
        'dfs_namenode_handler_count': 30,  # int(ln(len(DATANODES))*20),
    }
    HDFS_SECONDARY_NAMENODE_HOST = CLUSTER_HOSTS[1]
    HDFS_SECONDARY_NAMENODE_CONFIG = {
        # 'fs_checkpoint_dir_list': '/data01/hadoop/namesecondary',
        'fs_checkpoint_dir_list': HADOOP_DATA_DIR_PREFIX + '/namesecondary',
    }
    HDFS_DATANODE_HOSTS = list(CLUSTER_HOSTS)
    # dfs_datanode_du_reserved must be smaller than the amount of free space across the data dirs
    # Ideally each data directory will have at least 1TB capacity; they need at least 100GB at a minimum
    # dfs_datanode_failed_volumes_tolerated must be less than the number of different data dirs (ie volumes) in dfs_data_dir_list
    HDFS_DATANODE_CONFIG = {
        # 'dfs_data_dir_list': '/data01/hadoop/datanode,/data02/hadoop/datanode,/data03/hadoop/datanode,/data04/hadoop/datanode,/data05/hadoop/datanode,/data06/hadoop/datanode,/data07/hadoop/datanode,/data08/hadoop/datanode',
        'dfs_data_dir_list': HADOOP_DATA_DIR_PREFIX + '/datanode',
        'dfs_datanode_handler_count': 30,
        # 'dfs_datanode_du_reserved': 42949672960,
        'dfs_datanode_du_reserved': 1073741824,
        'dfs_datanode_failed_volumes_tolerated': 0,
        'dfs_datanode_data_dir_perm': 755,
    }
    HDFS_GATEWAY_HOSTS = list(CLUSTER_HOSTS)
    HDFS_GATEWAY_HOSTS.append(CM_HOST)
    HDFS_GATEWAY_CONFIG = {
        'dfs_client_use_trash': 'true'
    }

    return (HDFS_SERVICE_NAME, HDFS_SERVICE_CONFIG, HDFS_NAMENODE_SERVICE_NAME, HDFS_NAMENODE_HOST, HDFS_NAMENODE_CONFIG, HDFS_SECONDARY_NAMENODE_HOST, HDFS_SECONDARY_NAMENODE_CONFIG, HDFS_DATANODE_HOSTS, HDFS_DATANODE_CONFIG, HDFS_GATEWAY_HOSTS, HDFS_GATEWAY_CONFIG)


def deploy_hdfs(module, hdfs_service_name, hdfs_config, hdfs_nn_service_name, hdfs_nn_host, hdfs_nn_config,
                hdfs_snn_host, hdfs_snn_config, hdfs_dn_hosts, hdfs_dn_config, hdfs_gw_hosts, hdfs_gw_config):
    changed = False
    cluster = find_cluster(module, api, name)

    # Deploys HDFS - NN, DNs, SNN, gateways.
    # This does not yet support HA yet.
    hdfs_service = cluster.create_service(hdfs_service_name, "HDFS")
    hdfs_service.update_config(hdfs_config)

    nn_role_group = hdfs_service.get_role_config_group("{0}-NAMENODE-BASE".format(hdfs_service_name))
    nn_role_group.update_config(hdfs_nn_config)
    nn_service_pattern = "{0}-" + hdfs_nn_service_name
    hdfs_service.create_role(nn_service_pattern.format(hdfs_service_name), "NAMENODE", hdfs_nn_host)

    snn_role_group = hdfs_service.get_role_config_group("{0}-SECONDARYNAMENODE-BASE".format(hdfs_service_name))
    snn_role_group.update_config(hdfs_snn_config)
    hdfs_service.create_role("{0}-snn".format(hdfs_service_name), "SECONDARYNAMENODE", hdfs_snn_host)

    dn_role_group = hdfs_service.get_role_config_group("{0}-DATANODE-BASE".format(hdfs_service_name))
    dn_role_group.update_config(hdfs_dn_config)

    gw_role_group = hdfs_service.get_role_config_group("{0}-GATEWAY-BASE".format(hdfs_service_name))
    gw_role_group.update_config(hdfs_gw_config)

    datanode = 0
    for host in hdfs_dn_hosts:
        datanode += 1
        hdfs_service.create_role("{0}-dn-".format(hdfs_service_name) + str(datanode), "DATANODE", host)

    gateway = 0
    for host in hdfs_gw_hosts:
        gateway += 1
        hdfs_service.create_role("{0}-gw-".format(hdfs_service_name) + str(gateway), "GATEWAY", host)


# Initializes HDFS - format the file system
def init_hdfs(hdfs_service, hdfs_name, timeout):
    cmd = hdfs_service.format_hdfs("{0}-nn".format(hdfs_name))[0]
    if not cmd.wait(timeout).success:
        print "WARNING: Failed to format HDFS, attempting to continue with the setup"


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
        cluster_hosts=dict(type='str', default='locahots'),
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
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_hdfs_config(cm_host, cluster_hosts)
    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        try:
        hdfs_service = deploy_hdfs(CLUSTER, HDFS_SERVICE_NAME, HDFS_SERVICE_CONFIG, HDFS_NAMENODE_SERVICE_NAME,
                                   HDFS_NAMENODE_HOST, HDFS_NAMENODE_CONFIG, HDFS_SECONDARY_NAMENODE_HOST,
                                   HDFS_SECONDARY_NAMENODE_CONFIG, HDFS_DATANODE_HOSTS, HDFS_DATANODE_CONFIG,
                                   HDFS_GATEWAY_HOSTS, HDFS_GATEWAY_CONFIG)
        except: ApiException as e:
            module.fail_json(msg='Failed to deploy hdfs.\nError is %s' % e)

    try:
        init_hdfs(hdfs_service, hdfs_name, timeout)

    except ApiException as e:
        module.fail_json(msg='Failed to init hdfs.\nError is %s' % e)


# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
