#!/usr/bin/python  
# This file is part of Ansible

# This module performs the cluster configuration and installation from start to finish
# given the services, configuration and host information. All the information required
# should be provided in a cluster.yaml file

# All the services are handled based on what is provided in the configuration.
# Note: For any new service a `Service` class will need to be implemented.

from functools import wraps
import yaml

from ansible.module_utils.basic import *

from cm_api.api_client import ApiResource, ApiException
from cm_api.endpoints.services import ApiServiceSetupInfo


REMOTE_PARCEL_REPO_URLS = 'REMOTE_PARCEL_REPO_URLS'

# List of services to configure in the specified order. The names
# need to match with the names of the respective `Service` subclasses.
# BASE_SERVICES contains a list of services that will be started first, before the
# rest of the services are configured, since some of them depend on for example creating
# directories on HDFS.
BASE_SERVICES = ['Zookeeper', 'Hdfs', 'Yarn']
ADDITIONAL_SERVICES = ['Spark_On_Yarn', 'Hbase', 'Hive', 'Impala', 'Flume', 'Oozie', 'Sqoop',
                       'Solr', 'Kafka', 'Sentry', 'Hue']


def retry(attempts=3, delay=5):
    """Function which reruns/retries other functions.

    'attempts' - the number of attempted retries (defaults to 3)
    'delay' - time in seconds between each retry (defaults to 5)
    """
    def deco_retry(func):
        """Main decorator function."""
        @wraps(func)
        def retry_loop(*args, **kwargs):
            """Main num_tries loop."""
            attempt_counter = 1
            while attempt_counter <= attempts:
                try:
                    return func(*args, **kwargs)
                except ApiException as apie:  # pylint: disable=broad-except,catching-non-exception
                    if attempt_counter == attempts:
                        # pylint: disable=raising-bad-type
                        raise
                    time.sleep(delay)
                    attempt_counter += 1
        return retry_loop
    return deco_retry


def print_json(**kwargs):
    """
    Print json output based on the passed in arguments
    """
    print json.dumps(kwargs)


def fail(module, msg):
    """
    Return a fail message for Ansible
    """
    if module:
        module.fail_json(msg=msg)
    else:
        print_json(msg=msg)
        sys.exit(1)


class Parcels(object):
    """
    Cloudera Parcels manager

    This class handles all the required operations on Parcels from downloading, distributing
    to activating it.
    """
    def __init__(self, module, manager, cluster, version, repo, product='CDH'):
        self.module = module
        self.manager = manager
        self.cluster = cluster
        self.version = version
        self.repo = repo
        self.product = product
        self.validate()

    @property
    def parcel(self):
        """
        :return: Parcel object from the CM API
        """
        return self.cluster.get_parcel(self.product, self.version)

    def check_error(self, parcel):
        """
        Check for errors in parcels

        :param parcel: Parcel object from the CM API
        """
        if parcel.state.errors:
            fail(self.module, parcel.state.errors)

    def validate(self):
        """
        Validate provided parcel configuration against the CM API
        """
        @retry()
        def wait_parcel():
            return self.parcel

        try:
            self.check_error(self.parcel)
        except ApiException:
            if self.repo is None:
                raise Exception("None of the existing repos contain the requested "
                                "parcel version. Please specify a parcel repo.")
            cm_config = self.manager.get_config(view='full')
            repo_config = cm_config[REMOTE_PARCEL_REPO_URLS]
            value = ','.join([repo_config.value or repo_config.default, self.repo])

            self.manager.update_config({REMOTE_PARCEL_REPO_URLS: value})
            self.check_error(wait_parcel())

    @retry(attempts=20, delay=30)
    def check_state(self, states):
        """
        Check parcel progress state

        :param states: List of possible states to test for
        """
        parcel = self.parcel
        self.check_error(parcel)
        if parcel.stage in states:
            return
        else:
            print_json(type=self.__class__.__name__.upper(),
                       msg="{} progress: {} / {}".format(states[0], parcel.state.progress,
                                                         parcel.state.totalProgress))
            raise ApiException("Waiting on parcel to get to state {}".format(states[0]))

    def download(self):
        """
        Download the specified parcel to the Cloudera Manager server
        """
        print_json(type=self.__class__.__name__.upper(),
                   msg="Downloading: {}-{}".format(self.product, self.version))
        self.parcel.start_download()
        self.check_state(['DOWNLOADED', 'DISTRIBUTED', 'ACTIVATED', 'INUSE'])

    def distribute(self):
        """
        Distribute the parcel to all the nodes
        """
        print_json(type=self.__class__.__name__.upper(),
                   msg="Distributing: {}-{}".format(self.product, self.version))
        self.parcel.start_distribution()
        self.check_state(['DISTRIBUTED', 'ACTIVATED', 'INUSE'])

    def activate(self):
        """
        Activate the parcel for use in the cluster installation step
        """
        print_json(type=self.__class__.__name__.upper(),
                   msg="Activating: {}-{}".format(self.product, self.version))
        self.parcel.activate()
        self.check_state(['ACTIVATED', 'INUSE'])


