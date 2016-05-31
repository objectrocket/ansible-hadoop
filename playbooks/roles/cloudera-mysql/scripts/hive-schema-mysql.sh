#!/bin/bash

PATH=/opt/cloudera/;

cd $PATH


/usr/bin/mysql -h$1 -u$2 -p$3 $4 < hive-schema-1.1.0.mysql.sql;


