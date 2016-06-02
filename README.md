ansible-hadoop
---------
These Ansible playbooks will build a Hadoop cluster.

You can pre-build a Rackspace cloud environment or run the playbooks against an existing environment.

---

## [Installation] (id:installation)

See [INSTALL.md](../master/INSTALL.md) for installation and build instructions.


## [Requirements] (id:requirements)

- Ansible >= 2.0.

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

###`bootstrap* and hortonworks*`

Similarly, run the bootstrap and hortonworks scripts (in this order), depending what type of environment you have.

- For a Rackspace Cloud environment:
  ````
  bash bootstrap_rax.sh
  bash hortonworks_rax.sh
  ````

- For static / prebuilt environments:
  ````
  bash bootstrap_static.sh
  bash hortonworks_static.sh
  ````


## [Accessing Ambari] (id:ambari)

Once you are at this point you can see progress by accessing the Ambari interface (the `ambari-node` will be the last host that ran a play). 

The provided Ansible playbook will only open the firewall if you've added your workstation IP to `allowed_external_ips` variable in the `playbooks/group_vars/all` file. 

Alternatively, you can access Ambari by either opening the firewall manually or by opening a socks proxy with the following command:

````
ssh -D 12345 root@ambari-node
````

You will need to modify your browser settings to use socks proxy `localhost` and port `12345`. 

You'll then be able to navigate to http://ambari-node:8080 in your configured browser and access all subsidiary links.


## [Ansible-Hadoop History] (id:history)

As with many projects this code is the end result of a lot of effort from individuals not properly represented by a simple commit history. 

Rackspace started deploying Hadoop on dedicated gear for customers more than a year ago in a very manual process. This process landed with myself and these Rockstars:

[Joe Engel](https://github.com/Joeskyyy) (Racker Emeritus)

[Mark Lessel](https://github.com/magglass1)

[Alexandru Anghel](https://github.com/alexandruanghel)

All of whom wrote a lot of the automation for deploying Hadoop on customer gear at Rackspace.

Today with a pile of customers under our belt and many more all the time, we wanted to share our efforts with the world by publishing this code which you can also use to deploy Hadoop in various ways at Rackspace.

This of course is only the beginning! 

I hope this project evolves and inspires even more Rockstars to find ways to contribute.

