#!/bin/bash

ansible-playbook -f 20 -i inventory/static playbooks/hortonworks.yml
