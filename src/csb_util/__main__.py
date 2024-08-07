from __future__ import annotations
import os
from typing import Literal
from csb_util import csb

import argparse
import sys

import csb_util


def get_error_text(error: csb.ReadError):
    if error == csb.ReadError.SUCCESS:
        return None
    if error == csb.ReadError.INVALID_CSB_MAGIC:
        return "Invalid CSB file magic, are you sure this a csb file?"
    if error == csb.ReadError.INVALID_BYTE_ORDER:
        return "Invalid CSB byte order"
    if error == csb.ReadError.INVALID_STRP_MAGIC:
        return "Invalid STRP block magic"
    if error == csb.ReadError.INVALID_LNP_MAGIC:
        return "Invalid LNP block magic"
    if error == csb.ReadError.INVALID_LNT_MAGIC:
        return "Invalid LNT block magic"
    if error == csb.ReadError.INCONSISTENT_TOTAL_LINES:
        return "Inconsistent total csv lines"
    if error == csb.ReadError.INCONSISTENT_MAX_COLUMNS:
        return "Inconsistent max csv columns"
    if error == csb.ReadError.INCONSISTENT_TOTAL_FIELDS:
        return "Inconsistent total csv fields"


def get_csv_name(filename: str):
    if filename.endswith(".csv"):
        return filename
    if filename.endswith(".csv.csb"):
        return filename[:-4]
    if filename.endswith(".csb"):
        return filename[:-1] + "v"
    return filename + ".csv"


def get_csb_name(filename: str):
    if filename.endswith(".csb"):
        return filename
    return filename + ".csb"


def decode(
    files: list[str], outdir: str, skip_validation: bool = False, silent: bool = False
):
    for file in files:
        with open(file, "rb") as f:
            lines, err = csb.read_csb(f, not skip_validation)

        if lines is None:
            if not silent:
                error_text = get_error_text(err)
                print(error_text)
            exit(err.value)

        filename = os.path.basename(file)
        filename = get_csv_name(filename)

        outpath = os.path.join(outdir, filename)

        with open(
            outpath,
            "w",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            csb.write_csv(f, lines)

        if not silent:
            print(f"Decoded {os.path.abspath(file)} to {os.path.abspath(outpath)}")


def encode(
    files: list[str],
    outdir: str,
    byteorder: Literal["<", ">"] = "<",
    silent: bool = False,
):
    for file in files:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            lines = csb.read_csv(f)

        filename = os.path.basename(file)
        filename = get_csb_name(filename)

        outpath = os.path.join(outdir, filename)

        with open(outpath, "wb") as f:
            csb.write_csb(f, lines, byteorder)

        if not silent:
            print(f"Encoded {os.path.abspath(file)} to {os.path.abspath(outpath)}")


def main():
    epilog = "Copyright (C) 2024 fieryhenry. Program licensed under the GNU General Public License v3"
    parser = argparse.ArgumentParser(
        "python -m csb_util",
        description="utility to encode and decode csb files",
        epilog=epilog,
    )
    parser.add_argument(
        "--version",
        "-v",
        help="print the version of the program and exit",
        action="store_true",
    )
    parser.add_argument(
        "--silent", "-s", action="store_true", help="don't output anything to stdout"
    )
    actions = parser.add_subparsers(
        title="actions",
        description="actions to decode or encode csb files",
        help="show action help with 'python -m csb_util {decode,encode} --help'",
    )
    decode_parser = actions.add_parser(
        "decode",
        description="decode csb files to csv files",
        help="decode csb files to csv files",
        epilog=epilog,
    )

    decode_parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        required=False,
        help="a list of individual csb files to decode (optional)",
        dest="dfiles",
    )
    decode_parser.add_argument(
        "--dirs",
        "-d",
        nargs="+",
        required=False,
        help="a list of directories containing csb files to decode (optional)",
        dest="ddirs",
    )
    decode_parser.add_argument(
        "--outdir",
        "-o",
        required=True,
        help="output directory to place the decoded csv files in",
        dest="doutdir",
    )
    decode_parser.add_argument(
        "--ignore", "-i", action="store_true", help="ignore any non-csb files given"
    )
    decode_parser.add_argument(
        "--skip-validate",
        "-s",
        required=False,
        action="store_true",
        help="skip the extra validation checks on the decoded csb files that make sure that the file decoded without errors",
        dest="dskip_validation",
    )

    encode_parser = actions.add_parser(
        "encode",
        description="encode csv files to csb files",
        help="encode csv files to csb files",
        epilog=epilog,
    )

    encode_parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        required=False,
        dest="efiles",
        help="a list of individual csv files to encode (optional)",
    )
    encode_parser.add_argument(
        "--dirs",
        "-d",
        nargs="+",
        required=False,
        dest="edirs",
        help="a list of directories containg csv files to encode (optional)",
    )
    encode_parser.add_argument(
        "--outdir",
        "-o",
        required=True,
        dest="eoutdir",
        help="output directory to place the encoded csb files in",
    )
    encode_parser.add_argument(
        "--byteorder",
        "-b",
        required=False,
        default="<",
        choices=["<", ">"],
        dest="ebyteorder",
        help="byte order, can be little endian ('<') or big endian ('>'). Defaults to little.",
    )
    encode_parser.add_argument(
        "--ignore", "-i", action="store_true", help="ignore any non-csv files given"
    )

    args = parser.parse_args(sys.argv[1:])

    if args.version:
        print(csb_util.__version__)
        exit(0)

    kwargs = args._get_kwargs()

    decode_action = True

    if not kwargs:
        parser.print_help()
        exit(0)

    for kwarg in kwargs:
        if kwarg[0].startswith("d"):
            decode_action = True
            break
        elif kwarg[0].startswith("e"):
            decode_action = False
            break

    files: list[str] | None = args.dfiles if decode_action else args.efiles
    dirs: list[str] | None = args.ddirs if decode_action else args.edirs
    outdir: str = args.doutdir if decode_action else args.eoutdir

    os.makedirs(outdir, exist_ok=True)

    all_files: list[str] = []

    if files is not None:
        for file in files:
            if not os.path.exists(file):
                if not args.silent:
                    print(f"Input file '{os.path.abspath(file)}' does not exist")
                exit(-1)
            if os.path.isdir(file):
                if not args.silent:
                    print(f"Input file '{os.path.abspath(file)}' is a directory")
                exit(-1)

            all_files.append(file)

    if dirs is not None:
        for dir in dirs:
            if not os.path.exists(dir):
                if not args.silent:
                    print(f"Input directory '{os.path.abspath(dir)}' does not exist")
                exit(-1)
            if not os.path.isdir(dir):
                if not args.silent:
                    print(
                        f"Input directory '{os.path.abspath(dir)}' is not a directory"
                    )
                exit(-1)

            for file in os.listdir(dir):
                path = os.path.join(dir, file)
                all_files.append(path)

    new_files: list[str] = all_files.copy()
    if args.ignore:
        for file in all_files:
            if decode_action:
                if not file.endswith(".csb"):
                    new_files.remove(file)
            else:
                if not file.endswith(".csv"):
                    new_files.remove(file)

    all_files = new_files
    if not all_files:
        print("Nothing to do. No files given")
        exit(0)

    if decode_action:
        decode(all_files, outdir, args.dskip_validation, args.silent)
    else:
        encode(all_files, outdir, args.ebyteorder, args.silent)


if __name__ == "__main__":
    main()
