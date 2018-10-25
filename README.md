# VaultLocker Base Layer

This layer manages integration with VaultLocker to automatically encrypt
block devices and automatically unlocking them at boot.

# Usage

## Using Juju Storage Annotations

The easiest way to use this layer is to define a block device storage entry in
your `metadata.yaml` and annotate it with `vaultlocker-encrypt: true` to mark
it to be encrypted, and optionally `vaultlocker-mountbase: path` to specify a
location to have the decrypted mapped device mounted.  The actual mountpoint
will be `{mountbase}/{storage_name}` for "single" storage endpoints, or
`{mountbase}/{storage_name}/{storage_id_num}` for "multiple" storage endpoints.

The following flags will be set to let your charm know when your block devices
have been encrypted and optionally mounted:

* `layer.vaultlocker.{storage_name}.ready` Set when the given storage endpoint
  has one or more devices encrypted and mounted.

* `layer.vaultlocker.{storage_id}.ready` Set for each device that is encrypted
  and mounted.

For example:

```yaml
storage:
  secrets:
    type: block
    vaultlocker-encrypt: true
    vaultlocker-mountbase: /mnt/myapp
```

With that, when Vault is related to your charm via the `vault` relation
endpoint provided by this layer, the `secrets` device will automatically be
encrypted and an XFS filesystem created on it which will then mounted at
`/mnt/myapp/secrets`.


## Using the Library

Alternatively, you can manually encrypt a storage entry or arbitrary block
device using the library:

```python
from charms.reactive import when_all, when_not, set_flag

from charms.layer import vaultlocker


@when_all('config.set.encrypt',
          'layer.vaultlocker.ready')
@when_not('charm.foo.encrypted')
def encrypt():
    vaultlocker.encrypt_storage('secrets', mountbase='/mnt/myapp')
    device_name = '/dev/sdd1'
    vaultlocker.encrypt_device(device_name, mountpoint='/mnt/mysecrets')
    decrypted_device_name = vaultlocker.decrypted_device(device_name)
    # use the decrypted_device_name in place of device_name
    set_flag('charm.foo.encrypted')
```


# Reference

More details can be found in the [docs](docs/vaultlocker.md).
