import shutil

from charms.reactive import when_all, when_not, set_flag, clear_flag
from charmhelpers.core import hookenv

from charms import layer


@when_all('apt.installed.vaultlocker',
          'layer.vault-kv.ready',
          'layer.vault-kv.config.changed')
def configure_vaultlocker():
    # write VaultLocker config file
    layer.vaultlocker.write_vaultlocker_conf(layer.vault_kv.get_vault_config())
    # create location for loop device service envs
    layer.vaultlocker.LOOP_ENVS.mkdir(parents=True, exist_ok=True)
    # create loop device service template
    shutil.copyfile('templates/vaultlocker-loop@.service',
                    '/etc/systemd/system/vaultlocker-loop@.service')
    # mark as complete
    set_flag('layer.vaultlocker.configured')
    clear_flag('layer.vault-kv.config.changed')


@when_all('layer.vaultlocker.configured')
@when_not('layer.vaultlocker.ready')
def auto_encrypt():
    metadata = hookenv.metadata()
    for storage_name, storage_metadata in metadata.get('storage', {}).items():
        if storage_metadata.get('vaultlocker-encrypt', False):
            mountbase = storage_metadata.get('vaultlocker-mountbase')
            layer.vaultlocker.encrypt_storage(storage_name, mountbase)
    set_flag('layer.vaultlocker.ready')
