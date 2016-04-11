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


def build_search_config(CLUSTER_HOSTS, HDFS_SERVICE_NAME, ZOOKEEPER_SERVICE_NAME)
    SEARCH_SERVICE_NAME = "SEARCH"
    SEARCH_SERVICE_CONFIG = {
        'hdfs_service': HDFS_SERVICE_NAME,
        'zookeeper_service': ZOOKEEPER_SERVICE_NAME,
    }
    SEARCH_SOLR_HOST = CLUSTER_HOSTS[0]
    SEARCH_SOLR_CONFIG = {}
    SEARCH_GW_HOSTS = list(CLUSTER_HOSTS)
    SEARCH_GW_CONFIG = {}

    return (SEARCH_SERVICE_NAME, SEARCH_SERVICE_CONFIG, SEARCH_SOLR_HOST, SEARCH_SOLR_CONFIG, SEARCH_GW_HOSTS, SEARCH_GW_CONFIG)


def deploy_search(module, api, search_service_name, search_service_config, search_solr_host, search_solr_config,
                search_gw_hosts, search_gw_config):

  changed = False

  search_service = cluster.create_service(search_service_name, "SOLR")
  search_service.update_config(search_service_config)

  solr = search_service.get_role_config_group("{0}-SOLR_SERVER-BASE".format(search_service_name))
  solr.update_config(search_solr_config)
  search_service.create_role("{0}-solr".format(search_service_name), "SOLR_SERVER", search_solr_host)

  gw = search_service.get_role_config_group("{0}-GATEWAY-BASE".format(search_service_name))
  gw.update_config(search_gw_config)

  gateway = 0
  for host in search_gw_hosts:
      gateway += 1
      search_service.create_role("{0}-gw-".format(search_service_name) + str(gateway), "GATEWAY", host)

  # solrctl init
  zk_ensemble = ZOOKEEPER_HOSTS[0] + ":2181," + ZOOKEEPER_HOSTS[1] + ":2181," + ZOOKEEPER_HOSTS[2] + ":2181/solr"
  shell_command = ["export SOLR_ZK_ENSEMBLE=" + zk_ensemble + "; solrctl init"]
  solrctl_init_output = Popen(shell_command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                              close_fds=True).stdout.read()


  result = dict(changed=changed, cluster=cluster.name)
  module.exit_json(**result)

  return search_service


def delete_cluster(module, api,  name):

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
        zookeeper_service_name=dict(type='str', default='ZOOKEEPER'),
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

    build_search_config(cluster_hosts, hdfs_service_name, zookeeper_service_name)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)

    else:
        try:
            search_service = deploy_search(module, API, name, SEARCH_SERVICE_NAME, SEARCH_SERVICE_CONFIG, SEARCH_SOLR_HOST,
                                           SEARCH_SOLR_CONFIG, SEARCH_GW_HOSTS, SEARCH_GW_CONFIG)
        except: ApiException as e:
            module.fail_json(msg='Failed to deploy hbase.\nError is %s' % e)

    return search_service

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
