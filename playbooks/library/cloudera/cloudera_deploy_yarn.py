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
module: cloudera_deploy_yarn
short_description: deploy yarn / delete a Cloudera cluster
description:
     - deploy yarn / deletes a Cloudera cluster using Cloudera Manager.
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


def build_yarn_config(HDFS_SERVICE_NAME, CLUSTER_HOSTS, HADOOP_DATA_DIR_PREFIX):
    ### YARN ###
    YARN_SERVICE_NAME = "YARN"
    YARN_SERVICE_CONFIG = {
        'hdfs_service': HDFS_SERVICE_NAME,
    }
    YARN_RM_HOST = CLUSTER_HOSTS[0]
    YARN_RM_CONFIG = {}
    YARN_JHS_HOST = CLUSTER_HOSTS[0]
    YARN_JHS_CONFIG = {}
    YARN_NM_HOSTS = list(CLUSTER_HOSTS)
    YARN_NM_CONFIG = {
        # 'yarn_nodemanager_local_dirs': '/data01/hadoop/yarn/nm',
        'yarn_nodemanager_local_dirs': HADOOP_DATA_DIR_PREFIX + '/yarn/nm',
    }
    YARN_GW_HOSTS = list(CLUSTER_HOSTS)
    YARN_GW_CONFIG = {
        'mapred_submit_replication': min(3, len(YARN_GW_HOSTS))
    }

    return (YARN_SERVICE_NAME, YARN_SERVICE_CONFIG, YARN_RM_HOST, YARN_RM_CONFIG, YARN_JHS_HOST, YARN_JHS_CONFIG, YARN_NM_HOSTS, YARN_NM_CONFIG, YARN_GW_HOSTS, YARN_GW_CONFIG)

def deploy_yarn(module, api, name, yarn_service_name, yarn_service_config, yarn_rm_host, yarn_rm_config, yarn_jhs_host, yarn_jhs_config, yarn_nm_hosts, yarn_nm_config, yarn_gw_hosts, yarn_gw_config):

    changed = False
    cluster = find_cluster(module, api, name)

    yarn_service = cluster.create_service(yarn_service_name, "YARN")
    yarn_service.update_config(yarn_service_config)

    rm = yarn_service.get_role_config_group("{0}-RESOURCEMANAGER-BASE".format(yarn_service_name))
    rm.update_config(yarn_rm_config)
    yarn_service.create_role("{0}-rm".format(yarn_service_name), "RESOURCEMANAGER", yarn_rm_host)

    jhs = yarn_service.get_role_config_group("{0}-JOBHISTORY-BASE".format(yarn_service_name))
    jhs.update_config(yarn_jhs_config)
    yarn_service.create_role("{0}-jhs".format(yarn_service_name), "JOBHISTORY", yarn_jhs_host)

    nm = yarn_service.get_role_config_group("{0}-NODEMANAGER-BASE".format(yarn_service_name))
    nm.update_config(yarn_nm_config)

    nodemanager = 0
    for host in yarn_nm_hosts:
        nodemanager += 1
        yarn_service.create_role("{0}-nm-".format(yarn_service_name) + str(nodemanager), "NODEMANAGER", host)

    gw = yarn_service.get_role_config_group("{0}-GATEWAY-BASE".format(yarn_service_name))
    gw.update_config(yarn_gw_config)

    gateway = 0
    for host in yarn_gw_hosts:
        gateway += 1
        yarn_service.create_role("{0}-gw-".format(yarn_service_name) + str(gateway), "GATEWAY", host)

    # TODO need api version 6 for these, but I think they are done automatically?
    # yarn_service.create_yarn_job_history_dir()
    # yarn_service.create_yarn_node_manager_remote_app_log_dir()

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return yarn_service


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
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_yarn_config(hdfs_service_name, cluster_hosts, hadoop_data_dir_prefix)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        try:
            yarn_service = deploy_yarn(module, API, name, YARN_SERVICE_NAME, YARN_SERVICE_CONFIG, YARN_RM_HOST, YARN_RM_CONFIG,
                                       YARN_JHS_HOST, YARN_JHS_CONFIG, YARN_NM_HOSTS, YARN_NM_CONFIG, YARN_GW_HOSTS,
                                       YARN_GW_CONFIG)

        except: ApiException as e:
            module.fail_json(msg='Failed to deploy yarn.\nError is %s' % e)

    return yarn_service


# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
