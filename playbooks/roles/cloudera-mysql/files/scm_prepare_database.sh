#!/bin/bash
# Copyright (c) 2011-2012 Cloudera, Inc. All rights reserved.
#
# Configures Oracle, MySQL or PostgreSQL for SCM.

SCRIPT_DIR="$( cd -P "$( dirname "$0" )" && pwd )"

# SCM server default file contains location of system MySQL jar
prog="cloudera-scm-server"
CMF_DEFAULTS=$(readlink -e $(dirname ${BASH_SOURCE-$0})/../../../etc/default)
CMF_DEFAULTS=${CMF_DEFAULTS:-/etc/default}

# Find the config directory
CMF_CONFIG_DIR=$(readlink -e $(dirname ${BASH_SOURCE-$0})/../../../etc/$prog)
CMF_CONFIG_DIR=${CMF_CONFIG_DIR:-/etc/$prog}

[ -e $CMF_DEFAULTS/$prog ] && . $CMF_DEFAULTS/$prog

source "$SCRIPT_DIR/scm_database_functions.sh"

main()
{
  parse_arguments "$@"

  # Before making destructive changes, check
  # some preconditions:
  locate_java_home
  check_config_writable

  create_user_and_database
  write_config_file
  test_db_connection

  # This is the important bit!
  echo "All done, your SCM database is configured correctly!"
}

usage()
{
cat << EOF
usage: $0 [options] (postgresql|mysql|oracle) database username [password]

Prepares a database (currently either MySQL, PostgreSQL or Oracle)
for use by Cloudera Service Configuration Manager (SCM):
o Creates a database (For PostgreSQL and MySQL only)
o Grants access to that database, by:
  - (PostgreSQL) Creating a role
  - (MySQL) Creating a grant
o Creates the SCM database configuration file.
o Tests if the database connection parameters are valid.

MANDATORY PARAMETERS
database type: either "oracle", "postgresql" or "mysql"
database: For PostgreSQL and MySQL, name of the SCM database to create.
          For Oracle this is the SID of the Oracle database.
username: Username for access to SCM's database.

OPTIONAL PARAMETERS
password: Password for the SCM user. If not provided, will
          prompt for it.

OPTIONS
   -h|--host       Database host. Default is to connect locally.
   -P|--port       Database port. If not specified, the database specific
                   default will be used: namely, 3306 for MySQL,
                   5432 for PostgreSQL, and 1521 for Oracle.
   -u|--user       Database username that has privileges for creating
                   users and grants.  The default is '$USER'.
                   Typical values are 'root' for MySQL and
                   'postgres' for PostgreSQL. Not applicable for Oracle.
   -p|--password   Database Password. Default is no password.
   --scm-host      SCM server's hostname. Omit if SCM is colocated with MySQL.
   --config-path   Path to SCM configuration files.
                   Default is /etc/cloudera-scm-server.
   -f|--force      Don't stop when an error is encountered.
   -v|--verbose    Print more informational messages.
   -?|--help       Show this message.

NOTE ON POSTGRESQL CONFIGURATION
PostgreSQL must be configured to accept connections
with md5 password authentication.  To do so,
edit /var/lib/pgsql/data/pg_hba.conf (or similar)
to include "host all all 127.0.0.1/32 md5" _above_
a similar line that allows 'ident' authentication.
EOF
}

