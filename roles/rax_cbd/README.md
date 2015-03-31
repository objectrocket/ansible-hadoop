rax_cbd - create / delete / resize a Rackspace Cloud Big Data cluster
---------

This is an ansible module that allows to create, resize and delete a Rackspace Cloud Big Data cluster.
It can wait for the cluster to be built (configurable) and offers a variety of configurable options.

As a prerequisite, the python-lavaclient module for Cloud Big Data has to be installed: http://docs.rackspace.com/cbd/api/v1.0/cbd-getting-started/content/installing_Client.html

It uses the standard pyrax credentials file that looks like:
````
[rackspace_cloud]
username = my_username
api_key = 01234567890abcdef
````

Being a custom Ansible module, it can be used in a couple of different ways:

* put the file in a library folder under the structure of your cookbook (like in this repo)
* have ANSIBLE_LIBRARY environment variable to point to the folder where the module resides

Included are a couple of examples that illustrate some use cases and how can the returned variables be used.

#### Example run:
````
ansible-playbook -i hosts_simple cbd_simple.yml
````
