#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function, unicode_literals, division, absolute_import
import sys
from collections import namedtuple
import struct
import uuid
from fcntl import ioctl

__copyright__ = "Copyright 2013-2014, Salix OS"
__author__ = "Cyrille Pontvieux <jrd@salixos.org>"
__credits__ = ["Cyrille Pontvieux", "Alex Zakharov"]
__email__ = "jrd@salixos.org"
__license__ = "MIT"
__version__ = "1.0.1"

if sys.version_info >= (3, 0):
    _unicode = lambda x: str(x)
    split_literal = "0"
    _range = range

    def hex(bytestring):
        return bytestring.hex()

elif sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding("utf8")
    _unicode = unicode
    _range = xrange
    split_literal = b"\0"
    import binascii

    def hex(bytestring):
        return binascii.hexlify(bytestring)


# http://en.wikipedia.org/wiki/Master_boot_record#Sector_layout
MBR_FORMAT = [
    # (b'446x', '_'),  # boot code
    (b"440x", "_"),  # boot code
    (b"4s", "drive_signature"),
    (b"2x", "_"),  # reserved
    (b"16s", "partition1"),
    (b"16s", "partition2"),
    (b"16s", "partition3"),
    (b"16s", "partition4"),
    (b"2s", "signature"),
]

# http://en.wikipedia.org/wiki/Master_boot_record#Partition_table_entries
MBR_PARTITION_FORMAT = [
    (b"B", "status"),  # > 0x80 => active
    (b"3p", "chs_first"),  # 8*h + 2*c + 6*s + 8*c
    (b"B", "type"),
    (b"3p", "chs_last"),  # 8*h + 2*c + 6*s + 8*c
    (b"L", "lba"),
    (b"L", "sectors"),
]

# http://en.wikipedia.org/wiki/Partition_type#List_of_partition_IDs
MBR_EXTENDED_TYPE = [0x05, 0x0F, 0x15, 0x1F, 0x85]

# http://en.wikipedia.org/wiki/Extended_boot_record#Structures
EBR_FORMAT = [
    (b"446x", "_"),
    (b"16s", "partition"),  # lba = offset from ebr, sectors = size of partition
    (b"16s", "next_ebr"),  # lba = offset from extended partition, sectors = next EBR + next Partition size
    (b"16x", "_"),
    (b"16x", "_"),
    (b"2s", "signature"),
]

MBR_PARTITION_TYPE = {
    0x00: "Empty",
    0x01: "FAT12",
    0x04: "FAT16 16-32MB",
    0x05: "Extended, CHS",
    0x06: "FAT16 32MB-2GB",
    0x07: "NTFS",
    0x0B: "FAT32",
    0x0C: "FAT32X",
    0x0E: "FAT16X",
    0x0F: "Extended, LBA",
    0x11: "Hidden FAT12",
    0x14: "Hidden FAT16,16-32MB",
    0x15: "Hidden Extended, CHS",
    0x16: "Hidden FAT16,32MB-2GB",
    0x17: "Hidden NTFS",
    0x1B: "Hidden FAT32",
    0x1C: "Hidden FAT32X",
    0x1E: "Hidden FAT16X",
    0x1F: "Hidden Extended, LBA",
    0x27: "Windows recovery environment",
    0x39: "Plan 9",
    0x3C: "PartitionMagic recovery partition",
    0x42: "Windows dynamic extended partition marker",
    0x44: "GoBack partition",
    0x63: "Unix System V",
    0x64: "PC-ARMOUR protected partition",
    0x81: "Minix",
    0x82: "Linux Swap",
    0x83: "Linux",
    0x84: "Hibernation",
    0x85: "Linux Extended",
    0x86: "Fault-tolerant FAT16B volume set",
    0x87: "Fault-tolerant NTFS volume set",
    0x88: "Linux plaintext",
    0x8E: "Linux LVM",
    0x93: "Hidden Linux",
    0x9F: "BSD/OS",
    0xA0: "Hibernation",
    0xA1: "Hibernation",
    0xA5: "FreeBSD",
    0xA6: "OpenBSD",
    0xA8: "Mac OS X",
    0xA9: "NetBSD",
    0xAB: "Mac OS X Boot",
    0xAF: "Mac OS X HFS",
    0xBE: "Solaris 8 boot",
    0xBF: "Solaris x86",
    0xE8: "Linux Unified Key Setup",
    0xEB: "BFS",
    0xEE: "EFI GPT protec MBR",
    0xEF: "EFI system",
    0xFA: "Bochs x86 emulator",
    0xFB: "VMware File System",
    0xFC: "VMware Swap",
    0xFD: "Linux RAID",
}


