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
module: cloudera_deploy_hue
short_description: deploy hue / delete a Cloudera cluster
description:
     - deploy hue / deletes a Cloudera cluster using Cloudera Manager.
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


def build_hue_config(CLUSTER_HOSTS, HIVE_SERVICE_NAME, HBASE_SERVICE_NAME, IMPALA_SERVICE_NAME, OOZIE_SERVICE_NAME, SQOOP_SERVICE_NAME, HDFS_SERVICE_NAME, HDFS_NAMENODE_SERVICE_NAME, HBASE_SERVICE_NAME, HBASE_THRIFTSERVER_SERVICE_NAME, SEARCH_SOLR_HOST):
    HUE_SERVICE_NAME = "HUE"
    HUE_SERVICE_CONFIG = {
        'hive_service': HIVE_SERVICE_NAME,
        'hbase_service': HBASE_SERVICE_NAME,
        'impala_service': IMPALA_SERVICE_NAME,
        'oozie_service': OOZIE_SERVICE_NAME,
        'sqoop_service': SQOOP_SERVICE_NAME,
        'hue_webhdfs': HDFS_SERVICE_NAME + "-" + HDFS_NAMENODE_SERVICE_NAME,
        'hue_hbase_thrift': HBASE_SERVICE_NAME + "-" + HBASE_THRIFTSERVER_SERVICE_NAME,
    }
    HUE_SERVER_HOST = CLUSTER_HOSTS[0]
    HUE_SERVER_CONFIG = {
        'hue_server_hue_safety_valve': '[search]\r\n## URL of the Solr Server\r\nsolr_url=http://' + SEARCH_SOLR_HOST + ':8983/solr',
    }
    HUE_KTR_HOST = CLUSTER_HOSTS[0]
    HUE_KTR_CONFIG = {}

    return (HUE_SERVICE_NAME, HUE_SERVICE_CONFIG, HUE_SERVER_HOST, HUE_SERVER_CONFIG, HUE_KTR_HOST, HUE_KTR_CONFIG)

def deploy_hue(module, api, name, flume_service_name, flume_service_config, flume_agent_hosts, flume_agent_config):

    changed = False
    cluster = find_cluster(module, api, name)

    flume_service = cluster.create_service(flume_service_name, "FLUME")
    flume_service.update_config(flume_service_config)

    gw = flume_service.get_role_config_group("{0}-AGENT-BASE".format(flume_service_name))
    gw.update_config(flume_agent_config)

    agent = 0
    for host in flume_agent_hosts:
        agent += 1
        flume_service.create_role("{0}-agent-".format(flume_service_name) + str(agent), "AGENT", host)


    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return flume_service


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
        hive_service_name=dict(type='str', default='HIVE'),
        impala_service_name=dict(type='str', default='IMPALA'),
        oozie_service_name=dict(type='str', default='OOZIE'),
        sqoop_service_name=dict(type='str', default='SQOOP'),
        hdfs_service_name=dict(type='str', default='HDFS'),
        hdfs_namenode_service_name=dict(type='str', default='nn'),
        hbase_service_name=dict(type='str', default='HBASE'),
        hbase_thriftserver_service_name=dict(type='str', default='HBASETHRIFTSERVER'),
        search_solr_host=dict(type='str', default=''),
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
    hive_service_name = module.params.get('hive_service_name')
    impala_service_name = module.params.get('impala_service_name')
    oozie_service_name = module.params.get('oozie_service_name')
    sqoop_service_name = module.params.get('sqoop_service_name')
    hdfs_service_name = module.params.get('hdfs_service_name')
    hdfs_namenode_service_name = module.params.get('hdfs_namenode_service_name')
    hbase_service_name = module.params.get('hbase_service_name')
    hbase_thriftserver_service_name = module.params.get('hbase_thriftserver_service_name')
    search_solr_host = module.params.get('search_solr_host')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))


    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_hue_config(cluster_hosts, hive_service_name, hbase_service_name, impala_service_name, oozie_service_name,
                     sqoop_service_name, hdfs_service_name, hdfs_namenode_service_name, hbase_service_name,
                     hbase_thriftserver_service_name, search_solr_host):


    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)

    else:
        try:
            hue_service = deploy_hue(CLUSTER, HUE_SERVICE_NAME, HUE_SERVICE_CONFIG, HUE_SERVER_HOST, HUE_SERVER_CONFIG,
                                     HUE_KTR_HOST, HUE_KTR_CONFIG)
        except: ApiException as e:
            module.fail_json(msg='Failed to deploy hue.\nError is %s' % e)

    return hue_service

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
