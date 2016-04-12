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


def build_accumulo_config(CLUSTER_HOSTS, MAPRED_SERVICE_NAME, ZOOKEEPER_SERVICE_NAME):
    ### Accumulo ###
    ACCUMULO_SERVICE_NAME = "accumulo"
    ACCUMULO_SERVICE_CONFIG = {
        'accumulo_instance_name': "accumulo",
        'mapreduce_service': MAPRED_SERVICE_NAME,
        'zookeeper_service': ZOOKEEPER_SERVICE_NAME,
    }
    ACCUMULO_MASTER_HOSTS = [CLUSTER_HOSTS[0]]
    ACCUMULO_MASTER_CONFIG = {}
    ACCUMULO_TRACER_HOSTS = list(CLUSTER_HOSTS)
    ACCUMULO_TRACER_CONFIG = {}
    ACCUMULO_TSERVER_HOSTS = list(CLUSTER_HOSTS)
    ACCUMULO_TSERVER_CONFIG = {}
    ACCUMULO_LOGGER_HOSTS = list(CLUSTER_HOSTS)
    ACCUMULO_LOGGER_CONFIG = {}
    ACCUMULO_GATEWAY_HOSTS = list(CLUSTER_HOSTS)
    ACCUMULO_GATEWAY_CONFIG = {}
    ACCUMULO_MONITOR_HOST = CLUSTER_HOSTS[0]
    ACCUMULO_MONITOR_CONFIG = {}
    ACCUMULO_GC_HOST = CLUSTER_HOSTS[0]
    ACCUMULO_GC_CONFIG = {}

    return (ACCUMULO_SERVICE_NAME, ACCUMULO_SERVICE_CONFIG, ACCUMULO_MASTER_HOSTS, ACCUMULO_MASTER_CONFIG, ACCUMULO_TRACER_HOSTS, ACCUMULO_TRACER_CONFIG, ACCUMULO_TSERVER_HOSTS, ACCUMULO_TSERVER_CONFIG, ACCUMULO_LOGGER_HOSTS, ACCUMULO_LOGGER_CONFIG, ACCUMULO_GATEWAY_HOSTS, ACCUMULO_GATEWAY_CONFIG, ACCUMULO_MONITOR_HOST, ACCUMULO_MONITOR_CONFIG, ACCUMULO_GC_HOST, ACCUMULO_GC_CONFIG)

def deploy_accumulo(module, api, name, service_name, service_config, master_hosts, master_config, tracer_hosts, tracer_config, tserver_hosts, tserver_config, logger_hosts, logger_config, monitor_host, monitor_config, gc_host, gc_config, gw_hosts, gw_config):

    changed = False
    cluster = find_cluster(module, api, name)

    accumulo = cluster.create_service(service_name, "csd_accumulo")
    accumulo.update_config(service_config)

    accumulo_masters_group = accumulo.get_role_config_group("{0}-MASTER-BASE".format(service_name))
    accumulo_masters_group.update_config(master_config)

    accumulo_tracers_group = accumulo.get_role_config_group("{0}-TRACER-BASE".format(service_name))
    accumulo_tracers_group.update_config(tracer_config)

    accumulo_tservers_group = accumulo.get_role_config_group("{0}-TSERVER-BASE".format(service_name))
    accumulo_tservers_group.update_config(tserver_config)

    accumulo_loggers_group = accumulo.get_role_config_group("{0}-LOGGER-BASE".format(service_name))
    accumulo_loggers_group.update_config(logger_config)

    accumulo_gateways_group = accumulo.get_role_config_group("{0}-GATEWAY-BASE".format(service_name))
    accumulo_gateways_group.update_config(gw_config)

    accumulo_monitor_group = accumulo.get_role_config_group("{0}-MONITOR-BASE".format(service_name))
    accumulo_monitor_group.update_config(monitor_config)

    accumulo_gc_group = accumulo.get_role_config_group("{0}-GC-BASE".format(service_name))
    accumulo_gc_group.update_config(gc_config)

    # Create Accumulo Masters
    count = 0
    for host in master_hosts:
        count += 1
        accumulo.create_role("{0}-master".format(service_name) + str(count), "csd_accumulo_master", host)

    # Create Accumulo Loggers
    count = 0
    for host in logger_hosts:
        count += 1
        accumulo.create_role("{0}-logger".format(service_name) + str(count), "csd_accumulo_logger", host)

    # Create Accumulo TServers
    count = 0
    for host in tserver_hosts:
        count += 1
        accumulo.create_role("{0}-tserver".format(service_name) + str(count), "csd_accumulo_tserver", host)

    # Create Accumulo Gateways
    count = 0
    for host in gw_hosts:
        count += 1
        accumulo.create_role("{0}-gateway".format(service_name) + str(count), "GATEWAY", host)

    # Create Accumulo Tracers
    count = 0
    for host in tracer_hosts:
        count += 1
        accumulo.create_role("{0}-tracer".format(service_name) + str(count), "csd_accumulo_tracer", host)

    # Create Accumulo GC
    accumulo.create_role("{0}-gc".format(service_name), "csd_accumulo_gc", gc_host)

    # Create Accumulo Monitor
    accumulo.create_role("{0}-monitor".format(service_name), "csd_accumulo_monitor", monitor_host)

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return accumulo_service


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
        mapred_service_name=dict(type='str', default='MAPRED'),
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
    mapred_service_name = module.params.get('mapred_service_name')
    zookeeper_service_name = module.params.get('zookeeper_service_name')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_accumulo_config(cluster_hosts, mapred_service_name, zookeeper_service_name)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)

    else:
        try:
            accumulo_service = deploy_flume(ACCUMULO_SERVICE_NAME, ACCUMULO_SERVICE_CONFIG, ACCUMULO_MASTER_HOSTS, ACCUMULO_MASTER_CONFIG, ACCUMULO_TRACER_HOSTS, ACCUMULO_TRACER_CONFIG, ACCUMULO_TSERVER_HOSTS, ACCUMULO_TSERVER_CONFIG, ACCUMULO_LOGGER_HOSTS, ACCUMULO_LOGGER_CONFIG, ACCUMULO_MONITOR_HOST, ACCUMULO_MONITOR_CONFIG, ACCUMULO_GC_HOST, ACCUMULO_GC_CONFIG, ACCUMULO_GATEWAY_HOSTS, ACCUMULO_GATEWAY_CONFIG)

        except: ApiException as e:
            module.fail_json(msg='Failed to deploy accumulo.\nError is %s' % e)

    return accumulo_service

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
