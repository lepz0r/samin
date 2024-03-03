#!/usr/bin/python3

import argparse
import logging
import subprocess


def get_fs_type(device):
    get_fs_command = ["blkid", "-o", "value", "-s", "TYPE", device]
    filesystem = subprocess.check_output(get_fs_command)
    return filesystem


# Parser
def parser():
    parser = argparse.ArgumentParser(description="btrfs snapshot manager")
    subparser = parser.add_subparsers(dest="action")

    parser.add_argument("-s", "--subvolume", help="Specify subvolume", required=True)
    parser.add_argument("-b", "--device", help="Specify subvolume", required=True)
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

    filesystem = get_fs_type(args.device)

    if filesystem == b"btrfs\n":
        import btrfs as fs
    else:
        raise Exception("Filesystem is not supported")

    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG)

    if args.action == "create-config":
        fs.create_config(args.subvolume, args.device)
    elif args.action == "take-snapshot":
        fs.take_snapshot(args.subvolume, args.device, args.description)
    elif args.action == "delete-snapshot":
        confirmation = input(
            "Are you sure you want to delete snapshot "
            + args.snapshot_number
            + " from "
            + args.device
            + " subvolume "
            + args.subvolume
            + "? "
        )
        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
            fs.delete_snapshot(args.subvolume, args.device, args.snapshot_number)
    elif args.action == "rollback":
        confirmation = input(
            "Are you sure you want to rollback subvolume "
            + args.subvolume
            + " on "
            + args.device
            + " to snapshot #"
            + args.snapshot_number
            + "? "
        )
        if confirmation.lower() in ["y", "yes", "yup", "yep", "roger"]:
            fs.rollback(args.subvolume, args.device, args.snapshot_number)
            print("Remount the subvolume or reboot to finish")
    elif args.action == "list-snapshots":
        fs.list_snapshots(args.subvolume, args.device, args.utc)
    elif args.action == "delete-config":
        fs.delete_config(args.subvolume, args.device)


if __name__ == "__main__":
    parser()
