from functools import wraps
import logging
import sys
import time

import yaml

from ansible.module_utils.basic import AnsibleModule

from cm_api.api_client import ApiResource, ApiException
from cm_api.endpoints.services import ApiServiceSetupInfo


LOG = logging.getLogger(__name__)

CDH = 'CDH'
REMOTE_PARCEL_REPO_URLS = 'REMOTE_PARCEL_REPO_URLS'

SERVICE_ORDER = ['Zookeeper', 'Hdfs', 'Yarn']


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


def set_loggger():
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s:%(lineno)d:: %(message)s')
    ch.setFormatter(formatter)
    LOG.addHandler(ch)
    LOG.setLevel(logging.DEBUG)


def fail(module, msg):
    if module:
        module.fail_json(msg=msg)
    else:
        LOG.error(msg)
        sys.exit(1)


class Parcels(object):

    def __init__(self, module, manager, cluster, version, repo):
        self.module = module
        self.manager = manager
        self.cluster = cluster
        self.version = version
        self.repo = repo
        self.validate()

    @property
    def parcel(self):
        return self.cluster.get_parcel(CDH, self.version)

    def check_error(self, parcel):
        if parcel.state.errors:
            fail(self.module, parcel.state.errors)

    def validate(self):
        @retry()
        def wait_parcel():
            return self.parcel

        try:
            self.check_error(self.cluster.get_parcel(CDH, self.version))
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
        parcel = self.parcel
        self.check_error(parcel)
        if parcel.stage in states:
            return
        else:
            LOG.info("Parcel %s progress: %s / %s"
                     % (states[0], parcel.state.progress, parcel.state.totalProgress))
            raise ApiException("Waiting on parcel to get to state {}".format(states[0]))

    def download(self):
        self.parcel.start_download()
        self.check_state(['DOWNLOADED', 'DISTRIBUTED', 'ACTIVATED', 'INUSE'])

    def distribute(self):
        self.parcel.start_distribution()
        self.check_state(['DISTRIBUTED', 'ACTIVATED', 'INUSE'])

    def activate(self):
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
        self.name = self.__class__.__name__.upper()
        self.type = type or self.name
        self.service = None

    def deploy(self):
        LOG.info("[%s] Deploying service", self.name)
        try:
            self.service = self.cluster.get_service(self.name)
        except ApiException:
            self.service = self.cluster.create_service(self.name, self.type)
        self.service.update_config(self.config.get('config', {}))
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
        role_id = 0
        for host in role['hosts']:
            role_id += 1
            role_name = '{}-{}-{}'.format(self.name, group, role_id)
            try:
                self.service.get_role(role_name)
            except ApiException:
                self.service.create_role(role_name, group, host)

    def pre_start(self):
        raise NotImplementedError("Functionality specific to each service needs to be implemented")

    def post_start(self):
        raise NotImplementedError("Functionality specific to each service needs to be implemented")


class Zookeeper(Service):

    def create_roles(self, role, group):
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
        LOG.info("[%s] Initializing Zookeeper", self.name)
        self.service.init_zookeeper()


class Hdfs(Service):

    def pre_start(self):
        LOG.info("[%s] Formatting HDFS Namenode", self.name)
        cmds = self.service.format_hdfs('{}-NAMENODE-1'.format(self.name))
        for cmd in cmds:
            if not cmd.wait(60).active:
                LOG.warn("[%s] Failed formatting HDFS, continuing with setup. %s",
                         self.name, cmd.resultMessage)

    def post_start(self):
        self.service = self.cluster.get_service(self.name)
        self.service.create_hdfs_tmp()


class Yarn(Service):

    def pre_start(self):
        pass


class ClouderaManager(object):

    def __init__(self, module, config):
        self.api = ApiResource(config['cm']['host'], username=config['cm']['username'],
                               password=config['cm']['password'])
        self.manager = self.api.get_cloudera_manager()
        self.config = config
        self.module = module
        self.cluster = None
        LOG.debug(config)

    def create_cluster(self):
        cluster_config = self.config['cluster']
        try:
            self.cluster = self.api.get_cluster(cluster_config['name'])
        except ApiException:
            LOG.info("Creating Cluster entity: %s", cluster_config['name'])
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

    @retry(attempts=20, delay=5)
    def wait_inspect_hosts(self, cmd):
        cmd = cmd.fetch()
        if cmd.success is None:
            raise ApiException("Waiting on command {} to finish".format(cmd))
        elif not cmd.success:
            fail(self.module, 'Host inspection failed')
        LOG.info("Host inspection completed: %s", cmd.resultMessage)

    def deploy_mgmt_services(self):
        LOG.info("Deploying Management Services")
        try:
            mgmt = self.manager.get_service()
            if mgmt.serviceState == 'STARTED':
                return
        except ApiException:
            LOG.warn("[MGMT] Management Services don't exist. Creating...")
            mgmt = self.manager.create_mgmt_service(ApiServiceSetupInfo())

        for role in config['services']['MGMT']['roles']:
            if not len(mgmt.get_roles_by_type(role['group'])) > 0:
                LOG.info("[MGMT] Creating role for %s", role['group'])
                mgmt.create_role('{}-1'.format(role['group']), role['group'], role['hosts'][0])

        for role in config['services']['MGMT']['roles']:
            role_group = mgmt.get_role_config_group('mgmt-{}-BASE'.format(role['group']))
            role_group.update_config(role.get('config', {}))

        mgmt.start().wait()
        if self.manager.get_service().serviceState == 'STARTED':
            LOG.info("[MGMT] Management Services started")
        else:
            fail(self.module, "[MGMT] Cloudera Management services didn't start up properly")

    def setup(self):
        # TODO(rnirmal): How to handle licenses?
        # TODO(rnirmal): Cloudera Manager SSL?

        # Create the cluster entity and associate hosts
        LOG.info("Creating cluster...")
        self.create_cluster()

        # Download and activate the parcels
        LOG.info("Setting up parcels...")
        parcel = Parcels(self.module, self.manager, self.cluster,
                         self.config['parcel']['version'], self.config['parcel']['repo'])
        parcel.download()
        parcel.distribute()
        parcel.activate()

        # Inspect all the hosts
        LOG.info("Inspecting hosts...")
        self.wait_inspect_hosts(self.manager.inspect_hosts())

        # Create Management services
        self.deploy_mgmt_services()

        # Create services
        for service in SERVICE_ORDER:
            service_config = self.config['services'].get(service.upper())
            if service_config:
                svc = getattr(sys.modules[__name__], service)(self.cluster, service_config)
                svc.deploy()
                svc.pre_start()

        # Start the cluster
        LOG.info("Starting up the Cluster")
        self.cluster.stop().wait()
        self.cluster.start().wait()
        Hdfs(self.cluster, {}).post_start()

        # Deploy all the client configs
        self.cluster.deploy_client_config()


if __name__ == '__main__':
    set_loggger()
    module = None
    try:
        argument_spec = dict(
            template=dict(type='str', default='/opt/cluster.yaml')
        )

        module = AnsibleModule(
            argument_spec=argument_spec
        )

        yaml_template = module.params.get('template')

        if not yaml_template:
            fail(module, msg='The cluster configuration template is not available')
    except ValueError as e:
        LOG.warn("Skipping ansible run and running locally")
        yaml_template = 'cluster.yaml'

    try:
        with open(yaml_template, 'r') as cluster_yaml:
            config = yaml.load(cluster_yaml)
        cm = ClouderaManager(module, config)
        cm.setup()
    except IOError as e:
        fail(module, 'Error loading cluster yaml config')
