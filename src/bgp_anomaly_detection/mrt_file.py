from collections import OrderedDict, Counter
from copy import copy
from csv import DictWriter, DictReader, field_size_limit
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from json import dump as json_dump, load as json_load, loads, dumps
from math import inf
from pathlib import Path
from pickle import dump as pickle_dump, load as pickle_load
from sys import maxsize
from typing import Self

from frozendict import frozendict
from mrtparse import Reader, MRT_T, TD_V2_ST, BGP_ATTR_T, AS_PATH_SEG_T

from .autonomous_system import AS
from .location import make_location_dictionary
from .logging import Logger
from .paths import Paths

MESSAGES_AVG = 1154829  # Average number of messages in a snapshot .bz2 file

maxInt = maxsize
while True:
    try:
        field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)
logger = Logger.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SnapShot:
    """
    Represents a snapshot of Border Gateway Protocol (BGP) data, facilitating import, processing, and export of
    Autonomous System (AS) routing information from various file formats. Supported formats include .bz2 for raw BGP
    data, .json or .csv for parsed AS data.

    The class parses BGP messages from the specified file, updating attributes such as snapshot time, AS paths,
    prefixes, and peer information. Parsed AS information can be exported to JSON, CSV, or pickled formats for
    further analysis or archival purposes.
    """

    file_path: str
    timestamp: datetime = field(init=False)
    as_map: frozendict[str, AS] = field(init=False)
    msg_limit: int = field(default=inf)

    def __post_init__(self):
        file_path = Path(self.file_path)
        file_extension = file_path.suffix.lower()
        base_name = file_path.stem.split(".")
        date_part, time_part = base_name[1], base_name[2]
        date_time_str = date_part + time_part
        timestamp = datetime.strptime(date_time_str, "%Y%m%d%H%M")

        object.__setattr__(self, "timestamp", timestamp)

        parser = MRTParser()
        if file_extension == ".bz2":
            as_map = parser.import_bz2(self.file_path, self.msg_limit)
        elif file_extension == ".csv":
            as_map = parser.import_csv(self.file_path)
        elif file_extension == ".json":
            as_map = parser.import_json(self.file_path)
        else:
            raise ValueError(f"Unsupported file format: '{file_extension}'")

        object.__setattr__(self, "as_map", as_map)

    def __str__(self) -> str:
        """Return the file name of the BGP data file."""

        return Path(self.file_path).name

    # def __hash__(self) -> int:
    #     """Return a hash value based on the snapshot time."""
    #
    #     return hash(self.timestamp)

    def __eq__(self, other: Self) -> bool:
        """Compare two SnapShot instances for equality based on their snapshot times."""

        if isinstance(other, SnapShot):
            return self.timestamp == other.timestamp
        else:
            return NotImplemented

    def export_csv(self, destination_dir: str = Paths.PARSED_DIR) -> None:
        """
        Export parsed AS data to a CSV file.

        :param destination_dir: Directory path where the CSV file will be saved.
        :return: None
        """

        destination_dir = Path(destination_dir)
        destination_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"Exporting data to CSV")

        csv_data = list()
        for as_id, as_instance in self.as_map.items():
            if as_instance.path_sizes:
                path_sizes = dumps({length: qnty for length, qnty in as_instance.path_sizes})
            else:
                path_sizes = None
            if as_instance.announced_prefixes:
                announced_prefixes = ";".join(as_instance.announced_prefixes)
            else:
                announced_prefixes = None
            if as_instance.neighbours:
                neighbours = ";".join(as_instance.neighbours)
            else:
                neighbours = None

            csv_data.append(
                {
                    "as_id": as_id,
                    "location": as_instance.location,
                    "mid_path_count": as_instance.mid_path_count,
                    "end_path_count": as_instance.end_path_count,
                    "path_sizes": path_sizes,
                    "announced_prefixes": announced_prefixes,
                    "neighbours": neighbours
                }
            )

        csv_file_path = destination_dir / (Path(self.file_path).stem + ".csv")
        with open(csv_file_path, mode="w", newline="") as csv_file:
            fieldnames = [
                "as_id",
                "location",
                "mid_path_count",
                "end_path_count",
                "path_sizes",
                "announced_prefixes",
                "neighbours"
            ]
            writer = DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        logger.info(f"Parsed data saved at: {csv_file_path}")

    def export_json(self, destination_dir: str = Paths.PARSED_DIR) -> None:
        """
        Export parsed AS data to a JSON file.

        :param destination_dir: Directory path where the JSON file will be saved.
        :return: None
        """

        destination_dir = Path(destination_dir)
        destination_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"Exporting data to JSON")

        formatted_date_time = self.timestamp.strftime('%d/%m/%Y %H:%M')

        as_info = dict()
        for as_id in self.as_map:
            as_info[as_id] = self.as_map[as_id].export_json()

        output_data = {
            "snapshot_time": formatted_date_time,
            "as": {
                "as_total": len(self.as_map),
                "as_info": as_info
            }
        }

        json_file_path = destination_dir / (Path(self.file_path).stem + ".json")
        with open(json_file_path, "w") as output:
            json_dump(output_data, output, indent=4)

        logger.info(f"Parsed data saved at: {json_file_path}")

    def export_pickle(self, destination_dir: str = Paths.PARSED_DIR):
        """
        Save the SnapShot instance to a pickle file.

        :param destination_dir: Directory path where the pickle file will be saved.
        :return: None
        """

        destination_dir = Path(destination_dir)
        destination_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"Exporting snapshot to pickle file")

        save_path = destination_dir / (Path(self.file_path).stem + ".pkl")
        with open(save_path, "wb") as file:
            pickle_dump(self, file)

        logger.info(f"SnapShot instance saved successfully at: {save_path}")