# Attempts to locate java home, prints an error and exits if no
# java can be found. Copied from agents/cmf/service/commmon/cloudera-config.sh
locate_java_home() {
  local JAVA6_HOME_CANDIDATES=(
    '/usr/lib/j2sdk1.6-sun'
    '/usr/lib/jvm/java-6-sun'
    '/usr/lib/jvm/java-1.6.0-sun-1.6.0'
    '/usr/lib/jvm/j2sdk1.6-oracle'
    '/usr/lib/jvm/j2sdk1.6-oracle/jre'
    '/usr/java/jdk1.6'
    '/usr/java/jre1.6'
  )

  local OPENJAVA6_HOME_CANDIDATES=(
    '/usr/lib/jvm/java-1.6.0-openjdk'
    '/usr/lib/jvm/jre-1.6.0-openjdk'
  )

  local JAVA7_HOME_CANDIDATES=(
    '/usr/java/jdk1.7'
    '/usr/java/jre1.7'
    '/usr/lib/jvm/j2sdk1.7-oracle'
    '/usr/lib/jvm/j2sdk1.7-oracle/jre'
    '/usr/lib/jvm/java-7-oracle'
  )

  local OPENJAVA7_HOME_CANDIDATES=(
    '/usr/lib/jvm/java-1.7.0-openjdk'
    '/usr/lib/jvm/java-7-openjdk'
  )

  local JAVA8_HOME_CANDIDATES=(
    '/usr/java/jdk1.8'
    '/usr/java/jre1.8'
    '/usr/lib/jvm/j2sdk1.8-oracle'
    '/usr/lib/jvm/j2sdk1.8-oracle/jre'
    '/usr/lib/jvm/java-8-oracle'
  )

  local OPENJAVA8_HOME_CANDIDATES=(
    '/usr/lib/jvm/java-1.8.0-openjdk'
    '/usr/lib/jvm/java-8-openjdk'
  )

  local MISCJAVA_HOME_CANDIDATES=(
    '/Library/Java/Home'
    '/usr/java/default'
    '/usr/lib/jvm/default-java'
    '/usr/lib/jvm/java-openjdk'
    '/usr/lib/jvm/jre-openjdk'
  )

  case ${BIGTOP_JAVA_MAJOR} in
    6) JAVA_HOME_CANDIDATES=(${JAVA6_HOME_CANDIDATES[@]})
       ;;
    7) JAVA_HOME_CANDIDATES=(${JAVA7_HOME_CANDIDATES[@]} ${OPENJAVA7_HOME_CANDIDATES[@]})
       ;;
    8) JAVA_HOME_CANDIDATES=(${JAVA8_HOME_CANDIDATES[@]} ${OPENJAVA8_HOME_CANDIDATES[@]})
       ;;
    *) JAVA_HOME_CANDIDATES=(${JAVA7_HOME_CANDIDATES[@]}
                             ${JAVA8_HOME_CANDIDATES[@]}
                             ${JAVA6_HOME_CANDIDATES[@]}
                             ${MISCJAVA_HOME_CANDIDATES[@]}
                             ${OPENJAVA7_HOME_CANDIDATES[@]}
                             ${OPENJAVA8_HOME_CANDIDATES[@]}
                             ${OPENJAVA6_HOME_CANDIDATES[@]})
       ;;
  esac

  # attempt to find java
  if [ -z "${JAVA_HOME}" ]; then
    for candidate_regex in ${JAVA_HOME_CANDIDATES[@]}; do
        for candidate in `ls -rvd ${candidate_regex}* 2>/dev/null`; do
          if [ -e ${candidate}/bin/java ]; then
            export JAVA_HOME=${candidate}
            break 2
          fi
        done
    done
  fi

  verify_java_home
}

# Verify that JAVA_HOME set - does not verify that it's set to a meaningful
# value.
verify_java_home() {
  if [ -z "$JAVA_HOME" ]; then
    cat 1>&2 <<EOF
+======================================================================+
|      Error: JAVA_HOME is not set and Java could not be found         |
+----------------------------------------------------------------------+
| Please download the latest Oracle JDK from the Oracle Java web site  |
|  > http://www.oracle.com/technetwork/java/javase/index.html <        |
|                                                                      |
| Cloudera Manager requires Java 1.6 or later.                         |
| NOTE: This script will find Oracle Java whether you install using    |
|       the binary or the RPM based installer.                         |
+======================================================================+
EOF
    exit 1
  fi

  echo "JAVA_HOME=$JAVA_HOME"
}

parse_arguments()
{
  # Test that we're using compatible getopt version.
  getopt -T > /dev/null
  if [[ $? -ne 4 ]]; then
    echo "Incompatible getopt version."
    exit 1
  fi

  # Parse short and long option parameters.
  DB_TYPE=
  DB_HOST=
  DB_PORT=
  DB_USER=
  DB_PASSWORD=
  SCM_DATABASE=
  SCM_USER=
  SCM_PASSWORD=
  SCM_HOST=
  SCM_CONFIG_PATH=
  GETOPT=`getopt -n $0 -o h:,P:,u:,p::,f,v,? \
      -l help,verbose,force,host:,port:,user:,password::,scm-host:,config-path: \
      -- "$@"`
  eval set -- "$GETOPT"
  while true;
  do
    case "$1" in
    -h|--host)
      DB_HOST=$2
      shift 2
      ;;
    -P|--port)
      DB_PORT=$2
      shift 2
      ;;
    -u|--user)
      DB_USER=$2
      shift 2
      ;;
    -p|--password)
      case "$2" in
      "")
        read -esp "Enter database password: " DB_PASSWORD
        echo
        ;;
      *)
        DB_PASSWORD=$2
        ;;
      esac
      shift 2
      ;;
    --scm-host)
      SCM_HOST=$2
      shift 2
      ;;
    --config-path)
      SCM_CONFIG_PATH=$2
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -f|--force)
      FORCE=1
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      exit 1
      ;;
    esac
  done

  # Parse all non-option parameters. Extra parameters are ignored.
  DB_TYPE=$1
  SCM_DATABASE=$2
  SCM_USER=$3
  SCM_PASSWORD=$4

  case $DB_TYPE in
  mysql|postgresql|oracle)
    # ok
    ;;
  *)
    echo "Unknown database type: $DB_TYPE"
    usage
    exit 1
  esac

  # These must be set to continue.
  if [[ -z $DB_TYPE ]] || [[ -z $SCM_DATABASE ]] || [[ -z $SCM_USER ]]; then
    usage
    exit 1
  fi

  # Prompt for SCM password if it was not provided.
  if [[ -z $SCM_PASSWORD ]]; then
    read -esp "Enter SCM password: " SCM_PASSWORD
    echo
  fi

  if [[ -z $SCM_HOST ]]; then
    SCM_HOST="localhost"
  fi

  if [[ -z $DB_HOST ]]; then
    DB_HOST="localhost"
  fi

  if [[ $DB_PORT ]]; then
    DB_HOSTPORT="$DB_HOST:$DB_PORT"
  else
    DB_HOSTPORT="$DB_HOST"
  fi
}

