# Partition Reader

[![Python Versions](https://img.shields.io/badge/Python-2.7%20%7C%203.x-blue.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)

This script can read and parse common partition table formats (MBR, GPT, BSD DiskLabel).  
It was developed using references from [this project](https://github.com/jrd/pyreadpartitions).

---

## Installation

### Clone the repository

```bash
$ git clone https://github.com/dokzlo13/partition_reader.git
$ cd partition_reader
```

### Or download the single file

If you only need the main script, you can download it directly with `wget`:

```bash
$ wget https://raw.githubusercontent.com/dokzlo13/partition_reader/master/partition.py
```

---

## Usage

```bash
$ python partition.py image1 image2 ...
```

Or, for Python 2.7:

```bash
$ python2.7 partition.py image1 image2 ...
```

Use `-l` or `--log` to save the output to `partition.log` in the working directory.

<details>
  <summary>Example usage</summary>

```bash
$ python partition.py --help
usage: partition.py [-h] [-l] drives [drives ...]

Util to read MBR, GPT or BSD DiskTable tables

positional arguments:
  drives      Drives (or images) to read partitions

options:
  -h, --help  show this help message and exit
  -l, --log   Save output in to partition.log of working directory

----------------------------------------------------------------------------

$ python partition.py ./examples/disk.img

##### IMAGE disk.img #####
MBR Header
----------------------------------------------------------------------------------------
File dump        | #Parts | FS or potential FS     |  Start   |   Size     |  Note      |
                 |        |                        |          |           | *-active   |
----------------------------------------------------------------------------------------
 disk.img        | Serial: 0x00000000
----------------------------------------------------------------------------------------
                 |    1   | EFI GPT protec MBR     |    1     |   20479    | ID=0xEE    |
----------------------------------------------------------------------------------------
---
GPT Header
-----------------------------------------------------------------------------------------------------------------------------------------
File dump        | #Parts |         Partition GUID             |  Start   |   Size     |   FS or potential FS        |   Note   |
-----------------------------------------------------------------------------------------------------------------------------------------
 disk.img        | GUID: 0xA924656E-9A06-4F9E-82E2-CFEC246890F6
-----------------------------------------------------------------------------------------------------------------------------------------
                 |    1   | 0FC63DAF-8483-4772-8E79-3D69D8477DE4 |   2048   |   18398    | Linux filesystem data       |   0      |
                 |        | 943FC24C-950E-4E13-8D60-503407C8159E |          |           |                             |          |
-----------------------------------------------------------------------------------------------------------------------------------------
---
No Disklabel
---
```
</details>
