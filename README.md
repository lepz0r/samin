# samin

Just a simple snapshot utility for btrfs

## Requirements

```
btrfsutil
pytz
tzlocal
psutil
```

## Installation

### Arch Linux

This program is available on AUR, you can install this program using an AUR helper for example how to install this program using paru:

```
paru -S samin
```

Also check out [samin-pacman-hook](https://gitlab.com/lepz0r/samin-pacman-hook) also avaible on AUR to automatically take a snapshot after running pacman.

### Manual

```
pip install .
```

## Usage

```
btrfs snapshot manager

positional arguments:
  {create-config,delete-config,take-snapshot,delete-snapshot,rollback,list-snapshots}
    create-config       Create a config
    delete-config       Delete a config
    take-snapshot       Take a snapshot
    delete-snapshot     Delete a snapshot
    rollback            Rollback to snapshot
    list-snapshots      List snapshots

options:
  -h, --help            show this help message and exit
  -s SUBVOLUME, --subvolume SUBVOLUME
                        Specify subvolume
  -b DEVICE, --device DEVICE
                        Specify subvolume
  -d, --debug           Enable debugging
  -u, --utc             Show time in UTC instead of local time
```

## Example

#### Create a config for a subvolume

```
# python -m samin --subvolume @home --device /dev/sda1 create-config
Creating config
```

#### Take a snapshot

```
# python -m samin --subvolume @ --device /dev/sda1 take-snapshot
taking snapshot
```

#### Delete a snapshot

```
# python -m samin --subvolume @ --device /dev/sda1 delete-snapshot 1
```

You can also specify multiple snapshots to delete-snapshot

```
# python -m samin --subvolume @ --device /dev/sda1 delete-snapshot 1-9
```

```
# python -m samin --subvolume @ --device /dev/sda1 delete-snapshot 2,4,6,8
```

#### Rollback to a snapshot

```
# python -m samin --subvolume @ --device /dev/sda1 rollback 1
```
