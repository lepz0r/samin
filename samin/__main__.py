#!/usr/bin/python3

import argparse
import logging
import subprocess
import os
import psutil


def get_fs_type(device):
    get_fs_command = ["blkid", "-o", "value", "-s", "TYPE", device]
    filesystem = subprocess.check_output(get_fs_command)
    return filesystem


def get_block(path):
    path = os.path.abspath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    p = [p for p in psutil.disk_partitions(all=True) if p.mountpoint == path.__str__()]
    return p[0].device


# Parser
def parser():
    parser = argparse.ArgumentParser(description="btrfs snapshot manager")
    subparser = parser.add_subparsers(dest="action")

    parser.add_argument("-s", "--subvolume", help="Specify subvolume")
    parser.add_argument("-b", "--device", help="Specify subvolume")
    parser.add_argument("-d", "--debug", help="Enable debugging", action="store_true")
    parser.add_argument(
        "-u",
        "--utc",
        action="store_true",
        help="Show time in UTC instead of local time",
    )

    c_config_parser = subparser.add_parser("create-config", help="Create a config")
    d_config_parser = subparser.add_parser("delete-config", help="Delete a config")

    t_snap_parser = subparser.add_parser("take-snapshot", help="Take a snapshot")
    t_snap_parser.add_argument(
        "--description",
        help="Specify description",
        default="No description given",
    )

    d_snap_parser = subparser.add_parser("delete-snapshot", help="Delete a snapshot")
    d_snap_num = d_snap_parser.add_argument("snapshot_number")

    rollback_parser = subparser.add_parser("rollback", help="Rollback to snapshot")
    rollback_num = rollback_parser.add_argument("snapshot_number")

    l_snap_parser = subparser.add_parser("list-snapshots", help="List snapshots")

    args = parser.parse_args()

    return args


def main_func():
    args = parser()

    if args.device is not None:
        device = args.device
    else:
        device = get_block("/")

    filesystem = get_fs_type(device)

    subvolume = args.subvolume

    if filesystem == b"btrfs\n":
        import samin.btrfs as fs

        if args.subvolume is not None:
            subvolume = args.subvolume
        else:
            subvolume = fs.get_subvolume("/")
    else:
        raise Exception("Filesystem is not supported")

    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG)

    if args.action == "create-config":
        fs.create_config(subvolume, device)
    elif args.action == "take-snapshot":
        fs.take_snapshot(subvolume, device, args.description)
    elif args.action == "delete-snapshot":
        confirmation = input(
            "Are you sure you want to delete snapshot "
            + args.snapshot_number
            + " from "
            + device
            + " subvolume "
            + subvolume
            + "? "
        )
        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
            fs.delete_snapshot(subvolume, device, args.snapshot_number)
    elif args.action == "rollback":
        confirmation = input(
            "Are you sure you want to rollback subvolume "
            + subvolume
            + " on "
            + device
            + " to snapshot #"
            + args.snapshot_number
            + "? "
        )
        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
            fs.rollback(subvolume, device, args.snapshot_number)
            print("Remount the subvolume or reboot to finish")
    elif args.action == "list-snapshots":
        fs.list_snapshots(subvolume, device, args.utc)
    elif args.action == "delete-config":
        fs.delete_config(subvolume, device)


if __name__ == "__main__":
    main_func()