class Service(object):
    """
    Superclass to handle common repeatable functionality for each service

    Note: All subclass names should match an existing service name within CDH
    """

    def __init__(self, cluster, config, type=None):
        self.cluster = cluster
        self.config = config
        self.type = type or self.name
        self._service = None

    @property
    def name(self):
        """
        Name of the service as required by CM API
        :return: name
        """
        return self.__class__.__name__.upper()

    @property
    def service(self):
        """
        Create a service entity within the cluster context if one doesn't already exist
        :return: `ApiService` instance
        """
        if self._service is not None:
            return self._service

        try:
            self._service = self.cluster.get_service(self.name)
        except ApiException:
            self._service = self.cluster.create_service(self.name, self.type)
        return self._service

    @property
    def started(self):
        """
        Check if a service is already started and running.
        :return: service state Boolean
        """
        return True if self.service.serviceState == 'STARTED' else False

    @retry(attempts=10, delay=30)
    def run_cmd(self, func, timeout, fail_msg, *args, **kwargs):
        """
        Wrap retry checks for pre and post start commands that sometimes are not available to
        execute immediately after configuring or starting a service
        """
        cmd = func(*args, **kwargs)
        if not cmd.wait(timeout).success:
            if (cmd.resultMessage is not None and
                    "is not currently available for execution" in cmd.resultMessage):
                raise ApiException('Retry command')
            print_json(type=self.name, msg="{}. {}".format(fail_msg, cmd.resultMessage))

    def deploy(self):
        """
        Update group configs. Create roles and update role specific configs.
        """
        print_json(type=self.name, msg="Deploying service")

        # Service creation and config updates
        self.service.update_config(self.config.get('config', {}))

        # Retrieve base role config groups, update configs for those and create individual roles
        # per host
        if not self.config.get('roles'):
            raise Exception("[{}] Atleast one role should be specified per service".format(self.name))
        for role in self.config['roles']:
            if not role.get('group') and role.get('hosts'):
                raise Exception("[{}] group and hosts should be specified per role".format(self.name))
            group = role['group']
            role_group = self.service.get_role_config_group('{}-{}-BASE'.format(self.name, group))
            role_group.update_config(role.get('config', {}))
            self.create_roles(role, group)

    def create_roles(self, role, group):
        """
        Create individual roles for all the hosts under a specific role group

        :param role: Role configuration from yaml
        :param group: Role group name
        """
        role_id = 0
        for host in role['hosts']:
            role_id += 1
            role_name = '{}-{}-{}'.format(self.name, group, role_id)
            try:
                self.service.get_role(role_name)
            except ApiException:
                self.service.create_role(role_name, group, host)

    @retry(attempts=6, delay=10)
    def start(self):
        """
        Start the service and wait for the command to finish, followed by a check that the
        service is running and healthy
        """
        print_json(type=self.name, msg="Starting service")
        self._service = None
        if not self.started:
            cmd = self.service.start()
            if not cmd.wait(300).success:
                print_json(type=self.name,
                           msg="Command Service start failed. {}".format(cmd.resultMessage))
                if (cmd.resultMessage is not None and
                        'There is already a pending command on this entity' in cmd.resultMessage):
                    raise ApiException('Retry command')
                raise Exception("Service {} failed to start".format(self.name))

        self._service = None
        assert self.started

    def pre_start(self):
        """
        Any service specific actions that needs to be performed before the cluster is started.
        Each service subclass can implement and hook into the pre-start process.
        """
        pass

    def post_start(self):
        """
        Post cluster start actions required to be performed on a per service basis.
        """
        pass