# http://en.wikipedia.org/wiki/GUID_Partition_Table#Partition_table_header_.28LBA_1.29
GPT_HEADER_FORMAT = [
    (b"8s", "signature"),
    (b"H", "revision_minor"),
    (b"H", "revision_major"),
    (b"L", "header_size"),
    (b"L", "crc32"),
    (b"4x", "_"),
    (b"Q", "current_lba"),
    (b"Q", "backup_lba"),
    (b"Q", "first_usable_lba"),
    (b"Q", "last_usable_lba"),
    (b"16s", "disk_guid"),
    (b"Q", "part_entry_start_lba"),
    (b"L", "num_part_entries"),
    (b"L", "part_entry_size"),
    (b"L", "crc32_part_array"),
]

# http://en.wikipedia.org/wiki/GUID_Partition_Table#Partition_entries_.28LBA_2.E2.80.9333.29
GPT_PARTITION_FORMAT = [
    (b"16s", "guid"),
    (b"16s", "uid"),
    (b"Q", "first_lba"),
    (b"Q", "last_lba"),
    (b"Q", "flags"),
    (b"72s", "name"),
]

# http://en.wikipedia.org/wiki/GUID_Partition_Table#Partition_type_GUIDs
GPT_GUID = {
    "024DEE41-33E7-11D3-9D69-0008C781F39F": "MBR partition scheme",
    "C12A7328-F81F-11D2-BA4B-00A0C93EC93B": "EFI System partition",
    "21686148-6449-6E6F-744E-656564454649": "BIOS Boot partition",
    "D3BFE2DE-3DAF-11DF-BA40-E3A556D89593": "Intel Fast Flash (iFFS) partition (for Intel Rapid Start technology)",
    "F4019732-066E-4E12-8273-346C5641494F": "Sony boot partition",
    "BFBFAFE7-A34F-448A-9A5B-6213EB736C22": "Lenovo boot partition / Ceph Journal",
    "E3C9E316-0B5C-4DB8-817D-F92DF00215AE": "Microsoft Reserved Partition (MSR)",
    "EBD0A0A2-B9E5-4433-87C0-68B6B72699C7": "Basic data partition",
    "5808C8AA-7E8F-42E0-85D2-E1E90434CFB3": "Logical Disk Manager (LDM) metadata partition",
    "AF9B60A0-1431-4F62-BC68-3311714A69AD": "Logical Disk Manager data partition",
    "DE94BBA4-06D1-4D40-A16A-BFD50179D6AC": "Windows Recovery Environment",
    "37AFFC90-EF7D-4E96-91C3-2D7AE055B174": "IBM General Parallel File System (GPFS) partition",
    "75894C1E-3AEB-11D3-B7C1-7B03A0000000": "Data partition",
    "E2A1E728-32E3-11D6-A682-7B03A0000000": "Service Partition",
    "0FC63DAF-8483-4772-8E79-3D69D8477DE4": "Linux filesystem data",
    "A19D880F-05FC-4D3B-A006-743F0F84911E": "RAID partition",
    "0657FD6D-A4AB-43C4-84E5-0933C84B4F4F": "Swap partition",
    "E6D6D379-F507-44C2-A23C-238F2A3DF928": "Logical Volume Manager (LVM) partition",
    "933AC7E1-2EB4-4F13-B844-0E14E2AEF915": "/home partition",
    "3B8F8425-20E0-4F3B-907F-1A25A76F98E8": "/srv partition",
    "7FFEC5C9-2D00-49B7-8941-3EA10A5586B7": "Plain dm-crypt partition",
    "CA7D7CCB-63ED-4C53-861C-1742536059CC": "LUKS partition",
    "8DA63339-0007-60C0-C436-083AC8230908": "Reserved",
    "83BD6B9D-7F41-11DC-BE0B-001560B84F0F": "Boot partition",
    "516E7CB4-6ECF-11D6-8FF8-00022D09712B": "Data partition",
    "516E7CB5-6ECF-11D6-8FF8-00022D09712B": "Swap partition",
    "516E7CB6-6ECF-11D6-8FF8-00022D09712B": "Unix File System (UFS) partition",
    "516E7CB8-6ECF-11D6-8FF8-00022D09712B": "Vinum volume manager partition",
    "516E7CBA-6ECF-11D6-8FF8-00022D09712B": "ZFS partition",
    "48465300-0000-11AA-AA11-00306543ECAC": "Hierarchical File System Plus (HFS+) partition",
    "55465300-0000-11AA-AA11-00306543ECAC": "Apple UFS",
    "6A898CC3-1DD2-11B2-99A6-080020736631": "ZFS / usr partition ",
    "52414944-0000-11AA-AA11-00306543ECAC": "Apple RAID partition",
    "52414944-5F4F-11AA-AA11-00306543ECAC": "Apple RAID partition, offline",
    "426F6F74-0000-11AA-AA11-00306543ECAC": "Apple Boot partition",
    "4C616265-6C00-11AA-AA11-00306543ECAC": "Apple Label",
    "5265636F-7665-11AA-AA11-00306543ECAC": "Apple TV Recovery partition",
    "53746F72-6167-11AA-AA11-00306543ECAC": "Apple Core Storage (i.e. Lion FileVault) partition",
    "6A82CB45-1DD2-11B2-99A6-080020736631": "Boot partition",
    "6A85CF4D-1DD2-11B2-99A6-080020736631": "Root partition",
    "6A87C46F-1DD2-11B2-99A6-080020736631": "Swap partition",
    "6A8B642B-1DD2-11B2-99A6-080020736631": "Backup partition",
    # '6A898CC3-1DD2-11B2-99A6-080020736631': '/usr partition',
    "6A8EF2E9-1DD2-11B2-99A6-080020736631": "/var partition",
    "6A90BA39-1DD2-11B2-99A6-080020736631": "/home partition",
    "6A9283A5-1DD2-11B2-99A6-080020736631": "Alternate sector",
    "6A945A3B-1DD2-11B2-99A6-080020736631": "Reserved partition",
    "6A9630D1-1DD2-11B2-99A6-080020736631": "Reserved partition",
    "6A980767-1DD2-11B2-99A6-080020736631": "Reserved partition",
    "6A96237F-1DD2-11B2-99A6-080020736631": "Reserved partition",
    "6A8D2AC7-1DD2-11B2-99A6-080020736631": "Reserved partition",
    "49F48D32-B10E-11DC-B99B-0019D1879648": "Swap partition",
    "49F48D5A-B10E-11DC-B99B-0019D1879648": "FFS partition",
    "49F48D82-B10E-11DC-B99B-0019D1879648": "LFS partition",
    "49F48DAA-B10E-11DC-B99B-0019D1879648": "RAID partition",
    "2DB519C4-B10F-11DC-B99B-0019D1879648": "Concatenated partition",
    "2DB519EC-B10F-11DC-B99B-0019D1879648": "Encrypted partition",
    "FE3A2A5D-4F32-41A7-B725-ACCC3285A309": "ChromeOS kernel",
    "3CB8E202-3B7E-47DD-8A3C-7FF2A13CFCEC": "ChromeOS rootfs",
    "2E0A753D-9E48-43B0-8337-B15192CB1B5E": "ChromeOS future use",
    "42465331-3BA3-10F1-802A-4861696B7521": "Haiku BFS",
    "85D5E45E-237C-11E1-B4B3-E89A8F7FC3A7": "Boot partition",
    "85D5E45A-237C-11E1-B4B3-E89A8F7FC3A7": "Data partition",
    "85D5E45B-237C-11E1-B4B3-E89A8F7FC3A7": "Swap partition",
    "0394EF8B-237E-11E1-B4B3-E89A8F7FC3A7": "Unix File System (UFS) partition",
    "85D5E45C-237C-11E1-B4B3-E89A8F7FC3A7": "Vinum volume manager partition",
    "85D5E45D-237C-11E1-B4B3-E89A8F7FC3A7": "ZFS partition",
    # 'BFBFAFE7-A34F-448A-9A5B-6213EB736C22': 'Ceph Journal',
    "45B0969E-9B03-4F30-B4C6-5EC00CEFF106": "Ceph dm-crypt Encrypted Journal",
    "4FBD7E29-9D25-41B8-AFD0-062C0CEFF05D": "Ceph OSD",
    "4FBD7E29-9D25-41B8-AFD0-5EC00CEFF05D": "Ceph dm-crypt OSD",
    "89C57F98-2FE5-4DC0-89C1-F3AD0CEFF2BE": "Ceph disk in creation",
    "89C57F98-2FE5-4DC0-89C1-5EC00CEFF2BE": "Ceph dm-crypt disk in creation",
}


