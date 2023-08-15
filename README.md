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
  --subvolume SUBVOLUME
                        Specify subvolume
  --device DEVICE       Specify subvolume
```

## Example
Create a config for a subvolume
```
# python3 main.py --subvolume @home --device /dev/sda1 create-config
Creating config
```
Take a snapshot
```
# python3 main.py --subvolume @ --device /dev/sda1 take-snapshot
taking snapshot
```
Delete a snapshot
```
# python3 main.py --subvolume @ --device /dev/sda1 delete-snapshot 1
```
Rollback to a snapshot
```
# python3 main.py --subvolume @ --device /dev/sda1 rollback 1
```
