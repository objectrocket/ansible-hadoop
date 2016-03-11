#!/bin/bash

export AWS_ACCESS_KEY_ID="$(grep -i AWS_ACCESS_KEY_ID ~/.aws/credentials | cut -d= -f2 | xargs)"
export AWS_SECRET_ACCESS_KEY="$(grep -i AWS_SECRET_ACCESS_KEY ~/.aws/credentials | cut -d= -f2 | xargs)"

aws_region=$(grep aws_region playbooks/group_vars/all|cut -d"'" -f2)
cluster_name=$(grep cluster_name playbooks/group_vars/all|cut -d"'" -f2)

# Uncomment this for Ubuntu Builds
# ansible_user="ubuntu"

# Uncomment this for Redhat/CentOS builds
ansible_user="ec2-user"

cat > inventory/ec2.ini <<EOL
[ec2]
regions = $aws_region
regions_exclude =
instance_filters = tag:environment=$cluster_name
cache_path = ~/.ansible/tmp
cache_max_age = 1
destination_variable = public_dns_name
vpc_destination_variable = ip_address

route53 = False
all_instances = False
all_rds_instances = False
all_elasticache_replication_groups = False
all_elasticache_clusters = False
all_elasticache_nodes = False

nested_groups = False
replace_dash_in_groups = True
expand_csv_tags = False
group_by_tag_keys = True
group_by_security_group = True
EOL

ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook  -e "ansible_user=$ansible_user" -i inventory/ec2.py playbooks/bootstrap_aws.yml