# http://trcdatarecovery.com/articles/bsd-disklabel-partitioning-scheme
DISKLABEL_HEADER_FORMAT = [
    (b"4s", "signature1"),
    (b"4s", "controller"),
    (b"16s", "disklabel"),
    (b"16s", "pack_id"),
    (b"L", "sector_byte"),
    (b"88s", "misc"),
    (b"4s", "signature2"),
    (b"2s", "checksum"),
    (b"H", "slices_total"),
    (b"L", "boot_size"),
    (b"L", "superblock_size"),
]

DISKLABEL_PARTITION_FORMAT = [
    (b"L", "sectors_total"),
    (b"L", "first_sector"),
    (b"L", "filesystem_size"),
    (b"B", "type"),
    (b"1s", "fragments"),
    (b"2s", "cylinders"),
]

DISKLABEL_PARTITION_TYPE = {
    0x00: "Unused",
    0x01: "Swap",
    0x02: "V6",
    0x03: "V7",
    0x04: "SystemV",
    0x05: "4.1BSD",
    0x06: "Eighth edition",
    0x07: "4.2BSD fast file system (FFS)",
    0x08: "MSDOS (FAT variants)",
    0x09: "4.4BSD (LFS)",
    0x0A: "Unknown",
    0x0B: "OS/2 (HPFS)",
    0x0C: "CD-ROM (ISO9660)",
    0x0D: "Bootstrap",
    0x20: "NTFS",
    0x1B: "ZFS",
}


