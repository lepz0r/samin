#!/usr/bin/python3

import btrfsutil
import json
import os
import argparse
import shutil
import subprocess
import pytz
import psutil
import logging
from pathlib import Path
from datetime import datetime
from tzlocal import get_localzone


def get_root_mountpoint():
    root_mountpoint = "/run/samin/"
    logging.debug("Mountpoint: " + root_mountpoint)
    return root_mountpoint


def get_confdir():
    confdir = get_root_mountpoint() + ".samin"
    logging.debug("Config directory: " + confdir)
    return confdir


def get_subvol_conf(subvol):
    subvol_conf = get_confdir() + "/" + subvol + "/"
    logging.debug("Subvolume config: " + subvol_conf)
    return subvol_conf


def generate_snapshot_metadata(desc):
    date = datetime.utcnow()
    metadata = {"date": date.strftime("%Y-%m-%dT%H:%M:%S"), "description": desc}
    return metadata


def mnt(device, mountpoint):
    get_fs_command = ["blkid", "-o", "value", "-s", "TYPE", device]
    filesystem = subprocess.check_output(get_fs_command)
    logging.debug("Filesystem of " + device + " is " + filesystem.decode("utf-8"))

    if filesystem != b"btrfs\n":
        raise Exception("Filesystem is not btrfs")
    try:
        if os.path.ismount(mountpoint) is False:
            mnt_command = ["mount", "-o", "subvolid=0", device, mountpoint]
            logging.debug("Mounting filesystem")
            subprocess.check_call(mnt_command)
            return True
    except subprocess.CalledProcessError as e:
        print(e.output)
        return False


def check_if_subvol_mounted(subvol):
    partitions = psutil.disk_partitions()
    subvolid = btrfsutil.subvolume_info(subvol).id

    for i in partitions:
        if str(subvolid) in i.opts:
            logging.debug("Subvolume " + subvol + " is mounted")
            return True


def mount_root_mountpoint(root_mountpoint, device):
    logging.debug("Creating mountpoint directory ")
    os.makedirs(root_mountpoint, exist_ok=True)
    mnt(device, root_mountpoint)


def umnt(mountpoint):
    logging.debug("Unmouting " + mountpoint)
    subprocess.check_call(["umount", mountpoint])


def get_snapshot_metadatas(subvol, device, utc=False):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)
    snapshot_location = subvol_confdir + "/snapshots/"
    metadatas = []

    if len(os.listdir(snapshot_location)) == 0:
        print("No snapshots found")
    else:
        for snapshot in os.listdir(snapshot_location):
            with open(
                subvol_confdir + "/snapshots/" + snapshot + "/metadata.json"
            ) as metadata:
                current_metadata = json.loads(metadata.read())
                logging.debug("Found snapshot metadata: " + str(current_metadata))
                date_obj = datetime.strptime(
                    current_metadata["date"], "%Y-%m-%dT%H:%M:%S"
                )
                if utc is False:
                    local_tz = get_localzone()
                    current_metadata["date"] = date_obj.replace(
                        tzinfo=pytz.utc
                    ).astimezone(local_tz)
                else:
                    current_metadata["date"] = date_obj
                current_metadata["number"] = snapshot
                metadatas.append(current_metadata)

    umnt(root_mountpoint)

    return metadatas


def list_snapshots(subvol, device, utc=False):
    metadatas: list
    metadatas = get_snapshot_metadatas(subvol, device, utc)
    if len(metadatas) > 0:
        print("| No.\t| Date\t\t\t\t| Description")
        for metadata in range(len(metadatas)):
            snp_date = datetime.strftime(
                metadatas[metadata]["date"], "%a %b %d %Y %H:%M:%S %p"
            )
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
        number = "1"
    else:
        number = str(int(snapshot_dir[-1]) + 1)

    logging.debug("Next snapshot number: " + number)
    return number


def create_config(subvol, device):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()
    confdir = get_confdir()

    mount_root_mountpoint(root_mountpoint, device)

    if Path(confdir).exists() is False:
        logging.debug("Creating samin config subvolume")
        btrfsutil.create_subvolume(confdir)

    logging.debug("Creating subvolume config")
    os.makedirs(subvol_confdir + "/snapshots", exist_ok=True)

    umnt(root_mountpoint)


def delete_config(subvol, device):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)

    subvol_snapshots = os.listdir(subvol_confdir + "snapshots/")

    if len(subvol_confdir) != 0:
        for snapshot_number in subvol_snapshots:
            delete_snapshot(subvol, device, snapshot_number, False)

    logging.debug("Deleting config")
    shutil.rmtree(subvol_confdir)

    umnt(root_mountpoint)


def create_snapshot_dir(subvol, desc):
    subvol_conf = get_subvol_conf(subvol)
    # root_mountpoint = get_root_mountpoint()
    metadata = generate_snapshot_metadata(desc)
    next_snapshot_number = get_next_snapshot_number(subvol_conf + "/snapshots")
    snapshot_dir = subvol_conf + "snapshots/" + next_snapshot_number
    logging.debug("Creating snapshot dir at " + snapshot_dir)
    os.makedirs(snapshot_dir, exist_ok=True)

    with open(snapshot_dir + "/metadata.json", "w") as output:
        logging.debug("Saving metadata: " + str(metadata))
        json.dump(metadata, output, indent=2)

    return snapshot_dir


