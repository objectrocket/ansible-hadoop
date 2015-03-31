ansible-hadoop
==============

Ansible + Hadoop Prep and Ambari install 

This project is under development: Current release .0


production                # inventory file for production servers
stage                     # inventory file for stage environment

group_vars/
   Cloud  		  # Anything specific to these groups 
   OnMetal
   Dedicated

host_vars/
   somethingUnusual       # Add custom host specific Vars

library/rax_cbd           # CBD Deployment Library
filter_plugins/           # nothing here currently 

provision.yml             # Provision Cloud Resources
bootstrap.yml             # Prep Servers for Hadoop
ambari.yml                # Ambari install and blueprint provisioning

roles/
    common/               # this hierarchy represents a "role"
        tasks/            #
            main.yml      #  <-- tasks file can include smaller files if warranted
        handlers/         #
            main.yml      #  <-- handlers file
        templates/        #  <-- files for use with the template resource
            ntp.conf.j2   #  <------- templates end in .j2
        files/            #
            bar.txt       #  <-- files for use with the copy resource
            foo.sh        #  <-- script files for use with the script resource
        vars/             #
            main.yml      #  <-- variables associated with this role
        defaults/         #
            main.yml      #  <-- default lower priority variables for this role
        meta/             #
            main.yml      #  <-- role dependencies

    datanode/             # anything that only applies to datanodes
    masternode/           # ""
    edgenode/             # ""