class MBRError(Exception):
    pass


class MBRMissing(MBRError):
    pass


class GPTError(Exception):
    pass


class GPTMissing(GPTError):
    pass


class DisklabelError(Exception):
    pass


class DisklabelMissing(DisklabelError):
    pass


class DiskException(Exception):
    pass


def check_disk_file(disk):
    try:
        disk.tell()
    except:
        raise DiskException(
            "Please provide a file pointer (sys.stding or result of open function) as first argument, pointing to an existing disk such as /dev/sda."
        )


def make_fmt(name, fmt, extras=None):
    extras = extras or list()
    packfmt = b"<" + b"".join(t for t, n in fmt)
    tupletype = namedtuple(name, [n for t, n in fmt if n != "_"] + extras)
    return (packfmt, tupletype)


class MBRTable:
    def __init__(self, fp, name="None"):
        self.filename = name
        self.fp = fp
        self.info = None

        check_disk_file(self.fp)
        self.fp.seek(0)
        try:
            self.mbrheader = self.read_mbr_header()
            # drive_signature = self.read_mbr_signature()
            partitions = self.read_mbr_partitions()
            self.info = namedtuple("MBRInfo", "lba_size, header, partitions")(512, self.mbrheader, partitions)
        except MBRMissing:
            pass
            # print('MBR Missing!')
        except MBRError:
            print("Error reading MBR!")

    def read_mbr_signature(self):
        self.fp.seek(0x1B8, 0)
        data = self.fp.read(4)
        self.fp.seek(0)

    def read_mbr_header(self):
        fmt, MBRHeader = make_fmt("MBRHeader", MBR_FORMAT)
        data = self.fp.read(struct.calcsize(fmt))
        header = MBRHeader._make(struct.unpack(fmt, data))
        if header.signature != b"\x55\xaa":
            raise MBRMissing("Bad MBR signature")
        return header

    def read_mbr_partitions(self):
        parts = []
        for i in range(1, 4):
            part = self.read_mbr_partition(getattr(self.mbrheader, "partition{0}".format(i)), i)
            if part:
                parts.append(part)
        extendpart = None
        for part in parts:
            if part.type in MBR_EXTENDED_TYPE:
                extendpart = part
                break
        if extendpart:
            parts.extend(self.read_ebr_partition(extendpart.lba, 0, 5))
        return parts

    def read_mbr_partition(self, partstr, num):
        fmt, MBRPartition = make_fmt("MBRPartition", MBR_PARTITION_FORMAT, extras=["index", "active", "type_str"])
        part = MBRPartition._make(struct.unpack(fmt, partstr) + (num, False, ""))
        if part.type:
            ptype = "Unknown"
            if part.type in MBR_PARTITION_TYPE:
                ptype = MBR_PARTITION_TYPE[part.type]
            part = part._replace(active=part.status >= 0x80, type_str=ptype)
            return part

    def read_ebr_partition(self, extended_lba, lba, num):
        self.fp.seek((extended_lba + lba) * 512)  # lba size is fixed to 512 for MBR
        fmt, EBR = make_fmt("EBR", EBR_FORMAT)
        data = fp.read(struct.calcsize(fmt))
        ebr = EBR._make(struct.unpack(fmt, data))
        if ebr.signature != b"\x55\xaa":
            raise MBRError("Bad EBR signature")
        parts = [self.read_mbr_partition(ebr.partition, num)]
        if ebr.next_ebr != 16 * b"\x00":
            part_next_ebr = self.read_mbr_partition(ebr.next_ebr, 0)
            next_lba = part_next_ebr.lba
            parts.extend(self.read_ebr_partition(extended_lba, next_lba, num + 1))
        return parts

    def pprint(self):
        if self.info:
            print("MBR Header")
            print("-" * 88)
            print("File dump       | #Parts   | FS or potential FS   |  Start   |   Size     |   Note     |")
            print("                |          |                      |          |            | *-active   |")
            print("-" * 88)
            print("{0: <16}| Serial: 0x{1: <59}|".format(self.filename, hex(self.info.header.drive_signature)))
            for part in self.info.partitions:
                print("-" * 88)
                print(
                    "                |{n: ^9}|{type: ^23}|{from_s: ^10}|{size_s: ^12}| {boot: <2}ID=0x{code: <4X}|".format(
                        n=part.index,
                        boot="*" if part.active else "",
                        from_s=part.lba,
                        size_s=part.sectors,
                        code=part.type,
                        type=part.type_str,
                    )
                )
            print("-" * 88)
        else:
            print("No MBR")
        print("---")


