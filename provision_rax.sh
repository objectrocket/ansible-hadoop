#!/bin/bash

ansible-playbook -i inventory/localhost playbooks/provision_rax.yml
