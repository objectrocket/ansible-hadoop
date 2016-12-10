ansible-hadoop environment and general installation guide
---------

* These Ansible playbooks can build a Rackspace Cloud environment and install Hadoop on it. Follow this [link](#install-hdp-on-rackspace-cloud).

* It can also install Hadoop on existing Linux devices, be it dedicated devices in a datacenter or VMs running on a hypervizor. Follow this [link](#install-hdp-on-existing-devices).


---


# Install Hadoop on Rackspace Cloud

## Build setup

First step is to setup the build node / workstation.

This build node or workstation will run the Ansible code and build the Hadoop cluster (itself can be a Hadoop node).

This node needs to be able to contact the cluster devices via SSH and the Rackspace APIs via HTTPS.

The following steps must be followed to install Ansible and the prerequisites on this build node / workstation, depending on its operating system:

### CentOS/RHEL 6

1. Install required packages:

  ```
  sudo su -
  yum -y remove python-crypto
  yum -y install epel-release || yum -y install http://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
  yum repolist; yum install gcc gcc-c++ python-virtualenv python-pip python-devel sshpass git vim-enhanced libffi libffi-devel gcc openssl-devel -y
  ```

2. Create the Python virtualenv and install Ansible:

  ```
  virtualenv ansible2; source ansible2/bin/activate
  pip install oslo.config==3.0.0 keyring==5.7.1 importlib ansible pyrax
  ```

3. Generate SSH public/private key pair (press Enter for defaults):

  ```
  ssh-keygen -q -t rsa
  ```

### CentOS/RHEL 7

1. Install required packages:

  ```
  sudo su -
  yum -y install epel-release || yum -y install http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
  yum repolist; yum install gcc gcc-c++ python-virtualenv python-pip python-devel sshpass git vim-enhanced libffi libffi-devel gcc openssl-devel -y
  ```

2. Create the Python virtualenv and install Ansible:

  ```
  virtualenv ansible2; source ansible2/bin/activate
  pip install ansible==2.1.3.0 pyrax
  ```

3. Generate SSH public/private key pair (press Enter for defaults):

  ```
  ssh-keygen -q -t rsa
  ```

### Ubuntu 14+ / Debian 8

1. Install required packages:

  ```
  sudo su -
  apt-get update; apt-get -y install python-virtualenv python-pip python-dev sshpass git vim libffi libffi-devel gcc openssl-devel
  ```

2. Create the Python virtualenv and install Ansible:

  ```
  virtualenv ansible2; source ansible2/bin/activate
  pip install ansible==2.1.3.0 pyrax
  ```

3. Generate SSH public/private key pair (press Enter for defaults):

  ```
  ssh-keygen -q -t rsa
  ```


## Setup the Rackspace credentials file

The cloud environment requires the standard [pyrax](https://github.com/rackspace/pyrax/blob/master/docs/getting_started.md#authenticating) credentials file that looks like this:
```
[rackspace_cloud]
username = my_username
api_key = 01234567890abcdef
```

Replace `my_username` with your Rackspace Cloud username and `01234567890abcdef` with your API key.

Save this file as `.raxpub` under the home folder of the user running the playbook.


## Clone the repository

On the same build node / workstation, run the following:

```
cd; git clone https://github.com/rackerlabs/ansible-hadoop
```


## Set master-nodes variables

There are three types of nodes:

1. `master-nodes` are nodes running the master Hadoop services. You can specify one, two or three nodes.
 
 With two or three master nodes the HDFS NameNode will be configured in HA mode.

1. `slave-nodes` are nodes running the slave Hadoop services and store HDFS data. You can specify 0 or more nodes.
 
 By specifying no slave-nodes, the scripts will deploy a single-node Hadoop, similar with the Hortonworks sandbox.

1. `edge-nodes` are client only nodes and have only the client libraries installed. These are optional. 



Using the template at `~/ansible-hadoop/playbooks/group_vars/master-nodes-templates; Modify the file at `~/ansible-hadoop/playbooks/group_vars/master-nodes` to set master-nodes specific information (you can remove all the existing content from this file).

| Variable           | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| cluster_interface  | Should be set to the network device that the Hadoop nodes will use to communicate between them. |
| cloud_nodes_count  | Should be set to the desired number of master-nodes (1, 2 or 3).   |
| cloud_image        | The OS image to be used. Can be `CentOS 6 (PVHVM)`, `CentOS 7 (PVHVM)` or `Ubuntu 14.04 LTS (Trusty Tahr) (PVHVM)`. |
| cloud_flavor       | [Size flavor](https://developer.rackspace.com/docs/cloud-servers/v2/developer-guide/#supported-flavors-for-cloud-servers) of the nodes. Minimum `general1-8` for Hadoop nodes. |
| hadoop_disk        | The disk that will be mounted under `/hadoop`. If the [size flavor](https://developer.rackspace.com/docs/cloud-servers/v2/developer-guide/#supported-flavors-for-cloud-servers) provides with an ephemeral disk, set this to `xvde`. Remove this variable if `/hadoop` should just be a folder on the root filesystem or if the disk has already been partitioned and mounted. |
| datanode_disks     | Only used for single-nodes clusters. The disks that will be mounted under `/grid/{0..n}`. Should be set if one or more separate disk devices are used for storing HDFS data. |

For single-node clusters, if Rackspace Cloud Block Storage is to be built for storing HDFS data, set the following options:

| Variable           | Description                                                                         |
| ------------------ | ----------------------------------------------------------------------------------- |
| build_datanode_cbs | Set to `true` to build CBS for . `datanode_disks` also needs to be set (for example, to build two CBS disks, set `datanode_disks` to `['xvde', 'xvdf']`). |
| cbs_disks_size     | The size of the disk(s) in GB.                                                      |
| cbs_disks_type     | The type of the disk(s), can be `SATA` or `SSD`.                                    |

- Example with using 2 x `general1-8` master nodes running CentOS 7 with ServiceNet(`eth1`) as the cluster interface:

  ```
  cluster_interface: 'eth1'
  cloud_nodes_count: 2
  cloud_image: 'CentOS 7 (PVHVM)'
  cloud_flavor: 'general1-8'
  ```

- Example with using 2 x `onmetal-general2-small` master nodes running Ubuntu 14:

  ```
  cloud_nodes_count: 2
  cloud_image: 'OnMetal - Ubuntu 14.04 LTS (Trusty Tahr)'
  cloud_flavor: 'onmetal-general2-small'
  ```

- Example for installing a single-node cluster (Hortonworks sandbox in Rackspace Cloud) and using the ephemeral disk of the `performance2-15` flavor for the `/hadoop` mount (for a single node cluster, make sure `cloud_nodes_count` is set to `0` in `group_vars/slave-nodes`):

  ```
  cluster_interface: 'eth1'
  cloud_nodes_count: 1
  cloud_image: 'CentOS 7 (PVHVM)'
  cloud_flavor: 'performance2-15'
  hadoop_disk: xvde
  ```

- Example for installing a single-node OnMetal cluster (Hortonworks sandbox on OnMetal) and using the ephemeral SSD disks of the `onmetal-io2` flavor for both the `/hadoop` mount and HDFS data (for a single node cluster, make sure `cloud_nodes_count` is set to `0` in `group_vars/slave-nodes`):

  ```
  cloud_nodes_count: 1
  cloud_image: 'OnMetal - CentOS 7'
  cloud_flavor: 'onmetal-io2'
  hadoop_disk: sdc
  datanode_disks: ['sdd']
  ```

## Set slave-nodes variables

Using the template file ~/ansible-hadoop/playbooks/group_vars/master-nodes-templates; Modify the file at `~/ansible-hadoop/playbooks/group_vars/slave-nodes` to set slave-nodes specific information (you can remove all the existing content from this file).

| Variable           | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| cluster_interface  | Should be set to the network device that the Hadoop nodes will use to communicate between them. |
| cloud_nodes_count  | Should be set to the desired number of slave-nodes (0 or more).    |
| cloud_image        | The OS image to be used. Can be `CentOS 6 (PVHVM)`, `CentOS 7 (PVHVM)` or `Ubuntu 14.04 LTS (Trusty Tahr) (PVHVM)`. |
| cloud_flavor       | [Size flavor](https://developer.rackspace.com/docs/cloud-servers/v2/developer-guide/#supported-flavors-for-cloud-servers) of the nodes. Minimum `general1-8` for Hadoop nodes. |
| datanode_disks     | The disks that will be mounted under `/grid/{0..n}`. Should be set if one or more separate disk devices are used for storing HDFS data and remove it if the data should be stored on the root filesystem. Can be set to `['xvde']` or `['xvde', 'xvdf']` if the [size flavor](https://developer.rackspace.com/docs/cloud-servers/v2/developer-guide/#supported-flavors-for-cloud-servers) provides with an ephemeral disk. Alternatively, you can let the playbook build Cloud Block Storage for this purpose. |

If Rackspace Cloud Block Storage is to be built for storing HDFS data, set the following options:

| Variable           | Description                                                                         |
| ------------------ | ----------------------------------------------------------------------------------- |
| build_datanode_cbs | Set to `true` to build CBS. `datanode_disks` also needs to be set (for example, to build two CBS disks, set `datanode_disks` to `['xvde', 'xvdf']`). |
| cbs_disks_size     | The size of the disk(s) in GB.                                                      |
| cbs_disks_type     | The type of the disk(s), can be `SATA` or `SSD`.                                    |

- Example with 3 x `general1-8` nodes running CentOS 7 and 2 x 200GB CBS disks on each node:

  ```
  cluster_interface: 'eth1'
  cloud_nodes_count: 3
  cloud_image: 'CentOS 7 (PVHVM)'
  cloud_flavor: 'general1-8'
  build_datanode_cbs: true
  cbs_disks_size: 200
  cbs_disks_type: 'SATA'
  datanode_disks: ['xvde', 'xvdf']
  ```

- Example with 3 x OnMetal I/O v2 nodes running CentOS 7 and using the ephemeral SSD disks of the `onmetal-io2` flavor as the HDFS data drives:

  ```
  cloud_nodes_count: 3
  cloud_image: 'OnMetal - CentOS 7'
  cloud_flavor: 'onmetal-io2'
  datanode_disks: ['sdc', 'sdd']
  ```


## Set edge-nodes variables

Optionally, if edge nodes are used, modify the file at `~/ansible-hadoop/playbooks/group_vars/edge-nodes` to set edge-nodes specific information (you can remove all the existing content from this file).

The same guidelines as for the master nodes above can be used here.


## Set the global variables

Move on to the HDP or CDH Install guides respectively at this point 
