from charms.reactive import when_all, when_not, set_flag
from charms.reactive import endpoint_from_flag
from charms.reactive import data_changed
from charmhelpers.core import hookenv
from charmhelpers.core import unitdata

from charms.layer import vaultlocker


@when_all('vault.connected')
@when_not('layer.vaultlocker.requested')
def request_vault():
    vault = endpoint_from_flag('vault.available')
    app_name = hookenv.application_name()
    secret_backend = 'vaultlocker-{}'.format(app_name)
    vault.request_secret_backend(secret_backend)


@when_all('apt.installed.vaultlocker',
          'vault.available')
@when_not('layer.vaultlocker.configured')
def configure_vaultlocker():
    vault = endpoint_from_flag('vault.available')
    vault_url = vault.vault_url
    role_id = vault.unit_role_id
    token = vault.unit_token
    app_name = hookenv.application_name()
    secret_backend = 'vaultlocker-{}'.format(app_name)
    if data_changed('layer.vaultlocker.token', token):
        # fetch new secret ID
        secret_id = vaultlocker.retrieve_secret_id(vault_url, token)
        unitdata.kv().set('layer.vaultlocker.secret_id', secret_id)
    else:
        secret_id = unitdata.kv().get('layer.vaultlocker.secret_id')
    vaultlocker.write_vaultlocker_conf({
        'vault_url': vault_url,
        'role_id': role_id,
        'secret_backend': secret_backend,
        'secret_id': secret_id,
    })
    set_flag('layer.vaultlocker.configured')


@when_all('layer.vaultlocker.configured')
@when_not('layer.vaultlocker.ready')
def auto_encrypt():
    metadata = hookenv.metadata()
    for storage_name, storage_metadata in metadata.get('storage', {}).items():
        if storage_metadata.get('vaultlocker-encrypt', False):
            mountbase = storage_metadata.get('vaultlocker-mountbase')
            vaultlocker.encrypt_storage(storage_name, mountbase)
    set_flag('layer.vaultlocker.ready')
