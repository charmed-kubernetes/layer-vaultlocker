from charms.reactive import when_all, when_not, set_flag, clear_flag
from charmhelpers.core import hookenv

from charms.layer import vault_kv
from charms.layer import vaultlocker


@when_all('apt.installed.vaultlocker',
          'layer.vault-kv.ready',
          'layer.vault-kv.config.changed')
def configure_vaultlocker():
    vaultlocker.write_vaultlocker_conf(vault_kv.get_vault_config())
    set_flag('layer.vaultlocker.configured')
    clear_flag('layer.vault-kv.config.changed')


@when_all('layer.vaultlocker.configured')
@when_not('layer.vaultlocker.ready')
def auto_encrypt():
    metadata = hookenv.metadata()
    for storage_name, storage_metadata in metadata.get('storage', {}).items():
        if storage_metadata.get('vaultlocker-encrypt', False):
            mountbase = storage_metadata.get('vaultlocker-mountbase')
            vaultlocker.encrypt_storage(storage_name, mountbase)
    set_flag('layer.vaultlocker.ready')