class GPTTable:
    def __init__(self, fp, name="None"):
        self.fp = fp
        self.filename = name
        self.info = None

        check_disk_file(self.fp)
        self.fp.seek(0)
        info = {
            "lba_size": None,
            "header": None,
            "revision_minor": None,
            "revision_major": None,
            "crc32": None,
            "current_lba": None,
            "backup_lba": None,
            "first_usable_lba": None,
            "last_usable_lba": None,
            "disk_guid": None,
            "part_entry_start_lba": None,
            "num_part_entries": None,
            "part_entry_size": None,
            "crc32_part_array": None,
            "partitions": [],
        }
        try:
            blocksize = struct.unpack("i", ioctl(self.fp.fileno(), 4608 | 104, struct.pack("i", -1)))[0]
        except:
            blocksize = 512
        try:
            info["lba_size"] = blocksize
            self.gptheader = self.read_gpt_header(lba_size=blocksize)
            info["header"] = self.gptheader
            for key in [k for k in info.keys() if k not in ("lba_size", "partitions", "header")]:
                info[key] = getattr(self.gptheader, key)
            info["partitions"] = self.read_gpt_partitions(lba_size=blocksize)
            self.info = namedtuple("GPTInfo", info.keys())(**info)
        except GPTMissing:
            pass
            # print('GPT Missing!')
        except GPTError:
            print("Error reading GPT!")

    def read_gpt_header(self, lba_size=512):
        try:
            # skip MBR (if any)
            self.fp.seek(1 * lba_size)
        except IOError as e:
            raise GPTError(e)
        fmt, GPTHeader = make_fmt("GPTHeader", GPT_HEADER_FORMAT)
        data = self.fp.read(struct.calcsize(fmt))
        header = GPTHeader._make(struct.unpack(fmt, data))
        if header.signature != b"EFI PART":
            raise GPTMissing("Bad GPT signature")
        revision = header.revision_major + (header.revision_minor / 10)
        if revision < 1.0:
            raise GPTError("Bad GPT revision: {0}.{1}".format(header.revision_major, header.revision_minor))
        if header.header_size < 92:
            raise GPTError("Bad GPT header size: {0}".format(header.header_size))
        header = header._replace(
            disk_guid=_unicode(uuid.UUID(bytes_le=header.disk_guid)).upper(),
        )
        return header

    def read_gpt_partitions(self, lba_size=512):
        self.fp.seek(self.gptheader.part_entry_start_lba * lba_size)
        fmt, GPTPartition = make_fmt("GPTPartition", GPT_PARTITION_FORMAT, extras=["index", "type"])
        parts = []
        for i in _range(self.gptheader.num_part_entries):
            data = self.fp.read(self.gptheader.part_entry_size)
            if len(data) < struct.calcsize(fmt):
                raise GPTError("Short GPT partition entry #{0}".format(i + 1))
            part = GPTPartition._make(struct.unpack(fmt, data) + (i + 1, ""))
            if part.guid == 16 * b"\x00":
                continue
            guid = _unicode(uuid.UUID(bytes_le=part.guid)).upper()
            ptype = "Unknown"
            if guid in GPT_GUID:
                ptype = GPT_GUID[guid]

            part = part._replace(
                guid=guid,
                uid=_unicode(uuid.UUID(bytes_le=part.uid)).upper(),
                # cut on C-style string termination; otherwise you'll see a long row of NILs for most names
                name=part.name.decode("utf-16").split(split_literal, 1)[0],
                type=ptype,
            )
            parts.append(part)
        return parts

    def pprint(self):
        if self.info:
            print("GPT Header")
            print("-" * 137)
            print(
                "File dump       | #Parts   |           Partition GUID            |  Start   |    Size    |        FS or potential FS        |   Note    |"
            )
            print("-" * 137)
            print(" {0: <15}| GUID: 0x{1: <110}|".format(self.filename, self.info.disk_guid))
            for part in self.info.partitions:
                print("-" * 137)
                print(
                    "{empty: ^16}|{n: ^9}|{guid: ^38}|{from_s: ^10}|{size: ^12}| {type:31.31} |{flags: ^12}|".format(
                        empty="",
                        n=part.index,
                        guid=part.guid,
                        type=part.type,
                        size=part.last_lba - part.first_lba,
                        from_s=part.first_lba,
                        flags=part.flags,
                    )
                )
                print(
                    "{empty: ^16}|{empty: ^9}|{uid: ^38}|{empty: ^10}|{empty: ^12}| {empty:31.31} |{empty: ^12}|".format(
                        empty="", uid=part.uid
                    )
                )
            print("-" * 137)
        else:
            print("No GPT")
        print("---")