class Zookeeper(Service):
    """
    Service Role Groups:
        SERVER
    """
    def create_roles(self, role, group):
        """
        This is overriden since there are some Zookeeper configs that has to be specific to
        a single host/role

        :param role: Role configuration from yaml
        :param group: Role group name
        """
        role_id = 0
        for host in role['hosts']:
            role_id += 1
            role_name = '{}-{}-{}'.format(self.name, group, role_id)
            try:
                role = self.service.get_role(role_name)
            except ApiException:
                role = self.service.create_role(role_name, group, host)
            role.update_config({'serverId': role_id})

    def pre_start(self):
        """
        Initialize Zookeeper for the first runs. This commands fails silently if it's rerun
        """
        print_json(type=self.name, msg="Initializing")
        self.run_cmd(self.service.init_zookeeper, 60, "Command InitZookeeper failed")


class Hdfs(Service):
    """
    Service Role Groups:
        NAMENODE
        SECONDARYNAMENODE
        DATANODE
        GATEWAY
    """
    def pre_start(self):
        print_json(type=self.name, msg="Formatting HDFS Namenode")
        cmds = self.service.format_hdfs('{}-NAMENODE-1'.format(self.name))
        for cmd in cmds:
            if not cmd.wait(300).success:
                print_json(type=self.name,
                           msg="Failed formatting HDFS, continuing with setup. {}".format(cmd.resultMessage))

    def post_start(self):
        self.run_cmd(self.service.create_hdfs_tmp, 60, "Command CreateHdfsTmp failed")


class Yarn(Service):
    """
    Service Role Groups:
        RESOURCEMANAGER
        JOBHISTORY
        NODEMANAGER
    """


class Spark_On_Yarn(Service):
    """
    This is the Spark on Yarn service

    Service Role Groups:
        HISTORYSERVER
        GATEWAY
    """
    def pre_start(self):
        self.run_cmd(self.service._cmd, 60, "Command CreateSparkUserDir failed",
                     'CreateSparkUserDirCommand', api_version=7)

        self.run_cmd(self.service._cmd, 60, "Command CreateSparkHistoryDirCommand failed",
                     'CreateSparkHistoryDirCommand', api_version=7)

        self.run_cmd(self.service._cmd, 60, "Command SparkUploadJarServiceCommand failed",
                     'SparkUploadJarServiceCommand', api_version=7)


class Hbase(Service):
    """
    Service Role Groups:
        MASTER
        REGIONSERVER
        HBASETHRIFTSERVER
        GATEWAY
    """
    def pre_start(self):
        self.run_cmd(self.service.create_hbase_root, 60, "Command CreateHbaseRoot failed")


class Hive(Service):
    """
    Service Role Groups:
        HIVEMETASTORE
        HIVESERVER2
        WEBHCAT
        GATEWAY
    """
    def pre_start(self):
        self.run_cmd(self.service.create_hive_warehouse, 60, "Command CreateHiveWarehouse failed")

    def post_start(self):
        pass
        # TODO(rnirmal): These commands keep failing, need to figure out why. Nothing useful in the
        # manager logs
        # self.run_cmd(self.service.create_hive_metastore_database, 60,
        #              "Command CreateHiveMetastoreDatabase failed")
        #
        # self.run_cmd(self.service.create_hive_metastore_tables, 60,
        #              "Command CreateHiveMetastoreTables failed")


class Impala(Service):
    """
    Service Role Groups:
        STATESTORE
        CATALOGSERVER
        IMPALAD
    """
    def pre_start(self):
        self.run_cmd(self.service.create_impala_user_dir, 60, "Command CreateImpalaUserDir failed")


class Flume(Service):
    """
    Service Role Groups:
        AGENT
    """


class Oozie(Service):
    """
    Service Role Groups:
        OOZIE_SERVER
    """
    def pre_start(self):
        self.run_cmd(self.service.create_oozie_db, 300, "Command CreateOozieSchema failed")

        self.run_cmd(self.service.install_oozie_sharelib, 300,
                     "Command InstallOozieSharedLib failed")


