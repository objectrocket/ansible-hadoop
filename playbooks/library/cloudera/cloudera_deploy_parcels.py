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
module: cloudera_deploy_parcels
short_description: deploy parcels / delete a Cloudera cluster
description:
     - deploy parcels / deletes a Cloudera cluster using Cloudera Manager.
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
  state:
    description:
      - Indicate desired state of the resource
    choices:
      - present
      - absent
    default: present
author:
  - David Grier

'''

EXAMPLES = '''
- name: deploy parcels
  gather_facts: False
  hosts: local
  connection: local
  tasks:
    - name: Cloudera cluster create request
      local_action:
        module: cloudera_deploy_parcels
        name: my-test-cluster
        fullVersion: 5.6.0
        admin_password: admin
        cm_host: localhost
        hosts: localhost
        latest_parcel_url: 'http://archive.cloudera.com/cdh5/parcels/latest/'
        state: present
      register: parcels

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

def get_parcels(LATEST_PARCEL_URL):

    PARCEL_VERSION = CONFIG.get("CDH", "cdh.parcel.version")
    if PARCEL_VERSION.lower() == "latest":
        # Get list of parcels from the cloudera repo to see what the latest version is. Then to parse:
        # find first item that starts with CDH-
        # strip off leading CDH-
        # strip off everything after the last - in that item, including the -'
        PARCEL_PREFIX = 'CDH-'
        dir_list = urllib2.urlopen(LATEST_PARCEL_URL).read()
        dir_list = dir_list[dir_list.index(PARCEL_PREFIX) + len(PARCEL_PREFIX):]
        dir_list = dir_list[:dir_list.index('"')]
        PARCEL_VERSION = dir_list[:dir_list.rfind('-')]
    PARCELS = [
        {'name': "CDH", 'version': PARCEL_VERSION},
        # { 'name' : "CDH", 'version' : "5.0.1-1.cdh5.0.1.p0.47" },
        # { 'name' : "ACCUMULO", 'version' : "1.4.3-cdh4.3.0-beta-3"}
    ]
    return PARCELS

def deploy_parcels(module, api, name, hosts, cm_host, parcels):

    changed = False
    cluster = find_cluster(module, api, name)

    if not cluster:
        try:
            for parcel in parcels:
                p = cluster.get_parcel(parcel['name'], parcel['version'])
                p.start_download()
                while True:
                    p = cluster.get_parcel(parcel['name'], parcel['version'])
                    if p.stage == "DOWNLOADED":
                        break
                    if p.state.errors:
                        raise Exception(str(p.state.errors))
                    print "Downloading %s: %s / %s" % (parcel['name'], p.state.progress, p.state.totalProgress)
                    time.sleep(15)
                print "Downloaded %s" % (parcel['name'])
                p.start_distribution()
                while True:
                    p = cluster.get_parcel(parcel['name'], parcel['version'])
                    if p.stage == "DISTRIBUTED":
                        break
                    if p.state.errors:
                        raise Exception(str(p.state.errors))
                    print "Distributing %s: %s / %s" % (parcel['name'], p.state.progress, p.state.totalProgress)
                    time.sleep(15)
                print "Distributed %s" % (parcel['name'])
                p.activate()

            all_hosts = set(hosts.split(','))
            all_hosts.add(cm_host)
            cluster.add_hosts(all_hosts)
            changed = True
            time.sleep(10)
        except ApiException as e:
            module.fail_json(msg='Failed to build cluster.\nError is %s' % e)

    result = dict(changed=changed, cluster=cluster.name)
    module.exit_json(**result)

    return parcels

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
        hosts=dict(type='str', default=''),
        latest_parcel_url=dict(type='str', default='http://archive.cloudera.com/cdh5/parcels/latest/')
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
    hosts = module.params.get('hosts')
    latest_parcel_url = module.params.get('latest_parcel_url')
    auto_prov = module.params.get('auto_prov')
    wait = module.params.get('wait')
    wait_timeout = int(module.params.get('wait_timeout'))

    if not name:
        module.fail_json(msg='The cluster name is required for this module')

    cfg = ConfigParser.SafeConfigParser()

    get_parcels(latest_parcel_url)

    try:
        API = ApiResource(cm_host, version=fullVersion[0], username="admin", password=admin_password)
        MANAGER = API.get_cloudera_manager()

    except ApiException as e:
        module.fail_json(msg='Failed to connect to Cloudera Manager.\nError is %s' % e)

    if state == "absent":
        delete_cluster(module, API, name)
    else:
        deploy_parcels(module, API, name, hosts, cm_host, PARCELS)

    return cluster
# import module snippets
from ansible.module_utils.basic import *

### invoke the module
main()
