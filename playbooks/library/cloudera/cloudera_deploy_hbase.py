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
module: cloudera_deploy_hbase
short_description: deploy hbase / delete a Cloudera cluster
description:
     - deploy hbase / deletes a Cloudera cluster using Cloudera Manager.
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


def build_hbase_config(HDFS_SERVICE_NAME, ZOOKEEPER_SERVICE_NAME, CLUSTER_HOSTS):
    ### HBase ###
    HBASE_SERVICE_NAME = "HBASE"
    HBASE_SERVICE_CONFIG = {
        'hdfs_service': HDFS_SERVICE_NAME,
        'zookeeper_service': ZOOKEEPER_SERVICE_NAME,
    }
    HBASE_HM_HOST = CLUSTER_HOSTS[0]
    HBASE_HM_CONFIG = {}
    HBASE_RS_HOSTS = list(CLUSTER_HOSTS)
    HBASE_RS_CONFIG = {
        'hbase_hregion_memstore_flush_size': 1024000000,
        'hbase_regionserver_handler_count': 10,
        'hbase_regionserver_java_heapsize': 2048000000,
        'hbase_regionserver_java_opts': '',
    }
    HBASE_THRIFTSERVER_SERVICE_NAME = "HBASETHRIFTSERVER"
    HBASE_THRIFTSERVER_HOST = CLUSTER_HOSTS[0]
    HBASE_THRIFTSERVER_CONFIG = {}
    HBASE_GW_HOSTS = list(CLUSTER_HOSTS)
    HBASE_GW_CONFIG = {}

    return (HBASE_SERVICE_NAME, HBASE_SERVICE_CONFIG, HBASE_HM_HOST, HBASE_HM_CONFIG, HBASE_RS_HOSTS, HBASE_RS_CONFIG, HBASE_THRIFTSERVER_SERVICE_NAME, HBASE_THRIFTSERVER_HOST, HBASE_THRIFTSERVER_CONFIG, HBASE_GW_HOSTS, HBASE_GW_CONFIG)


def deploy_hbase(module, api, name, hbase_service_name, hbase_service_config, hbase_hm_host, hbase_hm_config, hbase_rs_hosts, hbase_rs_config, hbase_thriftserver_service_name, hbase_thriftserver_host, hbase_thriftserver_config, hbase_gw_hosts, hbase_gw_config ):

    changed = False
    cluster = find_cluster(module, api, name)

    hbase_service = cluster.create_service(hbase_service_name, "HBASE")
    hbase_service.update_config(hbase_service_config)

    hm = hbase_service.get_role_config_group("{0}-MASTER-BASE".format(hbase_service_name))
    hm.update_config(hbase_hm_config)
    hbase_service.create_role("{0}-hm".format(hbase_service_name), "MASTER", hbase_hm_host)

    rs = hbase_service.get_role_config_group("{0}-REGIONSERVER-BASE".format(hbase_service_name))
    rs.update_config(hbase_rs_config)

    ts = hbase_service.get_role_config_group("{0}-HBASETHRIFTSERVER-BASE".format(hbase_service_name))
    ts.update_config(hbase_thriftserver_config)
    ts_name_pattern = "{0}-" + hbase_thriftserver_service_name
    hbase_service.create_role(ts_name_pattern.format(hbase_service_name), "HBASETHRIFTSERVER", hbase_thriftserver_host)

    gw = hbase_service.get_role_config_group("{0}-GATEWAY-BASE".format(hbase_service_name))
    gw.update_config(hbase_gw_config)

    regionserver = 0
    for host in hbase_rs_hosts:
        regionserver += 1
        hbase_service.create_role("{0}-rs-".format(hbase_service_name) + str(regionserver), "REGIONSERVER", host)

    gateway = 0
    for host in hbase_gw_hosts:
        gateway += 1
        hbase_service.create_role("{0}-gw-".format(hbase_service_name) + str(gateway), "GATEWAY", host)

    hbase_service.create_hbase_root()

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return hbase_service


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
        hdfs_service_name=dict(type='str', default=''),
        zookeeper_service_name=dict(type='str', default=''),
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
    zookeeper_service_name = module.params.get('zookeeper_service_name')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_hbase_config(hdfs_service_name, zookeeper_service_name, cluster_hosts)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        try:
            hbase_service = deploy_hbase(module, API, name, HBASE_SERVICE_NAME, HBASE_SERVICE_CONFIG, HBASE_HM_HOST, HBASE_HM_CONFIG,
                         HBASE_RS_HOSTS, HBASE_RS_CONFIG, HBASE_THRIFTSERVER_SERVICE_NAME, HBASE_THRIFTSERVER_HOST,
                         HBASE_THRIFTSERVER_CONFIG, HBASE_GW_HOSTS, HBASE_GW_CONFIG)

        except: ApiException as e:
            module.fail_json(msg='Failed to deploy hbase.\nError is %s' % e)

    return hbase_service

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
