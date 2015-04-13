ansible-hadoop
---------

These Ansible playbooks will build a Hadoop cluster (Hortonworks Data Platform).

You can pre-build a Rackspace cloud environment or run the playbooks against an existing environment.

## Configuration files

To customize, change the variables under `playbooks/group_vars` folder:

1. **`playbooks/group_vars/all`**: contains global cluster and cloud settings
1. **`playbooks/group_vars/master-nodes`**: master-nodes configuration
1. **`playbooks/group_vars/slave-nodes`**: slave-nodes configuration
1. **`playbooks/group_vars/edge-nodes`**: edge-nodes configuration

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
This file will be referenced in `playbooks/group_vars/all` (the `rax_credentials_file` variable).

By default, the file is expected to be: `~/.raxpub`

## Scripts

#####`provision_rax.sh`

To provision a cloud environment, run the `provision_rax.sh` script after you've customized the variables under `playbooks/group_vars`:
````
bash provision_rax.sh
````

#####`bootstrap* and hortonworks*`

Similarly, run the bootstrap and hortonworks scripts (in this order), depending what type of environment you have.

Example for a cloud environment:
````
bash bootstrap_rax.sh
bash hortonworks_rax.sh
````
For dedicated / prebuilt environments, you'll need to manually add the nodes in the `inventory/static` file.

##### Accessing Ambari
Once you are at this point you can see progress by accessing the Ambari interface. The provided Ansible scripts do not open the firewall for access by default. You can access Ambari by either opening the firewall manually or by opening a socks proxy with the following command:

````
ssh -D 12345 root@ambari-ip
````

You will need to modify your browser settings to use socks proxy localhost and port 12345. 

You then be able to navigate to the ambari-ip:8080 in your configured browser and access all subsidary links

#####`provision_cbd.sh`

Provision a Rackspace Cloud Big Data cluster (http://www.rackspace.com/cloud/big-data) by running this script.

Customize it via the `playbooks/group_vars/cbd` file.
````
bash provision_cbd.sh
````
## Ansible-Hadoop History

As with many projects this code is the end result of a lot of effort from individuals not propoerly represented by a simple commit history. 

Rackspace started deploying Hadoop on dedicated gear for customers more than a year ago in a very manual process. This process landed with myself and these Rockstars:

[Joe Engel](https://github.com/Joeskyyy)

[Mark Lessel](https://github.com/magglass1)

[Alexandru Anghel](https://github.com/alexandruanghel)

All of whom wrote a lot of the automation for deploying Hadoop on customer gear at Rackspace.

Today with a pile of customers under our belt and many more all the time, we wanted to share our efforts with the world by publishing this code which you can also use to deploy Hadoop in various ways at Rackspace.

This of course is only the begininning! 

I hope this project evolves and inspires even more Rockstars to find ways to contribute.