def take_snapshot(subvol, device, desc="No description given"):
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)

    snapshot_dir = create_snapshot_dir(subvol, desc)

    logging.debug("Taking snapshot at " + snapshot_dir + "/snapshot")

    btrfsutil.create_snapshot(
        root_mountpoint + subvol,
        snapshot_dir + "/snapshot",
        read_only=True,
    )

    umnt(root_mountpoint)


def rollback(subvol, device, snapshot_number):
    subvol_conf = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()

    mount_root_mountpoint(root_mountpoint, device)

    snapshot_dir = create_snapshot_dir(subvol, "rolled back to " + snapshot_number)

    logging.debug(
        "Moving old subvolume from "
        + root_mountpoint
        + subvol
        + " to "
        + snapshot_dir
        + "/snapshot"
    )
    os.rename(
        root_mountpoint + subvol,
        snapshot_dir + "/snapshot",
    )

    logging.debug(
        "Generating new snapshot from "
        + subvol_conf
        + "snapshots/"
        + snapshot_number
        + "/"
        + "snapshot"
        + " to "
        + root_mountpoint
        + subvol
    )

    btrfsutil.create_snapshot(
        subvol_conf + "snapshots/" + snapshot_number + "/" + "snapshot",
        root_mountpoint + subvol,
    )

    umnt(root_mountpoint)


def map_snapshot_list(input):
    inputs = map(str, input.split(","))
    outputs = []
    for i in inputs:
        if "-" in i:
            start, end = map(int, i.split("-"))
            my_range = range(start, end + 1, +1)
            for n in my_range:
                outputs.append(n)
        else:
            outputs.append(i)

    return outputs


def delete_snapshot(subvol, device, snapshot_numbers, no_mount_op=False):
    subvol_confdir = get_subvol_conf(subvol)
    root_mountpoint = get_root_mountpoint()
    snapshots = map_snapshot_list(snapshot_numbers)

    if no_mount_op is False:
        mount_root_mountpoint(root_mountpoint, device)

    for snapshot in snapshots:
        snapshot_number = str(snapshot)
        if (
            check_if_subvol_mounted(
                subvol_confdir + "snapshots/" + snapshot_number + "/" + "snapshot"
            )
            is True
        ):
            logging.error(
                "Not removing snapshot #"
                + snapshot_number
                + ": snapshot is still mounted"
            )

        else:
            logging.debug(
                "Deleting snapshot: " + subvol_confdir + "snapshots/" + snapshot_number
            )
            btrfsutil.delete_subvolume(
                subvol_confdir + "snapshots/" + snapshot_number + "/" + "snapshot"
            )
            shutil.rmtree(subvol_confdir + "snapshots/" + snapshot_number)

    if no_mount_op is True:
        umnt(root_mountpoint)


# Parser
# def fs_parser():
#    parser = argparse.ArgumentParser(description="btrfs snapshot manager")
#    #
#    parser.add_argument("-s", "--subvolume", help="Specify subvolume", required=True)
#
#    return parser
#
#
#    parser.add_argument("-b", "--device", help="Specify subvolume", required=True)
#    parser.add_argument("-d", "--debug", help="Enable debugging", action="store_true")
#    parser.add_argument(
#        "-u",
#        "--utc",
#        action="store_true",
#        help="Show time in UTC instead of local time",
#    )
#
#    c_config_parser = subparser.add_parser("create-config", help="Create a config")
#    d_config_parser = subparser.add_parser("delete-config", help="Delete a config")
#
#    t_snap_parser = subparser.add_parser("take-snapshot", help="Take a snapshot")
#    t_snap_parser.add_argument(
#        "--description",
#        help="Specify description",
#        default="No description given",
#    )
#
#    d_snap_parser = subparser.add_parser("delete-snapshot", help="Delete a snapshot")
#    d_snap_num = d_snap_parser.add_argument("snapshot_number")
#
#    rollback_parser = subparser.add_parser("rollback", help="Rollback to snapshot")
#    rollback_num = rollback_parser.add_argument("snapshot_number")
#
#    l_snap_parser = subparser.add_parser("list-snapshots", help="List snapshots")
#
#    args = parser.parse_args()
#
#    if args.debug is True:
#        logging.basicConfig(level=logging.DEBUG)
#
#    if args.action == "create-config":
#        create_config(args.subvolume, args.device)
#    elif args.action == "take-snapshot":
#        take_snapshot(args.subvolume, args.device, args.description)
#    elif args.action == "delete-snapshot":
#        confirmation = input(
#            "Are you sure you want to delete snapshot "
#            + args.snapshot_number
#            + " from "
#            + args.device
#            + " subvolume "
#            + args.subvolume
#            + "? "
#        )
#        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
#            delete_snapshot(args.subvolume, args.device, args.snapshot_number)
#    elif args.action == "rollback":
#        confirmation = input(
#            "Are you sure you want to rollback subvolume "
#            + args.subvolume
#            + " on "
#            + args.device
#            + " to snapshot #"
#            + args.snapshot_number
#            + "? "
#        )
#        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
#            rollback(args.subvolume, args.device, args.snapshot_number)
#            print("Remount the subvolume or reboot to finish")
#    elif args.action == "list-snapshots":
#        list_snapshots(args.subvolume, args.device, args.utc)
#    elif args.action == "delete-config":
#        delete_config(args.subvolume, args.device)
#
#
if __name__ == "__main__":
    parser()
