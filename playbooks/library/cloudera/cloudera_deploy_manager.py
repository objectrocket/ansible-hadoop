#!/usr/bin/python
# This file is part of Ansible
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
module: cloudera_deploy_manager
short_description: Setup Cloudera Management Services
description:
     - Setup Cloudera Management services using Cloudera Manager
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
  hosts:
    description:
      - Comma separated hostnames of the nodes forming the cluster
    default: null
  service_host:
    description:
      - host where management services will run
  service_pass:
    description:
      - password for db access for management services
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
        hosts: localhost
        service_host: cm_host
        service_pass: temp
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

def build_amon_config(service_host, service_pass)
    # The values change every time the cloudera-scm-server-db process is restarted.
    # TBD will CM have to be reconfigured each time?
    AMON_ROLENAME = "ACTIVITYMONITOR"
    AMON_ROLE_CONFIG = {
        'firehose_database_host': service_host + ':3306',
        'firehose_database_user': 'amon',
        'firehose_database_password': service_pass,
        'firehose_database_type': 'mysql',
        'firehose_database_name': 'amon',
        'firehose_heapsize': '215964392',
    }
    return (AMON_ROLENAME, AMON_ROLE_CONFIG)


def build_mgmt_config()
    MGMT_SERVICENAME = "MGMT"
    MGMT_SERVICE_CONFIG = {
        'zookeeper_datadir_autocreate': 'true',
    }
    MGMT_ROLE_CONFIG = {
        'quorumPort': 2888,
    }
    return (MGMT_SERVICENAME, MGMT_SERVICE_CONFIG, MGMT_ROLE_CONFIG)

def build_apub_config()
    APUB_ROLENAME = "ALERTPUBLISHER"
    APUB_ROLE_CONFIG = {}

    return (APUB_ROLENAME, APUB_ROLE_CONFIG)

def build_eserv_config()
    ESERV_ROLENAME = "EVENTSERVER"
    ESERV_ROLE_CONFIG = {
        'event_server_heapsize': '215964392'
    }
    return (ESERV_ROLENAME, ESERV_ROLE_CONFIG)

def build_hmon_config()
    HMON_ROLENAME = "HOSTMONITOR"
    HMON_ROLE_CONFIG = {}

    return (HMON_ROLENAME, HMON_ROLE_CONFIG)


def build_smon_config()
    SMON_ROLENAME = "SERVICEMONITOR"
    SMON_ROLE_CONFIG = {}

    return (SMON_ROLENAME, SMON_ROLE_CONFIG)

def build_nav_config(service_host, service_pass)
    NAV_ROLENAME = "NAVIGATOR"
    NAV_ROLE_CONFIG = {
        'navigator_database_host': service_host + ":3306",
        'navigator_database_user': "nav",
        'navigator_database_password': service_pass,
        'navigator_database_type': 'mysql',
        'navigator_database_name': 'nav',
        'navigator_heapsize': '215964392',
    }
    return (NAV_ROLENAME, NAV_ROLE_CONFIG)


def build_navms_config()
    NAVMS_ROLENAME = "NAVIGATORMETADATASERVER"
    NAVMS_ROLE_CONFIG = {
    }

    return (NAVMS_ROLENAME, NAVMS_ROLE_CONFIG)

def build_rman_config(service_host, service_pass)
    RMAN_ROLENAME = "REPORTMANAGER"
    RMAN_ROLE_CONFIG = {
        'headlamp_database_host': service_host + ":3306",
        'headlamp_database_user': 'rman',
        'headlamp_database_password': service_pass,
        'headlamp_database_type': 'mysql',
        'headlamp_database_name': 'rman',
        'headlamp_heapsize': '215964392',
    }

    return (RMAN_ROLENAME, RMAN_ROLE_CONFIG)

def build_configs(service_host, service_pass)
    build_amon_config(service_host, service_pass)
    build_mgmt_config()
    build_apub_config()
    build_eserv_config()
    build_hmon_config()
    build_smon_config()
    build_nav_config(service_host, service_pass)
    build_navms_config()
    build_rman_config(service_host, service_pass)


