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
module: cloudera_deploy_hive
short_description: deploy hive / delete a Cloudera cluster
description:
     - deploy hive / deletes a Cloudera cluster using Cloudera Manager.
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


def build_hive_config(CM_HOST, HIVE_METASTORE_PASSWORD, MAPRED_SERVICE_NAME, ZOOKEEPER_SERVICE_NAME, YARN_SERVICE_NAME):
    HIVE_SERVICE_NAME = "HIVE"
    HIVE_SERVICE_CONFIG = {
        'hive_metastore_database_host': CM_HOST,
        'hive_metastore_database_name': 'metastore',
        'hive_metastore_database_password': HIVE_METASTORE_PASSWORD,
        'hive_metastore_database_port': 3306,
        'hive_metastore_database_type': 'mysql',
        'mapreduce_yarn_service': MAPRED_SERVICE_NAME,
        'zookeeper_service': ZOOKEEPER_SERVICE_NAME,
        'mapreduce_yarn_service': YARN_SERVICE_NAME,
    }
    HIVE_HMS_HOST = CLUSTER_HOSTS[0]
    HIVE_HMS_CONFIG = {
        'hive_metastore_java_heapsize': 85306784,
    }
    HIVE_HS2_HOST = CLUSTER_HOSTS[0]
    HIVE_HS2_CONFIG = {}
    HIVE_WHC_HOST = CLUSTER_HOSTS[0]
    HIVE_WHC_CONFIG = {}
    HIVE_GW_HOSTS = list(CLUSTER_HOSTS)
    HIVE_GW_CONFIG = {}

    return (HIVE_SERVICE_NAME, HIVE_SERVICE_CONFIG, HIVE_HMS_HOST, HIVE_HMS_CONFIG, HIVE_HS2_HOST, HIVE_HS2_CONFIG, HIVE_WHC_HOST, HIVE_WHC_CONFIG, HIVE_GW_HOSTS, HIVE_GW_CONFIG)


  def deploy_hive(cluster, hive_service_name, hive_service_config, hive_hms_host, hive_hms_config, hive_hs2_host,
                  hive_hs2_config, hive_whc_host, hive_whc_config, hive_gw_hosts, hive_gw_config):

    changed = False
    cluster = find_cluster(module, api, name)

    hive_service = cluster.create_service(hive_service_name, "HIVE")
    hive_service.update_config(hive_service_config)

    hms = hive_service.get_role_config_group("{0}-HIVEMETASTORE-BASE".format(hive_service_name))
    hms.update_config(hive_hms_config)
    hive_service.create_role("{0}-hms".format(hive_service_name), "HIVEMETASTORE", hive_hms_host)

    hs2 = hive_service.get_role_config_group("{0}-HIVESERVER2-BASE".format(hive_service_name))
    hs2.update_config(hive_hs2_config)
    hive_service.create_role("{0}-hs2".format(hive_service_name), "HIVESERVER2", hive_hs2_host)

    whc = hive_service.get_role_config_group("{0}-WEBHCAT-BASE".format(hive_service_name))
    whc.update_config(hive_whc_config)
    hive_service.create_role("{0}-whc".format(hive_service_name), "WEBHCAT", hive_whc_host)

    gw = hive_service.get_role_config_group("{0}-GATEWAY-BASE".format(hive_service_name))
    gw.update_config(hive_gw_config)

    gateway = 0
    for host in hive_gw_hosts:
        gateway += 1
        hive_service.create_role("{0}-gw-".format(hive_service_name) + str(gateway), "GATEWAY", host)

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return hive_service



def init_hive(hive_service):
    hive_service.create_hive_metastore_database()
    hive_service.create_hive_metastore_tables()
    hive_service.create_hive_warehouse()

    #don't think that the create_hive_userdir call is needed as the create_hive_warehouse already creates it
    #hive_service.create_hive_userdir()

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
        hive_metastore_password=dict(type='str', default='temp'),
        mapred_service_name=dict(type='str', default='MAPRED'),
        zookeeper_service_name=dict(type='str', default='ZOOKEEPER'),
        yarn_service_name=dict(type='str', default='YARN')
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
    hive_metastore_password = module.params.get('hive_metastore_password')
    mapred_service_name = module.params.get('mapred_service_name')
    zookeeper_service_name = module.params.get('zookeeper_service_name')
    yarn_service_name = module.params.get('yarn_service_name')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_hive_config(cm_host, hive_metastore_password, mapred_service_name, zookeeper_service_name, yarn_service_name)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        try:
            hive_service = deploy_hive(module, API, name, HIVE_SERVICE_NAME, HIVE_SERVICE_CONFIG, HIVE_HMS_HOST, HIVE_HMS_CONFIG,
                                       HIVE_HS2_HOST, HIVE_HS2_CONFIG, HIVE_WHC_HOST, HIVE_WHC_CONFIG, HIVE_GW_HOSTS,
                                       HIVE_GW_CONFIG)

        except: ApiException as e:
            module.fail_json(msg='Failed to deploy hive.\nError is %s' % e)

        try:
            init_hive(hive_service)

        except ApiException as e:
            module.fail_json(msg='Failed to init hive.\nError is %s' % e)

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
