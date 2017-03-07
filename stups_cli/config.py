import click
import dns.exception
import dns.resolver
import os
import requests
import subprocess
import yaml
from clickclick import Action, info


def get_path(section):
    # "old" style config files (one file per app)
    directory = click.get_app_dir(section)
    path = os.path.join(directory, '{}.yaml'.format(section))
    return path


def load_config(section):
    '''Get configuration for given section/project

    Tries to load YAML configuration file and also considers environment variables'''
    path = get_path(section)
    try:
        with open(path, 'rb') as fd:
            config = yaml.safe_load(fd)
    except:
        config = None
    config = config or {}
    env_prefix = '{}_'.format(section.upper().replace('-', '_'))
    for key, val in os.environ.items():
        if key.startswith(env_prefix):
            config_key = key[len(env_prefix):].lower()
            config[config_key] = val
    return config


def store_config(config, section):
    path = get_path(section)
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    try:
        with open(path, 'w') as fd:
            yaml.safe_dump(config, fd)
    except PermissionError:
        # we ignore permission errors here as users might make their config file readonly
        # to prevent corrupt files when running multiple processes
        pass


def is_valid_domain(domain):
    try:
        dns.resolver.query(domain, raise_on_no_answer=False)
        return True
    except:
        return False


def configure(preselected_domain=None):
    while True:
        errors = None
        autoconfigs = {}
        urls = {}

        existing_config = load_config('stups')
        # first use the provided domain
        domain = preselected_domain or existing_config.get('domain')

        while True:
            domain = click.prompt('Please enter your STUPS domain (e.g. "stups.example.org")', default=domain)
            if is_valid_domain(domain):
                break
            else:
                info('The entered domain is not valid. Please try again.')

        for component in ('mai', 'zign', 'zalando-token-cli',
                          'zalando-aws-cli', 'zalando-kubectl', 'zalando-deploy-cli'):

            with Action('Trying to autoconfigure {}..'.format(component)) as act:
                try:
                    answer = dns.resolver.query('_{}._autoconfig.{}'.format(component, domain), 'TXT')
                    for rdata in answer.rrset.items:
                        for string in rdata.strings:
                            autoconfigs[component] = yaml.safe_load(string)
                except dns.exception.DNSException as e:
                    act.error(str(e.__class__.__name__))
                    errors = True
                except Exception as e:
                    act.error('ERROR: {}'.format(e))
                    errors = True

        for component in ('pierone', 'even', 'fullstop', 'kio'):
            url = 'https://{}.{}'.format(component, domain)
            with Action('Checking {}..'.format(url)) as act:
                try:
                    requests.get(url, timeout=5, allow_redirects=False)
                except:
                    act.error('ERROR')
                    errors = True

            urls[component] = url

        token_service_url = autoconfigs.get('zign', {}).get('token_service_url')

        if token_service_url:
            username = existing_config.get('user') or os.getenv('USER')
            username = click.prompt('Please enter your OAuth username if it differs from $USER (e.g. "jdoe")',
                                    default=username)

        if not errors:
            with Action('Writing global config..'):
                store_config({'domain': domain}, 'stups')
            with Action('Writing config for Pier One..'):
                store_config({'url': urls['pierone']}, 'pierone')
            with Action('Writing config for Più..'):
                store_config({'even_url': urls['even']}, 'piu')
            with Action('Writing config for Fullstop..'):
                store_config({'url': urls['fullstop']}, 'fullstop')
            with Action('Writing config for Kio..'):
                store_config({'url': urls['kio']}, 'kio')
            with Action('Writing config for Zign..'):
                store_config({'url': token_service_url, 'user': username}, 'zign')
            if autoconfigs.get('zalando-token-cli'):
                with Action('Writing config for Zalando Token CLI..'):
                    store_config(autoconfigs['zalando-token-cli'], 'zalando-token-cli')
            if autoconfigs.get('zalando-aws-cli'):
                with Action('Writing config for Zalando AWS CLI..'):
                    store_config(autoconfigs['zalando-aws-cli'], 'zalando-aws-cli')
            if autoconfigs.get('zalando-kubectl'):
                with Action('Writing config for Zalando Kubectl..'):
                    store_config(autoconfigs['zalando-kubectl'], 'zalando-kubectl')
            if autoconfigs.get('zalando-deploy-cli'):
                with Action('Writing config for Zalando Deploy CLI..'):
                    store_config(autoconfigs['zalando-deploy-cli'], 'zalando-deploy-cli')

            user_pattern = autoconfigs.get('mai', {}).get('saml_user_pattern')
            if user_pattern:
                info('Now running "mai create-all" to configure your AWS profile(s)..')
                identity_provider_url = autoconfigs.get('mai', {}).get('saml_identity_provider_url')
                info('Please use the following pattern for your SAML username: {}'.format(user_pattern))
                returncode = subprocess.call(['mai', 'create-all', '--url', identity_provider_url])
                if returncode == 0:
                    info('You can now use "mai login .." to get temporary AWS credentials for your AWS account(s).')

        if errors:
            info('Automatic configuration failed. Please check the entered STUPS domain.')
            parts = domain.split('.')
            if len(parts) <= 2:
                domain = '.'.join(['stups'] + parts)
                info('The entered domain looks too short. Did you mean {}?'.format(domain))
            else:
                domain = '.'.join(['stups'] + parts[1:])
                info('The entered domain might be a team domain. Did you mean {}?'.format(domain))
        else:
            break
