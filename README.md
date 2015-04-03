hdp-poc - deploys a single-node Hortonworks Data Platform "cluster"
---------

This Ansible playbook will build a single node HDP instance that can be used as a poc for MBD.
You can run this playbook on an already existing server (dedicated or cloud) by using the inventory-dedicated file.

It also offers the possibility of building a Rackspace Cloud Server or OnMetal with or without Cloud Block Storage.
Just change the necessary options in the corresponding inventory file.

For the Cloud builds it uses pyrax so make sure you have it installed (https://github.com/rackspace/pyrax). 
(also recommended is to run 'pip install oslo.config netifaces').

It uses the standard pyrax credentials file that looks like:
````
[rackspace_cloud]
username = my_username
api_key = 01234567890abcdef
````
Which will then be referenced in the inventory (the ~/.raxpub file for example).

Customization can be done by changing the variables in the inventory file.

### Examples:

#### For a dedicated server
Customize the inventory-dedicated file by completing the following:

+ the correct IP under [ambari-host].
+ the correct rack user password (in place of \<rack password\>).
+ or if root can directly login, set ansible_ssh_user to root.
+ customize the main network interface (usually bond0 or eth0).
+ customize the cluster name if you want (hdp_cluster_name).
+ set hdp_install_hbase to true if you want hbase to be installed.
+ set the Ambari admin user password (hdp_new_admin_password) otherwise it will be the default one: admin.
+ set the password for all other services (nagiosadmin, hive, oozie).
+ set the email address where Nagios alerts would be sent to (hdp_nagios_contact).
+ set the disks that will be formatted and used as HDFS data disks. They need to be pre-configured (either from core before the kick or with omconfig storage / hpssacli).
+ alternatively, if you don't want to use separate disks for HDFS data, just set hdp_dfs_data_disks=[] and it will use the root volume.

````
ansible-playbook -i inventory-dedicated site.yml
````

#### For a normal Cloud Server
Customize the inventory file by completing the following:

+ the server name (must be a FQDN, you can use .localnet if you don't have a domain).
+ the required flavor (>8GB) and region.
+ the name and location of the public key you want to use to login (or leave the default if you already ran ssh-keygen -t rsa).
+ a Cloud Server will be configured with iptables so if you want to allow access to administrative IPs, complete rax_allow_ips (although it's recommended to use SSH tunnels so that the traffic is encrypted).
+ customize the main network interface (eth0 for ExNet or eth1 for ServiceNet).
+ customize the cluster name if you want (hdp_cluster_name).
+ set hdp_install_hbase to true if you want hbase to be installed.
+ set the Ambari admin user password (hdp_new_admin_password) otherwise it will be the default one: admin.
+ set the password for all other services (nagiosadmin, hive, oozie).
+ set the email address where Nagios alerts would be sent to (hdp_nagios_contact).
+ set the disks that will be formatted and used as HDFS data disks. You have the option to build Cloud Block Storage, just make sure you have the same number of disks in rax_cbs_volumes and hdp_dfs_data_disks, with the desired names.
+ alternatively, if you don't want to use separate disks for HDFS data, just set rax_cbs_build=false and hdp_dfs_data_disks=[] and it will use the root volume.

````
ansible-playbook -i inventory site.yml
````

#### For an OnMetal Cloud Server
Customize the inventory file by completing the following:

+ the server name (must be a FQDN, you can use .localnet if you don't have a domain).
+ the required flavor (recommended io1) and region (only IAD for now).
+ the name and location of the public key you want to use to login (or leave the default if you already ran ssh-keygen -t rsa).
+ a Cloud Server will be configured with iptables so if you want to allow access to administrative IPs, complete rax_allow_ips (although it's recommended to use SSH tunnels so that the traffic is encrypted).
+ customize the main network interface (bond0.101 for ExNet or bond0.401 for ServiceNet).
+ customize the cluster name if you want (hdp_cluster_name).
+ set hdp_install_hbase to true if you want hbase to be installed.
+ set the Ambari admin user password (hdp_new_admin_password) otherwise it will be the default one: admin.
+ set the password for all other services (nagiosadmin, hive, oozie).
+ set the email address where Nagios alerts would be sent to (hdp_nagios_contact).
+ set the disks that will be formatted and used as HDFS data disks. By default for OnMetal IO these are sda and sdb so you can leave them as they are.

````
ansible-playbook -i inventory-onmetal site.yml
````
