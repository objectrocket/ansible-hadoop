[![Build Status](http://104.130.29.12/buildStatus/icon?job=ansible-hadoop)](http://104.130.29.12/job/ansible-hadoop/)

ansible-hadoop
---------
These Ansible playbooks will build a Hadoop cluster.

You can pre-build a Rackspace cloud environment or run the playbooks against an existing environment.

---

## [Installation] (id:installation)

See [INSTALL-ENV.md](../master/INSTALL-ENV.md) for installation and build instructions.


## [Requirements] (id:requirements)

- Ansible == 2.1.3.0 (2.2 is not supported at the moment)

- Expects RHEL/CentOS 6/7 or Ubuntu 14 hosts.

- Building the Rackspace Cloud environment requires the `pyrax` Python module: [pyrax link](https://github.com/rackspace/pyrax).


## [Features] (id:features)

- It installs Hortonworks Data Platform using [Ambari Blueprints](https://cwiki.apache.org/confluence/display/AMBARI/Blueprints).

- It supports static inventory if the environment is pre-built (`inventory/static` file).

- The data drives can be customized and can be put on top of Cloud Block Storage (partitioning is automatic).

- If there are 2 or 3 masternodes, it will also enable HA NameNode.

- Memory settings are scaled with the hardware configuration of the nodes.


## [Inventory] (id:inventory)

- The cloud environment requires the standard `pyrax` credentials file that looks like this:
  ````
  [rackspace_cloud]
  username = my_username
  api_key = 01234567890abcdef
  ````
  
  This file will be referenced in `playbooks/group_vars/all` (the `rax_credentials_file` variable).

  By default, the file is expected to be: `~/.raxpub`.

- When provisioning HDP on existing infrastructure edit `inventory/static` and add the nodes.


## [Configuration files] (id:configuration)

To customize, change the variables under `playbooks/group_vars` folder:

1. **`playbooks/group_vars/all`**: contains global cluster and cloud settings
1. **`playbooks/group_vars/master-nodes`**: master-nodes configuration
1. **`playbooks/group_vars/slave-nodes`**: slave-nodes configuration
1. **`playbooks/group_vars/edge-nodes`**: edge-nodes configuration

For a one-node cluster, set `cloud_nodes_count` in master-nodes to 1 and `cloud_nodes_count` in slave-nodes to 0.


## [Scripts] (id:scripts)

###`provision_rax.sh`

To provision a cloud environment, run the `provision_rax.sh` script after you've customized the variables under `playbooks/group_vars`:
````
bash provision_rax.sh
````

Continue with the HDP deployment steps here :
[HDP Install](../master/INSTALL-HDP.md)
