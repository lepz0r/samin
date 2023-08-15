import btrfsutil
import json
import os
import sys
import argparse
import shutil
import subprocess
import pytz
from pathlib import Path
from datetime import datetime
from tzlocal import get_localzone


def get_root_mountpoint():
    return "/run/samin/"


def get_confdir():
    return get_root_mountpoint() + ".samin"


def get_subvol_conf(subvol):
    return get_confdir() + "/" + subvol + "/"


def generate_snapshot_metadata(desc):
    date = datetime.utcnow()
    return {"date": date.strftime("%Y-%m-%dT%H:%M:%S"), "description": desc}


def mnt(device, mountpoint):
    try:
        if os.path.ismount(mountpoint) is False:
            command = ["mount", "-o", "subvolid=0", device, mountpoint]
            subprocess.check_call(command)
            return True
    except subprocess.CalledProcessError as e:
        print(e.output)
        return False


def mount_root_mountpoint(root_mountpoint, device):
    os.makedirs(root_mountpoint, exist_ok=True)
    mnt(device, root_mountpoint)


def umnt(mountpoint):
    subprocess.check_call(["umount", mountpoint])


def get_snapshot_metadatas(subvol, device, return_as_list=True):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)
    snapshot_location = subvol_confdir + "/snapshots/"
    metadatas = []

    if os.listdir(snapshot_location) == 0:
        print("No snapshot found")
        sys.exit(1)
    else:
        for snapshot in os.listdir(snapshot_location):
            with open(
                subvol_confdir + "/snapshots/" + snapshot + "/metadata.json"
            ) as metadata:
                current_metadata = json.loads(metadata.read())
                current_metadata["number"] = snapshot
                metadatas.append(current_metadata)

    umnt(root_mountpoint)

    if return_as_list is True:
        return metadatas
    else:
        print("| No.\t| Date\t\t\t\t| Description")
        for metadata in range(len(metadatas)):
            snp_date_obj = datetime.strptime(
                metadatas[metadata]["date"], "%Y-%m-%dT%H:%M:%S"
            )
            local_tz = get_localzone()
            snp_date_local = snp_date_obj.replace(tzinfo=pytz.utc).astimezone(local_tz)
            snp_date = datetime.strftime(snp_date_local, "%a %b %d %Y %H:%M:%S %p")
            print(
                "| "
                + metadatas[metadata]["number"]
                + "\t| "
                + snp_date
                + "\t| "
                + metadatas[metadata]["description"]
            )


def get_next_snapshot_number(dir):
    snapshot_dir = os.listdir(path=dir)

    if len(snapshot_dir) == 0:
        return "1"
    else:
        return str(int(snapshot_dir[-1]) + 1)


def create_config(subvol, device):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()
    confdir = get_confdir()

    mount_root_mountpoint(root_mountpoint, device)

    if Path(confdir).exists() is False:
        btrfsutil.create_subvolume(confdir)

    os.makedirs(subvol_confdir + "/snapshots", exist_ok=True)

    # with open(subvol_confdir+'config.json', 'w') as output:
    #  json.dump(metadata,output)

    umnt(root_mountpoint)


def delete_config(subvol, device):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)

    subvol_snapshots = os.listdir(subvol_confdir + "snapshots/")

    if len(subvol_confdir) != 0:
        for snapshot_number in subvol_snapshots:
            delete_snapshot(subvol, device, snapshot_number, False)

    shutil.rmtree(subvol_confdir)

    umnt(root_mountpoint)


def take_snapshot(subvol, device, desc="No description given"):
    subvol_conf = get_subvol_conf(subvol)
    metadata = generate_snapshot_metadata(desc)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)
    os.makedirs(subvol_conf + "snapshots", exist_ok=True)
    next_snapshot_number = get_next_snapshot_number(subvol_conf + "/snapshots")
    snapshot_dir = subvol_conf + "/snapshots/" + next_snapshot_number
    os.makedirs(snapshot_dir, exist_ok=True)
    btrfsutil.create_snapshot(
        root_mountpoint + subvol,
        subvol_conf + "/snapshots/" + next_snapshot_number + "/snapshot",
        read_only=True,
    )

    with open(snapshot_dir + "/metadata.json", "w") as output:
        json.dump(metadata, output, indent=2)

    umnt(root_mountpoint)


def delete_snapshot(subvol, device, snapshot_number, no_mount_op=False):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    if no_mount_op is False:
        mount_root_mountpoint(root_mountpoint, device)

    btrfsutil.delete_subvolume(
        subvol_confdir + "snapshots/" + snapshot_number + "/" + "snapshot"
    )
    shutil.rmtree(subvol_confdir + "snapshots/" + snapshot_number)

    if no_mount_op is True:
        umnt(root_mountpoint)


def rollback(subvol, device, snapshot_number):
    subvol_conf = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)
    metadata = generate_snapshot_metadata("rolled back to " + snapshot_number)

    os.makedirs(subvol_conf + "snapshots", exist_ok=True)
    next_snapshot_number = get_next_snapshot_number(subvol_conf + "/snapshots")
    snapshot_dir = subvol_conf + "/snapshots/" + next_snapshot_number
    os.makedirs(snapshot_dir, exist_ok=True)
    os.rename(
        root_mountpoint + subvol,
        subvol_conf + "snapshots/" + next_snapshot_number + "/snapshot",
    )
    btrfsutil.create_snapshot(
        subvol_conf + "snapshots/" + snapshot_number + "/" + "snapshot",
        root_mountpoint + subvol,
    )

    with open(snapshot_dir + "/metadata.json", "w") as output:
        json.dump(metadata, output, indent=2)

    umnt(root_mountpoint)


# Parser
def parser():
    parser = argparse.ArgumentParser(description="btrfs snapshot manager")
    subparser = parser.add_subparsers(dest="action")

    parser.add_argument("-s", "--subvolume", help="Specify subvolume", required=True)
    parser.add_argument("-d", "--device", help="Specify subvolume", required=True)

    c_config_parser = subparser.add_parser("create-config", help="Create a config")
    d_config_parser = subparser.add_parser("delete-config", help="Delete a config")

    take_snp_parser = subparser.add_parser("take-snapshot", help="Take a snapshot")
    take_snp_parser.add_argument(
        "--description", help="Specify description", default="No description given"
    )

    d_snp_parser = subparser.add_parser("delete-snapshot", help="Delete a snapshot")
    d_snp_num = d_snp_parser.add_argument("snapshot_number")

    rollback_parser = subparser.add_parser("rollback", help="Rollback to snapshot")
    rollback_num = rollback_parser.add_argument("snapshot_number")

    list_snp_parser = subparser.add_parser("list-snapshots", help="List snapshots")

    args = parser.parse_args()

    if args.action == "create-config":
        create_config(args.subvolume, args.device)
        print("Creating config")
    elif args.action == "take-snapshot":
        take_snapshot(args.subvolume, args.device, args.description)
        print("taking snapshot")
    elif args.action == "delete-snapshot":
        delete_snapshot(args.subvolume, args.device, args.snapshot_number)
    elif args.action == "rollback":
        rollback(args.subvolume, args.device, args.snapshot_number)
    elif args.action == "list-snapshots":
        get_snapshot_metadatas(args.subvolume, args.device, return_as_list=False)
    elif args.action == "delete-config":
        delete_config(args.subvolume, args.device)


if __name__ == "__main__":
    parser()
