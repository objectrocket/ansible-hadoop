#!/bin/bash

export RAX_CREDS_FILE=$(grep rax_credentials_file playbooks/group_vars/all|cut -d"'" -f2)
export RAX_REGION=$(grep rax_region playbooks/group_vars/all|cut -d"'" -f2)

# ansible-playbook -vvv -i inventory/rax.py playbooks/cloudera.yml --tags cluster_deploy
ansible-playbook -vvv -i inventory/rax.py playbooks/cloudera.yml