peer = None


class MRTParser:
    """Parser for processing MRT formatted BGP data and converting it into AS routing information."""

    def __init__(self):
        self._as_map: dict[str, dict[str, int | str | Counter | set]] = dict()
        self._type = str()
        self._flag = str()
        self._peer_ip = str()
        self._ts = int()
        self._peer_as = int()
        self._nlri = list()
        self._withdrawn = list()
        self._as_path = list()
        self._next_hop = list()
        self._as4_path = list()

        self.location_map: frozendict[str, str]
        if not (Paths.DELEG_DIR / "locale.pkl").exists():
            self.location_map = make_location_dictionary()
        else:
            with open(Paths.DELEG_DIR / "locale.pkl", "rb") as file:
                self.location_map = pickle_load(file)

    def import_bz2(self, file_path: str, msg_limit: int) -> frozendict:
        """
        Import AS data from a .bz2 compressed BGP data file.

        :param file_path: Path to the .bz2 file.
        :param msg_limit: Maximum number of messages to process.
        :return: Frozen dictionary containing AS data.
        """

        reader = Reader(str(file_path))
        start_time = datetime.now()

        logger.info(f"Reading file: {file_path}")

        msg_count = 0
        for m in reader:
            if m.err:
                continue

            self._nlri = list()
            t = list(m.data['type'])[0]
            if t == MRT_T['TABLE_DUMP_V2']:
                self._td_v2(m.data)
            else:
                print(f"This MRT Format {t} is not supported.")

            msg_count += 1
            if msg_count >= msg_limit:
                break
            if msg_count % 100000 == 0:
                elapsed_time = datetime.now() - start_time
                elapsed_seconds = elapsed_time.total_seconds()
                messages_per_second = msg_count / elapsed_seconds
                messages_left = MESSAGES_AVG - msg_count
                estimated_seconds_left = messages_left / messages_per_second

                estimated_time_left = timedelta(seconds=estimated_seconds_left)
                estimated_minutes = estimated_time_left.seconds // 60
                estimated_seconds = estimated_time_left.seconds % 60

                logger.info(
                    f"{msg_count} messages processed... Estimated time left: {estimated_minutes}:{estimated_seconds:02}"
                )

        elapsed_time = datetime.now() - start_time
        elapsed_time_formatted = str(elapsed_time).split('.')[0]
        logger.info(f"Messages Total: {msg_count}\n"
                    f"Total time elapsed: {elapsed_time_formatted}")

        return self._freeze_map()

    @staticmethod
    def import_csv(file_path: str) -> frozendict:
        """
        Import AS data from a CSV file.

        :param file_path: Path to the CSV file.
        :return: Frozen dictionary containing AS data.
        """

        as_map: dict[str, AS] = dict()

        logger.info(f"Importing data from CSV file: {file_path}")

        with open(file_path, mode='r') as csv_file:
            reader = DictReader(csv_file)
            row: OrderedDict
            for row in reader:
                as_id = row["as_id"]
                location = row["location"]
                mid_path_count = int(row["mid_path_count"])
                end_path_count = int(row["end_path_count"])
                path_sizes_dict = loads(row["path_sizes"]) if row["path_sizes"] else dict()
                path_sizes = frozenset((int(length), qnty) for length, qnty in path_sizes_dict.items())
                announced_prefixes_raw = row["announced_prefixes"]
                if announced_prefixes_raw:
                    announced_prefixes = frozenset(announced_prefixes_raw.split(";"))
                else:
                    announced_prefixes = frozenset()
                neighbours_raw = row["neighbours"]
                if neighbours_raw:
                    neighbours = frozenset(neighbours_raw.split(";"))
                else:
                    neighbours = frozenset()

                as_map[as_id] = AS(as_id, location, mid_path_count, end_path_count, path_sizes,
                                   announced_prefixes, neighbours)

        logger.info("CSV data imported successfully")

        return frozendict(as_map)

    @staticmethod
    def import_json(file_path: str) -> frozendict:
        """
        Import parsed AS data from a JSON file.

        :param file_path: Path to the JSON file.
        :return: Frozen dictionary containing AS data.
        """

        as_map: dict[str, AS] = dict()

        with open(file_path, "r") as input_file:
            input_data = json_load(input_file)

        logger.info(f"Importing data from JSON file: {file_path}")

        for as_id, as_data in input_data["as"]["as_info"].items():
            location = as_data["location"]
            mid_path_count = int(as_data["path"]["mid_path_count"])
            end_path_count = int(as_data["path"]["end_path_count"])
            path_sizes_raw = as_data["path"]["path_sizes"]
            path_sizes = frozenset((length, qnty) for length, qnty in path_sizes_raw)
            announced_prefixes_raw = as_data["prefix"]["announced_prefixes"]
            announced_prefixes = frozenset(announced_prefixes_raw)
            neighbours_raw = as_data["neighbour"]["neighbours"]
            neighbours = frozenset(neighbours_raw)

            as_map[as_id] = AS(
                as_id, location, mid_path_count, end_path_count, path_sizes, announced_prefixes, neighbours
            )

        logger.info(f"JSON data imported successfully")

        return frozendict(as_map)

    def get_location(self, as_id: str) -> str:
        """
        Get the geographical location of an AS based on its ID.

        :param as_id: Autonomous System ID.
        :return: Geographical location code.
        """

        try:
            location = self.location_map[as_id]
            if location:
                return location
            else:
                return "ZZ"
        except KeyError:
            return "ZZ"

    def _freeze_map(self) -> frozendict:
        """
        Convert the internal AS map to a frozen dictionary.

        :return: Frozen dictionary containing AS data.
        """

        as_map: dict[str, AS] = dict()

        for as_id, as_dict in self._as_map.items():
            as_map[as_id] = AS(
                as_id,
                self._as_map[as_id]["location"],
                self._as_map[as_id]["mid_path_count"],
                self._as_map[as_id]["end_path_count"],
                frozenset(self._as_map[as_id]["path_sizes"].items()),
                frozenset(self._as_map[as_id]["announced_prefixes"]),
                frozenset(self._as_map[as_id]["neighbours"])
            )

        return frozendict(as_map)

    def _parse_data(self, prefix: str) -> None:
        """
        Parse AS path data, updating statistics for each AS in the path.

        :param prefix: The prefix being announced or withdrawn.
        :return: None
        """

        path = self._merge_as_path().split()
        valid_path = list()
        for as_id in path:
            if as_id in self._as_map:
                valid_path.append(as_id)
                continue
            if as_id.startswith("{"):  # Caso o AS esteja entre {}, ele é ignorado
                valid_path.append(None)
                continue
            valid_path.append(as_id)
            self._as_map[as_id] = {
                "location": self.get_location(as_id),
                "mid_path_count": int(),
                "end_path_count": int(),
                "path_sizes": Counter(),
                "announced_prefixes": set(),
                "neighbours": set(),
            }
        path = valid_path
        path_len = len(path)

        for i, as_id in enumerate(path):
            if as_id is None:
                continue

            if i < path_len - 1:
                next_as_id = path[i + 1]
                if next_as_id is not None:
                    self._as_map[as_id]["neighbours"].add(next_as_id)
                    self._as_map[next_as_id]["neighbours"].add(as_id)
            if i == 0 or i == path_len - 1:
                self._as_map[as_id]["end_path_count"] += 1
            else:
                self._as_map[as_id]["mid_path_count"] += 1

        origin_as_id = path[-1]
        if origin_as_id is not None:
            self._as_map[origin_as_id]["path_sizes"][path_len - 1] += 1
            self._as_map[origin_as_id]["announced_prefixes"].add(prefix)

    def _export_line(self, prefix) -> None:
        """
        Write a single line of parsed data to a text file.

        :param prefix: The prefix being announced or withdrawn.
        :return: None
        """

        # TODO: optional dump to text while reading .bz2 file
        with open(Paths.DUMP_DIR / "dump.txt", "a") as output:
            if self._flag == 'B' or self._flag == 'A':
                output.write('%s|%s|%s|%s|%s|%s|%s' % (
                    self._type, self._ts, self._flag, self._peer_ip, self._peer_as, prefix, self._merge_as_path()))
                output.write('\n')
            elif self._flag == 'W':
                output.write(
                    '%s|%s|%s|%s|%s|%s\n' % (self._type, self._ts, self._flag, self._peer_ip, self._peer_as, prefix))

    def _parse_routes(self) -> None:
        """
        Process routes (withdrawn and announced) and parse the data.

        :return: None
        """

        for withdrawn in self._withdrawn:
            if self._type == 'BGP4MP':
                self._flag = 'W'
                self._parse_data(withdrawn)
        for nlri in self._nlri:
            if self._type == 'BGP4MP':
                self._flag = 'A'
            for _ in self._next_hop:
                self._parse_data(nlri)

    def _td_v2(self, m) -> None:
        """
        Handle TABLE_DUMP_V2 type BGP messages.

        :param m: Message data.
        :return: None
        """

        global peer
        self._type = 'TABLE_DUMP2'
        self._flag = 'B'
        self._ts = list(m['timestamp'])[0]
        st = list(m['subtype'])[0]
        if st == TD_V2_ST['PEER_INDEX_TABLE']:
            peer = copy(m['peer_entries'])
        elif (
                st == TD_V2_ST['RIB_IPV4_UNICAST'] or
                st == TD_V2_ST['RIB_IPV4_MULTICAST'] or
                st == TD_V2_ST['RIB_IPV6_UNICAST'] or
                st == TD_V2_ST['RIB_IPV6_MULTICAST']
        ):
            self._nlri.append('%s/%d' % (m['prefix'], m['length']))
            for entry in m['rib_entries']:

                self._peer_ip = peer[entry['peer_index']]['peer_ip']
                self._peer_as = peer[entry['peer_index']]['peer_as']
                self._as_path = []
                self._next_hop = []
                self._as4_path = []
                for attr in entry['path_attributes']:
                    self._bgp_attr(attr)
                self._parse_routes()

    def _bgp_attr(self, attr) -> None:
        """
        Process BGP path attributes to extract necessary routing information.

        :param attr: Path attribute data.
        :return: None
        """

        attr_t = list(attr['type'])[0]
        if attr_t == BGP_ATTR_T['NEXT_HOP']:
            self._next_hop.append(attr['value'])
        elif attr_t == BGP_ATTR_T['AS_PATH']:
            self._as_path = []
            for seg in attr['value']:
                seg_t = list(seg['type'])[0]
                if seg_t == AS_PATH_SEG_T['AS_SET']:
                    self._as_path.append('{%s}' % ','.join(seg['value']))
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self._as_path.append('(' + seg['value'][0])
                    self._as_path += seg['value'][1:-1]
                    self._as_path.append(seg['value'][-1] + ')')
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self._as_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self._as_path += seg['value']
        elif attr_t == BGP_ATTR_T['MP_REACH_NLRI']:
            self._next_hop = attr['value']['next_hop']
            if self._type != 'BGP4MP':
                return
            for nlri in attr['value']['nlri']:
                self._nlri.append('%s/%d' % (nlri['prefix'], nlri['length']))
        elif attr_t == BGP_ATTR_T['MP_UNREACH_NLRI']:
            if self._type != 'BGP4MP':
                return
            for withdrawn in attr['value']['withdrawn_routes']:
                self._withdrawn.append('%s/%d' % (withdrawn['prefix'], withdrawn['length']))
        elif attr_t == BGP_ATTR_T['AS4_PATH']:
            self._as4_path = []
            for seg in attr['value']:
                seg_t = list(seg['type'])[0]
                if seg_t == AS_PATH_SEG_T['AS_SET']:
                    self._as4_path.append('{%s}' % ','.join(seg['value']))
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self._as4_path.append('(' + seg['value'][0])
                    self._as4_path += seg['value'][1:-1]
                    self._as4_path.append(seg['value'][-1] + ')')
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self._as4_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self._as4_path += seg['value']

    def _merge_as_path(self) -> str:
        """
        Merge AS paths, including AS4 paths if available.

        :return: Merged AS path as a string.
        """

        if len(self._as4_path):
            n = len(self._as_path) - len(self._as4_path)
            return ' '.join(self._as_path[:n] + self._as4_path)
        else:
            return ' '.join(self._as_path)
