from pathlib import Path
from subprocess import check_call
from uuid import uuid4

from charms.reactive import set_flag
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers.core import unitdata
from charmhelpers.contrib.openstack.vaultlocker import (  # noqa
    retrieve_secret_id,
    write_vaultlocker_conf,
)
from charmhelpers.contrib.storage.linux.utils import (
    is_block_device,
    is_device_mounted,
    mkfs_xfs,
)


def encrypt_storage(storage_name, mountbase=None):
    """
    Set up encryption for the given Juju storage entry, and optionally create
    and mount XFS filesystems on the encrypted storage entry location(s).

    Note that the storage entry **must** be defined with ``type: block``.

    If ``mountbase`` is not given, the location(s) will not be formatted or
    mounted.  When interacting with or mounting the location(s) manually, the
    name returned by :func:`decrypted_device` called on the storage entry's
    location should be used in place of the raw location.

    If the storage is defined as ``multiple``, the individual locations
    will be mounted at ``{mountbase}/{storage_name}/{num}`` where ``{num}``
    is based on the storage ID.  Otherwise, the storage will mounted at
    ``{mountbase}/{storage_name}``.
    """
    metadata = hookenv.metadata()
    storage_metadata = metadata['storage'][storage_name]
    if storage_metadata['type'] != 'block':
        raise ValueError('Cannot encrypt non-block storage: '
                         '{}'.format(storage_name))
    multiple = 'multiple' in storage_metadata
    for storage_id in hookenv.storage_list():
        if not storage_id.startswith(storage_name + '/'):
            continue
        storage_location = hookenv.storage_get('location', storage_id)
        if mountbase and multiple:
            mountpoint = Path(mountbase) / storage_id
        elif mountbase:
            mountpoint = Path(mountbase) / storage_name
        else:
            mountpoint = None
        encrypt_device(storage_location, mountpoint)
        set_flag('layer.vaultlocker.{}.ready'.format(storage_id))
        set_flag('layer.vaultlocker.{}.ready'.format(storage_name))


def encrypt_device(device, mountpoint=None):
    """
    Set up encryption for the given block device, and optionally create and
    mount an XFS filesystem on the encrypted device.

    If ``mountbase`` is not given, the device will not be formatted or
    mounted.  When interacting with or mounting the device manually, the
    name returned by :func:`decrypted_device` called on the device name
    should be used in place of the raw device name.
    """
    if not is_block_device(device):
        raise ValueError('Cannot encrypt non-block device: {}'.format(device))
    if is_device_mounted(device):
        raise ValueError('Cannot encrypt mounted device: {}'.format(device))
    hookenv.log('Encrypting device: {}'.format(device))
    uuid = str(uuid4())
    check_call(['vaultlocker', 'encrypt', '--uuid', uuid, device])
    unitdata.kv().set('layer.vaultlocker.uuids.{}'.format(device), uuid)
    if mountpoint:
        mapped_device = decrypted_device(device)
        hookenv.log('Creating filesystem on {} ({})'.format(mapped_device,
                                                            device))
        mkfs_xfs(mapped_device)
        Path(mountpoint).mkdir(mode=0o755, parents=True, exist_ok=True)
        hookenv.log('Mounting filesystem for {} ({}) at {}'
                    ''.format(mapped_device, device, mountpoint))
        host.mount(mapped_device, mountpoint, filesystem='xfs')
        host.fstab_add(mapped_device, mountpoint, 'xfs', ','.join([
            "defaults",
            "nofail",
            "x-systemd.requires=vaultlocker-decrypt@{uuid}.service".format(
                uuid=uuid,
            ),
            "comment=vaultlocker",
        ]))


def decrypted_device(device):
    """
    Returns the mapped device name for the decrypted version of the encrypted
    device.

    This mapped device name is what should be used for mounting the device.
    """
    uuid = unitdata.kv().get('layer.vaultlocker.uuids.{}'.format(device))
    if not uuid:
        return None
    return '/dev/mapper/crypt-{uuid}'.format(uuid=uuid)