check_config_writable()
{
  if [[ -z $SCM_CONFIG_PATH ]]; then
    SCM_CONFIG_PATH=$CMF_CONFIG_DIR
  fi
  SCM_ABS_CONFIG_PATH=`readlink -m "$SCM_CONFIG_PATH"`
  echo "Verifying that we can write to $SCM_ABS_CONFIG_PATH"
  check_can_mkdir_path $SCM_CONFIG_PATH
  fail_or_continue $? "--> Cannot write to $SCM_ABS_CONFIG_PATH"
}

#
# Create a user and database to bootstrap. Do it only if the database user
# is provided. If it is not specified, then assume that database is being
# provided to us and skip this step. Also skip this step if the database
# type is Oracle (we would like oracle dba to do this).
#
create_user_and_database()
{
  verbose echo "Database type: " $DB_TYPE
  verbose echo "Database user: " $DB_USER

  if [[ $DB_TYPE == "oracle" ]] || [[ -z $DB_USER ]]; then
    return;
  fi

  JAVA="$JAVA_HOME/bin/java"

  local MGMT_CLASSPATH="$CMF_JDBC_DRIVER_JAR:$SCRIPT_DIR/../lib/*:/usr/share/java/mysql-connector-java.jar"

  CREATE_CMD="${JAVA} -cp ${MGMT_CLASSPATH} com.cloudera.enterprise.dbutil.DbProvisioner --create"
  CREATE_CMD="${CREATE_CMD} -h $DB_HOSTPORT -u $DB_USER"
  CREATE_CMD="${CREATE_CMD} -H $SCM_HOST -U $SCM_USER -d $SCM_DATABASE -t $DB_TYPE"
  ECHO_CMD=$CREATE_CMD

  if [[ -n $DB_PASSWORD ]]; then
      CREATE_CMD="${CREATE_CMD} -p $DB_PASSWORD"
  fi

  if [[ -n $SCM_PASSWORD ]]; then
      CREATE_CMD="${CREATE_CMD} -P $SCM_PASSWORD"
  fi

  verbose echo "Executing: " $ECHO_CMD
  $CREATE_CMD

  fail_or_continue $?
}

write_config_file()
{
  # Write out the configuration file.
  echo "Creating SCM configuration file in $SCM_CONFIG_PATH"
  mkdir -p $SCM_CONFIG_PATH
  fail_or_continue $?
  DB_PROPERTIES_TMP_FILE=$(mktemp /tmp/XXXXXXXX)

  # Fix the ownership and permission bits so that SCM can read it
  chmod 600 $DB_PROPERTIES_TMP_FILE
  fail_or_continue $?

  # Check that there is a cloudera-scm user and group
  # 'groups' will fail if there is no user
  # 'grep' will fail if the user is not a member of the group
  groups cloudera-scm | grep -q cloudera-scm
  if [[ $? -eq 0 ]]; then
    chown cloudera-scm:cloudera-scm $DB_PROPERTIES_TMP_FILE
    fail_or_continue $?
  fi

  cat > $DB_PROPERTIES_TMP_FILE << EOF
# Auto-generated by `basename $0` on `date`
#
# For information describing how to configure the Cloudera Manager Server
# to connect to databases, see the "Cloudera Manager Installation Guide."
#
com.cloudera.cmf.db.type=$DB_TYPE
com.cloudera.cmf.db.host=$DB_HOSTPORT
com.cloudera.cmf.db.name=$SCM_DATABASE
com.cloudera.cmf.db.user=$SCM_USER
com.cloudera.cmf.db.password=$SCM_PASSWORD
EOF

  fail_or_continue $?
  mv --backup=numbered $DB_PROPERTIES_TMP_FILE $SCM_CONFIG_PATH/db.properties
  fail_or_continue $?
  verbose echo "Created db.properties file:"
  INDENT="sed -e s/^/\t/"
  verbose cat $SCM_CONFIG_PATH/db.properties | $INDENT
}

# NOTE: write_config_file should be called to generate db.properties file
test_db_connection()
{
  JAVA="$JAVA_HOME/bin/java"

  local DB_PROPERTY_PREFIX="com.cloudera.cmf.db."
  local MGMT_CLASSPATH="$CMF_JDBC_DRIVER_JAR:$SCRIPT_DIR/../lib/*:/usr/share/java/mysql-connector-java.jar"

  echo "Executing: " ${JAVA} -cp "${MGMT_CLASSPATH}" com.cloudera.enterprise.dbutil.DbCommandExecutor $SCM_CONFIG_PATH/db.properties $DB_PROPERTY_PREFIX
  ${JAVA} -cp "${MGMT_CLASSPATH}" com.cloudera.enterprise.dbutil.DbCommandExecutor $SCM_CONFIG_PATH/db.properties $DB_PROPERTY_PREFIX
  fail_or_continue $?
}

main "$@"
