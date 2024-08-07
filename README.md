# CSB Util

Utility to encode and decode .csb files.

CSB is basically a binary version of a CSV file optimized for quick parsing (it's definitely not optimized for file size as csb files are much larger than their csv counterparts)

These files are found in _The Battle Cats Unite!_. Although the CSB format is very similar to BNTX, which is used for images, which either means that PONOS took heavy inspiration from that format, or the CSB format is another Nintendo file format that alrady existed but isn't documented online. To get the csb files from the game you have to extract the .arc files which I won't be getting into here, I might make a tool in the future that extracts them though.

I've released this tool separately as other games might use the format too if it is a Nintendo format. 

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/fieryhenry)

## Installation

```bash
pip install csb_util
```

## Usage

Most of what you need to know is detailed in the --help option

```bash
python3 -m csb_util --help
```

### Decode

```bash
python3 -m csb_util decode --help
```

To decode csb files you can either pass in individual files with the --files option, e.g

```bash
python3 -m csb_util decode --files file1.csb file2.csb --outdir output
```

To decode a folder of csb files you can use the --dirs option, e.g

```bash
python3 -m csb_util decode --dirs folder1 folder2 --outdir output
```

If you have non-csb files in that folder that you want to ignore use the --ignore flag, e.g

```bash
python3 -m csb_util decode --dirs mixed_use_folder --outdir output --ignore
```

### Encode

```bash
python3 -m csb_util encode --help
```

Encode csv files back to csb files.

Options are basically the same as [decode](#decode), so just read that


## Install From Source

```bash
git clone https://github.com/fieryhenry/csb_util.git
cd csb_util
pip install -e .
```