def deploy_management(manager, mgmt_servicename, mgmt_service_conf, mgmt_role_conf, amon_role_name, amon_role_conf, apub_role_name, apub_role_conf, eserv_role_name, eserv_role_conf, hmon_role_name, hmon_role_conf, smon_role_name, smon_role_conf, nav_role_name, nav_role_conf, navms_role_name, navms_role_conf, rman_role_name, rman_role_conf):
   mgmt = manager.create_mgmt_service(ApiServiceSetupInfo())

   # create roles. Note that host id may be different from host name (especially in CM 5). Look it it up in /api/v5/hosts
   mgmt.create_role(amon_role_name + "-1", "ACTIVITYMONITOR", cm_host)
   mgmt.create_role(apub_role_name + "-1", "ALERTPUBLISHER", cm_host)
   mgmt.create_role(eserv_role_name + "-1", "EVENTSERVER", cm_host)
   mgmt.create_role(hmon_role_name + "-1", "HOSTMONITOR", cm_host)
   mgmt.create_role(smon_role_name + "-1", "SERVICEMONITOR", cm_host)
   mgmt.create_role(nav_role_name + "-1", "NAVIGATOR", cm_host)
   mgmt.create_role(navms_role_name + "-1", "NAVIGATORMETADATASERVER", cm_host)
   mgmt.create_role(rman_role_name + "-1", "REPORTSMANAGER", cm_host)

   # now configure each role
   for group in mgmt.get_all_role_config_groups():
       if group.roleType == "ACTIVITYMONITOR":
           group.update_config(amon_role_conf)
       elif group.roleType == "ALERTPUBLISHER":
           group.update_config(apub_role_conf)
       elif group.roleType == "EVENTSERVER":
           group.update_config(eserv_role_conf)
       elif group.roleType == "HOSTMONITOR":
           group.update_config(hmon_role_conf)
       elif group.roleType == "SERVICEMONITOR":
           group.update_config(smon_role_conf)
       elif group.roleType == "NAVIGATOR":
           group.update_config(nav_role_conf)
       elif group.roleType == "NAVIGATORMETADATASERVER":
           group.update_config(navms_role_conf)
       elif group.roleType == "REPORTSMANAGER":
           group.update_config(rman_role_conf)

   # now start the management service
   mgmt.start().wait()

   return mgmt

def main():
    argument_spec = dict(
        name=dict(type='str'),
        fullVersion=dict(type='str', default='5.6.0'),
        admin_password=dict(type='str', default='admin'),
        state=dict(default='present', choices=['present', 'absent']),
        cm_host=dict(type='str', default='localhost'),
        hosts=dict(type='str', default=''),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(default=30),
        service_host=dict(type='str', default='localhost'),
        service_password=dict(type='str', default='temp')
        )

    module = AnsibleModule(
        argument_spec=argument_spec
    )

    name = module.params.get('name')
    fullVersion = module.params.get('fullVersion')
    admin_password = module.params.get('admin_password')
    state = module.params.get('state')
    cm_host = module.params.get('cm_host')
    hosts = module.params.get('hosts')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))
    service_host = module.params.get('service_host')
    service_pass = module.params.get('service_pass')

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    build_configs(service_host, service_pass)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()


    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "present":
        deploy_management(module, API, name, MANAGER, MGMT_SERVICENAME, MGMT_SERVICE_CONFIG, MGMT_ROLE_CONFIG, AMON_ROLENAME,
                          AMON_ROLE_CONFIG, APUB_ROLENAME, APUB_ROLE_CONFIG, ESERV_ROLENAME, ESERV_ROLE_CONFIG,
                          HMON_ROLENAME, HMON_ROLE_CONFIG, SMON_ROLENAME, SMON_ROLE_CONFIG, NAV_ROLENAME,
                          NAV_ROLE_CONFIG, NAVMS_ROLENAME, NAVMS_ROLE_CONFIG, RMAN_ROLENAME, RMAN_ROLE_CONFIG)
        print "Deployed CM management service " + MGMT_SERVICENAME + " to run on " + CM_HOST

    else:
        delete_cluster(module, API, name, fullVersion, hosts, cm_host)

# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