class Sqoop(Service):
    """
    Service Role Groups:
        SQOOP_SERVER
    """
    def pre_start(self):
        self.run_cmd(self.service.create_sqoop_user_dir, 300,
                     "Command CreateSqoopUserDir failed")
        self.run_cmd(self.service.create_sqoop_database_tables, 300,
                     "Command CreateSqoopDBTables failed")


class Solr(Service):
    """
    Service Role Groups:
        HUE_SERVER
    """
    def pre_start(self):
        self.run_cmd(self.service.init_solr, 300, "Command InitSolr failed")
        self.run_cmd(self.service.create_solr_hdfs_home_dir, 300,
                     "Command CreateSolrHdfsHomeDir failed")


class Hue(Service):
    """
    Service Role Groups:
        HUE_SERVER
    """


class Kafka(Service):
    """
    Service Role Groups:
        KAFKA_BROKER
    """


class Sentry(Service):
    """
    Service Role Groups:
        SENTRY_SERVER
    """
    def pre_start(self):
        self.run_cmd(self.service.create_sentry_database_tables, 300,
                     "Command CreateSentryDBTables failed")


class ClouderaManager(object):
    """
    The complete orchestration of a cluster from start to finish assuming all the hosts are
    configured and Cloudera Manager is installed with all the required databases setup.

    Handle all the steps required in creating a cluster. All the functions are built to function
    idempotently. So you should be able to resume from any failed step but running thru the
    __class__.setup()
    """

    def __init__(self, module, config, trial=False, license_txt=None):
        self.api = ApiResource(config['cm']['host'], username=config['cm']['username'],
                               password=config['cm']['password'])
        self.manager = self.api.get_cloudera_manager()
        self.config = config
        self.module = module
        self.trial = trial
        self.license_txt = license_txt
        self.cluster = None

    def enable_license(self):
        """
        Enable the requested license, either it's trial mode or a full license is entered and
        registered.
        """
        try:
            _license = self.manager.get_license()
        except ApiException:
            print_json(type="LICENSE", msg="Enabling license")
            if self.trial:
                self.manager.begin_trial()
            else:
                if license_txt is not None:
                    self.manager.update_license(license_txt)
                else:
                    fail(self.module, 'License should be provided or trial should be specified')

            try:
                _license = self.manager.get_license()
            except ApiException:
                fail(self.module, 'Failed enabling license')
        print_json(type="LICENSE",
                   msg="Owner: {}, UUID: {}".format(_license.owner, _license.uuid))

    def create_cluster(self):
        """
        Create a cluster and add hosts to the cluster. A new cluster is only created
        if another one doesn't exist with the same name.
        """
        print_json(type="CLUSTER", msg="Creating cluster")
        cluster_config = self.config['cluster']
        try:
            self.cluster = self.api.get_cluster(cluster_config['name'])
        except ApiException:
            print_json(type="CLUSTER",
                       msg="Creating Cluster entity: {}".format(cluster_config['name']))
            self.cluster = self.api.create_cluster(cluster_config['name'],
                                                   cluster_config['version'],
                                                   cluster_config['fullVersion'])

        cluster_hosts = [self.api.get_host(host.hostId).hostname
                         for host in self.cluster.list_hosts()]
        hosts = []
        for host in cluster_config['hosts']:
            if host not in cluster_hosts:
                hosts.append(host)
        self.cluster.add_hosts(hosts)

    def activate_parcels(self):
        print_json(type="PARCELS", msg="Setting up parcels")
        for parcel_cfg in self.config['parcels']:
            parcel = Parcels(self.module, self.manager, self.cluster,
                             parcel_cfg.get('version'), parcel_cfg.get('repo'),
                             parcel_cfg.get('product', 'CDH'))
            parcel.download()
            parcel.distribute()
            parcel.activate()

    @retry(attempts=20, delay=5)
    def wait_inspect_hosts(self, cmd):
        """
        Inspect all the hosts. Basically wait till the check completes on all hosts.

        :param cmd: A command instance used for tracking the status of the command
        """
        print_json(type="HOSTS", msg="Inspecting hosts")
        cmd = cmd.fetch()
        if cmd.success is None:
            raise ApiException("Waiting on command {} to finish".format(cmd))
        elif not cmd.success:
            if (cmd.resultMessage is not None and
                    'is not currently available for execution' in cmd.resultMessage):
                raise ApiException('Retry Command')
            fail(self.module, 'Host inspection failed')
        print_json(type="HOSTS", msg="Host inspection completed: {}".format(cmd.resultMessage))

    def deploy_mgmt_services(self):
        """
        Configure, deploy and start all the Cloudera Management Services.
        """
        print_json(type="MGMT", msg="Deploying Management Services")
        try:
            mgmt = self.manager.get_service()
            if mgmt.serviceState == 'STARTED':
                return
        except ApiException:
            print_json(type="MGMT", msg="Management Services don't exist. Creating.")
            mgmt = self.manager.create_mgmt_service(ApiServiceSetupInfo())

        for role in config['services']['MGMT']['roles']:
            if not len(mgmt.get_roles_by_type(role['group'])) > 0:
                print_json(type="MGMT", msg="Creating role for {}".format(role['group']))
                mgmt.create_role('{}-1'.format(role['group']), role['group'], role['hosts'][0])

        for role in config['services']['MGMT']['roles']:
            role_group = mgmt.get_role_config_group('mgmt-{}-BASE'.format(role['group']))
            role_group.update_config(role.get('config', {}))

        mgmt.start().wait()
        if self.manager.get_service().serviceState == 'STARTED':
            print_json(type="MGMT", msg="Management Services started")
        else:
            fail(self.module, "[MGMT] Cloudera Management services didn't start up properly")

    def service_orchestrate(self, services):
        """
        Create, pre-configure provided list of services
        Stop/Start those services
        Perform and post service startup actions

        :param services: List of Services to perform service specific actions
        """
        service_classes = []

        # Create and pre-configure provided services
        for service in services:
            service_config = self.config['services'].get(service.upper())
            if service_config:
                svc = getattr(sys.modules[__name__], service)(self.cluster, service_config)
                if not svc.started:
                    svc.deploy()
                    svc.pre_start()
                service_classes.append(svc)

        print_json(type="CLUSTER", msg="Starting services: {} on Cluster".format(services))

        # Deploy all the client configs, since some of the services depend on other services
        # and is essential that the client configs are in place
        self.cluster.deploy_client_config()

        # Start each service and run the post_start actions for each service
        for svc in service_classes:
            # Only go thru the steps if the service is not yet started. This helps with
            # re-running the script after fixing errors
            if not svc.started:
                svc.start()
                svc.post_start()

    def setup(self):
        # TODO(rnirmal): Cloudera Manager SSL?

        # Enable a full license or start a trial
        self.enable_license()

        # Create the cluster entity and associate hosts
        self.create_cluster()

        # Download and activate the parcels
        self.activate_parcels()

        # Inspect all the hosts
        self.wait_inspect_hosts(self.manager.inspect_hosts())

        # Create Management services
        self.deploy_mgmt_services()

        # Configure and Start base services
        self.service_orchestrate(BASE_SERVICES)

        # Configure and Start remaining services
        self.service_orchestrate(ADDITIONAL_SERVICES)


if __name__ == '__main__':
    module = None
    # Load all the variables passed in by Ansible
    try:
        argument_spec = dict(
            template=dict(type='str', default='/opt/cluster.yaml'),
            trial=dict(type='bool', default=False),
            license_txt=dict(type='str', default='')
        )

        module = AnsibleModule(
            argument_spec=argument_spec
        )

        yaml_template = module.params.get('template')
        trial = module.params.get('trial')
        license_txt = module.params.get('license_txt')

        if not yaml_template:
            fail(module, msg='The cluster configuration template is not available')
    except ValueError as e:
        print_json(msg="Skipping ansible run and running locally")
        yaml_template = 'cluster.yaml'
        trial = True
        license_txt = ''

    # Load the cluster.yaml template and create a Cloudera cluster
    try:
        with open(yaml_template, 'r') as cluster_yaml:
            config = yaml.load(cluster_yaml)
        cm = ClouderaManager(module, config, trial, license_txt)
        cm.setup()
        if module:
            module.exit_json(changed=True)
    except IOError as e:
        fail(module, "Error creating cluster {}".format(e))