class DisklabelTable:
    def __init__(self, fp, name="None"):
        self.fp = fp
        self.filename = name
        self.info = None
        check_disk_file(self.fp)
        self.fp.seek(0)

        try:
            blocksize = struct.unpack("i", ioctl(self.fp.fileno(), 4608 | 104, struct.pack("i", -1)))[0]
        except:
            blocksize = 512
        try:
            self.header = self.read_disklabel_header(blocksize)
            self.partitions = self.read_disklabel_partitions(blocksize)
            self.info = namedtuple("DisklabelInfo", "lba_size, header, partitions")(512, self.header, self.partitions)
        except DisklabelMissing:
            pass
            # print('Disklabel Missing!')
        except DisklabelError:
            pass
            # print('Error reading Disklabel!')

    def read_disklabel_header(self, lba_size=512):
        try:
            # skip MBR (if any)

            self.fp.seek(1 * lba_size)
        except IOError as e:
            raise DisklabelError(e)
        fmt, DisklabelHeader = make_fmt("DisklabelHeader", DISKLABEL_HEADER_FORMAT, extras=["size"])
        data = self.fp.read(struct.calcsize(fmt))
        header = DisklabelHeader._make(struct.unpack(fmt, data) + (0x94,))

        if header.signature1 != b"WEV\x82" or header.signature2 != b"WEV\x82":
            raise DisklabelMissing("Bad Disklabel signature")
        return header

    def read_disklabel_partitions(self, lba_size=512):
        parts = []
        fmt, DisklabelPartition = make_fmt(
            "DisklabelPartition", DISKLABEL_PARTITION_FORMAT, extras=["index", "type_str"]
        )
        for num in _range(self.header.slices_total):
            self.fp.seek(lba_size + self.header.size + num * 0x10)
            partstr = self.fp.read(0x10)
            part = DisklabelPartition._make(struct.unpack(fmt, partstr) + (num, "Unknown"))
            if part.type:
                if part.type in DISKLABEL_PARTITION_TYPE:
                    ptype = DISKLABEL_PARTITION_TYPE[part.type]
                    part = part._replace(type_str=ptype)
                parts.append(part)
        return parts

    def pprint(self):
        if self.info:
            indexer = [i + ":" for i in "abcdefghijklmnopqrstuvwxyz"]
            print("Disklabel Header")
            print("-" * 88)
            print("File dump      | #Parts   | FS or potential FS   |  Start   |   Size   |   Note     |")
            print("-" * 88)
            print(" {0: <86}|".format(self.filename))
            for part in self.info.partitions:
                print("-" * 88)
                print(
                    "              |{n: ^9}|{type: ^23}|{from_s: ^10}|{size_s: ^12}| ID=0x{code: <4X}  |".format(
                        n=indexer[part.index],
                        from_s=part.first_sector,
                        size_s=part.sectors_total,
                        code=part.type,
                        type=part.type_str,
                    )
                )
            print("-" * 88)
        else:
            print("No Disklabel")
        print("---")


def get_info(fp, name):
    m = MBRTable(fp, name)
    m.pprint()

    g = GPTTable(fp, name)
    g.pprint()

    d = DisklabelTable(fp, name)
    d.pprint()

    print()


if __name__ == "__main__":
    import os
    import argparse

    parser = argparse.ArgumentParser(description="Util to read MBR, GPT or BSD DiskTable tables")
    parser.add_argument("drives", metavar="drives", type=str, nargs="+", help="Drives (or images) to read partitions")
    args = parser.parse_args()
    for drive_path in args.drives:
        if not os.path.exists(drive_path) or os.path.isdir(drive_path):
            print("Error, can't find image file", drive_path)
            exit(-1)
        try:
            fp = open(os.path.abspath(drive_path), "rb")
        except IOError:
            print("Error, can't open image", drive_path)
        else:
            print("##### IMAGE {0} #####".format(os.path.basename(drive_path)))
            get_info(fp, os.path.basename(drive_path))
    exit(0)
