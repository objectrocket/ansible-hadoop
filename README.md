ansible-hadoop
---------

These Ansible playbooks will build a Hadoop cluster (Hortonworks Data Platform).

You can pre-build a Rackspace cloud environment or run the playbooks against an existing environment.

## Configuration files

To customize, change the variables under `playbooks/group_vars` folder:

1. **playbooks/group_vars/all**: contains global cluster and cloud settings
1. **playbooks/group_vars/master-nodes**: master-nodes configuration
1. **playbooks/group_vars/slave-nodes**: slave-nodes configuration
1. **playbooks/group_vars/edge-nodes**: edge-nodes configuration

For a one-node cluster, set `cloud_nodes_count` in master-nodes to 1 and `cloud_nodes_count` in slave-nodes to 0.

## Requirements

- Requires Ansible 1.8 or newer
- Expects CentOS/RHEL 6.x hosts

Building the cloud environment requires `pyrax` Python module: https://github.com/rackspace/pyrax 

Also recommended is to run `pip install oslo.config netifaces`.

The cloud environment requires the standard pyrax credentials file that looks like this:
````
[rackspace_cloud]
username = my_username
api_key = 01234567890abcdef
````
This file will be referenced in the inventory (the `rax_credentials_file` variable).

By default, the file is expected to be: `~/.raxpub`

## Scripts

####`provision_rax.sh`

To provision a cloud environment, run the `provision_rax.sh` script after you've customized the variables under `playbooks/group_vars`:
````
bash provision_rax.sh
````

####`bootstrap* and hortonworks*`

Similarly, run the bootstrap and hortonworks scripts (in this order), depending what type of environment you have.

Example for a cloud environment:
````
bash bootstrap_rax.sh
bash hortonworks_rax.sh
````
For dedicated / prebuilt environments, you'll need to manually add the nodes in the `inventory/static` file.

####`provision_cbd.sh`

Provision a Rackspace Cloud Big Data cluster (http://www.rackspace.com/cloud/big-data) by running this script.

Customize it via the `playbooks/group_vars/cbd` file.
````
bash provision_cbd.sh
````
