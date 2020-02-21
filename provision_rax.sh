#!/bin/bash

ansible-playbook -i inventory/localhost  --extra-vars="ansible_python_interpreter=$(which python)" playbooks/provision_rax.yml
