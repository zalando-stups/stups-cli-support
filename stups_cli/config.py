
import click
import dns.resolver
import os
import requests
import yaml
from clickclick import Action, info


def get_path(section):
    # "old" style config files (one file per app)
    directory = click.get_app_dir(section)
    path = os.path.join(directory, '{}.yaml'.format(section))
    return path


def load_config(section):
    path = get_path(section)
    try:
        with open(path, 'rb') as fd:
            config = yaml.safe_load(fd)
    except:
        config = None
    return config or {}


def store_config(config, section):
    path = get_path(section)
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(path, 'w') as fd:
        yaml.dump(config, fd)


def configure():
    while True:
        errors = None
        autoconfigs = {}
        urls = {}
        domain = click.prompt('Please enter your STUPS domain (e.g. "stups.example.org")')

        for component in ('mai', 'zign'):

            with Action('Trying to autoconfigure {}..'.format(component)) as act:
                try:
                    answer = dns.resolver.query('_{}._autoconfig.{}'.format(component, domain), 'TXT')
                    for rdata in answer.rrset.items:
                        for string in rdata.strings:
                            autoconfigs[component] = yaml.safe_load(string)
                except:
                    act.error('ERROR')
                    errors = True

        for component in ('pierone', 'even'):
            url = 'https://{}.{}'.format(component, domain)
            with Action('Checking {}..'.format(url)) as act:
                try:
                    requests.get(url, timeout=5)
                except:
                    act.error('ERROR')
                    errors = True

            urls[component] = url

        if not errors:
            with Action('Writing config for Pier One..'):
                store_config({'url': urls['pierone']}, 'pierone')
            with Action('Writing config for Più..'):
                store_config({'even_url': urls['even']}, 'piu')
            with Action('Writing config for Zign..'):
                store_config({'url': autoconfigs.get('zign', {}).get('token_service_url')}, 'zign')

            info('Now use "mai create .." to configure your AWS profile(s).')
            info('SAML identity provider URL: {}'.format(autoconfigs.get('mai', {}).get('saml_identity_provider_url')))
            info('SAML username pattern:      {}'.format(autoconfigs.get('mai', {}).get('saml_user_pattern')))

        if not errors:
            break
