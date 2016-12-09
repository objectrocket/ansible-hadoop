ansible-hadoop installation guide
---------

* These Ansible playbooks can build a Rackspace Cloud environment and install CDH on it. Follow this [link](#install-hdp-on-rackspace-cloud).

* It can also install CDH on existing Linux devices, be it dedicated devices in a datacenter or VMs running on a hypervizor. Follow this [link](#install-hdp-on-existing-devices).

## Set the global variables

Modify the file at `~/ansible-hadoop/playbooks/group_vars/all` to set the cluster configuration.

## set the Cloudera variables

Modify the file at `~/ansible-hadoop/playbooks/group_vars/all` to set the cluster configuration.

The following table will describe the most important variables:

| Variable             | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| cluster_name         | The name of the HDP cluster                                         |
| distro               | select cdh or hdp for correct variable inclusions                   |
| rax_credentials_file | The location of the Rackspace credentials file as set above         |
| rax_region           | The Rackspace region where the Cloud Servers should be built        |
| allowed_external_ips | A list of IPs allowed to connect to cluster nodes                   |
| ssh keyfile          | The SSH keyfile that will be placed on cluster nodes at build time. |
| ssh keyname          | The name of the SSH key. Make sure you change this if another key was previously used with the same name. |

Modify the file at `~/ansible-hadoop/playbooks/group_vars/cloudera` to set the Cloudera configuration.

The following table will describe the most important variables:

| Variable             | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| cdh_version          | The HDP major version that should be installed                      |
| admin_password       | This is the Ambari admin user password                              |
| services_password    | This is a password used by everything else (like hive's database)   |
| install_*            | Set these to true in order to install the respective HDP component  |

## Provision the Cloud environment
The first step is to run the script that will provision the Cloud environment:

```
cd ~/ansible-hadoop/ && bash provision_rax.sh
```


## Bootstrapping

Then run the bootstrapping script that will setup the prerequisites on the cluster nodes.

```
cd ~/ansible-hadoop/ && bash bootstrap_rax.sh
```


## HDP Installation

Then run the script that will install Ambari and build the cluster using Ambari Blueprints:

```
cd ~/ansible-hadoop/ && bash cloudera_rax.sh
```


## Login to Cloudera Manager

Once you are at this point you can see progress by accessing the Cloudera Manager interface.

The Cloudera Manager server runs on the last master-node and be accessed on port 7180.


---


# Install CDH on existing devices


## Build setup

First step is to setup the build node / workstation.

This build node or workstation will run the Ansible code and build the Hadoop cluster (itself can be a Hadoop node).

This node needs to be able to contact the cluster devices via SSH.

All the SSH logins must be known / prepared in advance or alternative SSH public-key authentication can also be used.

The following steps must be followed to install Ansible and the prerequisites on this build node / workstation, depending on its operating system:

### CentOS/RHEL 6

1. Install required packages:

  ```
  sudo su -
  yum -y install epel-release || yum -y install http://dl.fedoraproject.org/pub/epel/epel-release-latest-6.noarch.rpm
  yum repolist; yum install python-virtualenv python-pip python-devel sshpass git vim-enhanced libffi libffi-devel gcc openssl-devel -y
  ```

2. Create the Python virtualenv and install Ansible:

  ```
  virtualenv ansible2; source ansible2/bin/activate
  pip install ansible==2.1.3.0 pyrax
  ```

### CentOS/RHEL 7

1. Install required packages:

  ```
  sudo su -
  yum -y install epel-release || yum -y install http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
  yum repolist; yum install python-virtualenv python-pip python-devel sshpass git vim-enhanced libffi libffi-devel gcc openssl-devel -y
  ```

2. Create the Python virtualenv and install Ansible:

  ```
  virtualenv ansible2; source ansible2/bin/activate
  pip install ansible==2.1.3.0 pyrax
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


## Clone the repository

On the same build node / workstation, run the following:

```
cd; git clone https://github.com/rackerlabs/ansible-hadoop
```


## Set the inventory

There are three types of nodes:

1. `master-nodes` are nodes running the master Hadoop services. You can specify one, two or three nodes.
 
 With two or three master nodes the HDFS NameNode will be configured in HA mode.

1. `slave-nodes` are nodes running the slave Hadoop services and store HDFS data. You can specify 0 or more nodes.
 
 By specifying no slave-nodes, the scripts will deploy a single-node HDP, similar with the Hortonworks sandbox.

1. `edge-nodes` are client only nodes and have only the client libraries installed. These are optional. 


Modify the inventory file at `~/ansible-hadoop/inventory/static` to match the desired cluster layout.

- For each node, set the `ansible_host` to the IP address that is reachable from the build node / workstation.

- Then set `ansible_user=root` and `ansible_ssh_pass` if the node allows for root user logins. If these are not set, public-key authentication will be used.

- Example for a 1 master node and 3 slave nodes cluster:

  ```
  [master-nodes]
  master01 ansible_host=192.168.0.2 ansible_user=root ansible_ssh_pass=changeme
  
  [slave-nodes]
  slave01 ansible_host=192.168.0.3 ansible_user=root ansible_ssh_pass=changeme
  slave02 ansible_host=192.168.0.4 ansible_user=root ansible_ssh_pass=changeme
  ```

- Example for installing a single-node HDP cluster on the local build node (useful if you want HDP installed on a VirtualBox / VMware VM):

  ```
  [master-nodes]
  master01 ansible_host=localhost ansible_connection=local
  ```


## Set master-nodes variables

Modify the file at `~/ansible-hadoop/playbooks/group_vars/master-nodes` to set master-nodes specific information (you can remove all the existing content from this file).

| Variable           | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| cluster_interface  | Should be set to the network device that the HDP nodes will use to communicate between them. |
| hadoop_disk        | The disk that should be mounted under `/hadoop`. The playbook will attempt to partition and format it! Remove this variable if `/hadoop` should just be a folder on the root filesystem or if the disk has already been partitioned and mounted. |
| datanode_disks     | Only used for single-nodes clusters. The disks that will be mounted under `/grid/{0..n}`. Should be set if one or more separate disk devices are used for storing HDFS data. |

- Example for using the `eth0` cluster interface and `sdb` as the disk device for `/hadoop`:

  ```
  cluster_interface: 'eth0'
  hadoop_disk: sdb
  ```

- Example for a single-node cluster with `sdb` mounted under `/hadoop` and `sdc`, `sdd`, `sde` used as data drives and mounted under `/grid/0`, `/grid/1` and `/grid/2`:

  ```
  cluster_interface: 'eth0'
  hadoop_disk: sdb
  datanode_disks: ['sdc', 'sdd', 'sde']
  ```


## Set slave-nodes variables

Modify the file at `~/ansible-hadoop/playbooks/group_vars/slave-nodes` to set slave-nodes specific information (you can remove all the existing content from this file).

| Variable           | Description                                                        |
| ------------------ | ------------------------------------------------------------------ |
| cluster_interface  | Should be set to the network device that the HDP nodes will use to communicate between them. |
| datanode_disks     | The disks that will be mounted under `/grid/{0..n}`. Should be set if one or more separate disk devices are used for storing HDFS data. Remove this variable if HDFS data should be stored on the root filesystem or if the disks have already been partitioned and mounted under `/grid/{0..n}`. |

- Example for using the `eth0` cluster interface and `sdb`, `sdc`, `sdd` as the disk devices that will be mounted under `/grid/0`, `/grid/1` and `/grid/2`:

  ```
  cluster_interface: 'eth0'
  datanode_disks: ['sdb', 'sdc', 'sdd']
  ```


## Set edge-nodes variables

Optionally, if edge nodes are used, modify the file at `~/ansible-hadoop/playbooks/group_vars/edge-nodes` to set edge-nodes specific information (you can remove all the existing content from this file).

The same guidelines as for the master nodes above can be used here.


## Set the global variables

Modify the file at `~/ansible-hadoop/playbooks/group_vars/all` to set the cluster configuration.

The following table will describe the most important variables:

| Variable          | Description                                                         |
| ----------------- | ------------------------------------------------------------------- |
| cluster_name      | The name of the HDP cluster.                                        |
| hdp_version       | The HDP major version that should be installed.                     |
| admin_password    | This is the Ambari admin user password.                             |
| services_password | This is a password used by everything else (like hive's database).  |
| install_*         | Set these to true in order to install the respective HDP component. |


## Bootstrapping

The first step is to run the bootstrapping script that will setup the prerequisites on the cluster nodes.

```
cd ~/ansible-hadoop/ && bash bootstrap_static.sh
```


## HDP Installation

Then run the script that will install Ambari and build the cluster using Ambari Blueprints:

```
cd ~/ansible-hadoop/ && bash hortonworks_static.sh
```


## Login to Ambari

Once you are at this point you can see progress by accessing the Ambari interface.

The Ambari server runs on the last master-node and be accessed on port 8080.

