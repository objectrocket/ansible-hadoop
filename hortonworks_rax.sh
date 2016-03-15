#!/bin/bash

export RAX_CREDS_FILE=$(grep rax_credentials_file playbooks/group_vars/all|cut -d"'" -f2)
export RAX_REGION=$(grep rax_region playbooks/group_vars/all|cut -d"'" -f2)
VARS="${VARS} ANSIBLE_SCP_IF_SSH=y ANSIBLE_HOST_KEY_CHECKING=False"

export $VARS
ansible-playbook -f 20 -i inventory/rax.py playbooks/hortonworks.yml
