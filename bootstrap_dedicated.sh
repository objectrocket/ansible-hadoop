#!/bin/bash

ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -f 20 -i inventory/static playbooks/bootstrap.yml
