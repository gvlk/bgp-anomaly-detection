from copy import copy
from datetime import datetime, timedelta
from json import dump as json_dump, load as json_load
from pathlib import Path
from pickle import dump as pickle_dump, load as pickle_load

from mrtparse import Reader, MRT_T, TD_V2_ST, BGP_ATTR_T, AS_PATH_SEG_T

from .autonomous_system import AS
from .logging import Logger
from .paths import Paths

peer = None

logger = Logger.get_logger(__name__)


class SnapShot:
    """
    Represents a snapshot of Border Gateway Protocol (BGP) data, facilitating import, processing, and export of
    Autonomous System (AS) routing information from various file formats. Supported formats include .bz2 for raw BGP
    data, .json or .csv for parsed AS data, and .pkl for serialized SnapShot instances.

    The class parses BGP messages from the specified file, updating attributes such as snapshot time, AS paths,
    prefixes, and peer information. Parsed AS information can be exported to JSON, CSV, or pickled formats for
    further analysis or archival purposes.
    """

    __slots__ = [
        "_file_path", "_type", "_ts", "_flag",
        "_peer_ip", "_peer_as", "_nlri", "_withdrawn",
        "_as_path", "_next_hop", "_as4_path",
        "_export_to_file", "known_as", "snapshot_time"
    ]

    def __init__(self, file_path: str | Path) -> None:
        """
        The raw BGP data file can be in one of three formats:

        - .bz2: Raw BGP data file
        - .json: JSON file containing parsed AS data
        - ".csv": CSV file containing parsed AS data
        - .pkl: Pickle file containing a previously saved SnapShot instance
        """

        self._file_path = Path(file_path)
        file_extension = self._file_path.suffix.lower()
        if file_extension == ".pkl":
            self._import_pickle()
            return

        base_name = self._file_path.stem.split('.')
        date_part = base_name[1]
        time_part = base_name[2]
        date_time_str = date_part + time_part

        self.snapshot_time = datetime.strptime(date_time_str, '%Y%m%d%H%M')
        self.known_as: dict[str, AS] = dict()

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
        self._export_to_file = False

        if file_extension == ".bz2":
            self._import_bz2()
        elif file_extension == ".json":
            self._import_json()

    def __repr__(self) -> str:
        """Return the file name of the BGP data file."""

        return self._file_path.name

    def __eq__(self, snapshot_instance) -> bool:
        """Compare two SnapShot instances for equality based on their snapshot times."""

        if isinstance(snapshot_instance, SnapShot):
            return self.snapshot_time == snapshot_instance.snapshot_time
        else:
            return NotImplemented

    def __hash__(self) -> int:
        """Return a hash value based on the snapshot time."""

        return hash(self.snapshot_time)

    def _import_bz2(self) -> None:
        """Iterate over messages in the BGP data file, processing them and logging progress."""

        reader = Reader(str(self._file_path))
        start_time = datetime.now()

        if not self._export_to_file:
            logger.info(f"Reading file: {self._file_path}")
        else:
            logger.info(f"Dumping file: {self._file_path}")

        total_messages = 1154829  # Average number of messages in a snapshot .bz2 file
        count = 0

        for m in reader:
            if m.err:
                continue

            self._nlri = list()
            t = list(m.data['type'])[0]
            if t == MRT_T['TABLE_DUMP_V2']:
                self._td_v2(m.data)
            else:
                print(f"This MRT Format {t} is not supported.")

            count += 1
            if count % 100000 == 0:
                elapsed_time = datetime.now() - start_time
                elapsed_seconds = elapsed_time.total_seconds()
                messages_per_second = count / elapsed_seconds if elapsed_seconds > 0 else 0
                messages_left = total_messages - count
                estimated_seconds_left = messages_left / messages_per_second if messages_per_second > 0 else 0

                estimated_time_left = timedelta(seconds=estimated_seconds_left)
                estimated_minutes = estimated_time_left.seconds // 60
                estimated_seconds = estimated_time_left.seconds % 60

                logger.info(
                    f"{count} messages processed... Estimated time left: {estimated_minutes}:{estimated_seconds:02}"
                )

        elapsed_time = datetime.now() - start_time
        elapsed_time_formatted = str(elapsed_time).split('.')[0]
        logger.info(f"Messages Total: {count}")
        logger.info(f"Total time elapsed: {elapsed_time_formatted}")

    def _import_json(self) -> None:
        """Import parsed AS data from a JSON file."""

        with open(self._file_path, "r") as input_file:
            input_data = json_load(input_file)

        logger.info(f"Importing data from JSON file: {self._file_path}")

        for as_id, as_data in input_data["as"]["as_info"].items():
            self.known_as[as_id] = AS(as_id)
            self.known_as[as_id].import_data(as_data)

        logger.info(f"JSON data imported successfully")

    def _import_pickle(self) -> None:
        """Load SnapShot instance from a pickle file."""

        logger.info(f"Loading SnapShot instance from: {self._file_path}")

        with open(self._file_path, "rb") as file:
            snapshot_instance = pickle_load(file)

        for slot in self.__slots__:
            setattr(self, slot, getattr(snapshot_instance, slot))

        logger.info(f"SnapShot instance loaded successfully")

    def _parse_data(self, prefix: str) -> None:
        """
        Parse AS path data, updating statistics for each AS in the path.

        :param prefix: The prefix being announced or withdrawn.
        """

        path = self._merge_as_path().split()
        valid_path = list()
        for as_id in path:
            if as_id in self.known_as:
                valid_path.append(as_id)
            else:
                try:
                    self.known_as[as_id] = AS(as_id)
                except ValueError:  # Caso o AS esteja entre {}, ele é ignorado
                    valid_path.append(None)
                    continue
                else:
                    valid_path.append(as_id)
        path = valid_path

        for i, as_id in enumerate(path):
            if as_id is None:
                continue
            current_as = self.known_as[as_id]
            current_as.times_seen += 1

            if i < len(path) - 1:
                next_as_id = path[i + 1]
                if next_as_id is not None:
                    next_as = self.known_as[next_as_id]
                    current_as.neighbours.add(next_as.id)
                    next_as.neighbours.add(current_as.id)
            if i == 0 or i == len(path) - 1:
                current_as.n_end_path += 1
            else:
                current_as.n_mid_path += 1

        origin_as_id = path[-1]
        if origin_as_id is not None:
            origin_as = self.known_as[origin_as_id]
            origin_as.path_sizes[len(path) - 1] += 1
            origin_as.announced_prefixes.add(prefix)

    def _export_line(self, prefix) -> None:
        """
        Write a single line of parsed data to a text file.

        :param prefix: The prefix being announced or withdrawn.
        """

        with open(Paths.DUMP_DIR / (self._file_path.stem + ".txt"), "a") as output:
            if self._flag == 'B' or self._flag == 'A':
                output.write('%s|%s|%s|%s|%s|%s|%s' % (
                    self._type, self._ts, self._flag, self._peer_ip, self._peer_as, prefix, self._merge_as_path()))
                output.write('\n')
            elif self._flag == 'W':
                output.write(
                    '%s|%s|%s|%s|%s|%s\n' % (self._type, self._ts, self._flag, self._peer_ip, self._peer_as, prefix))

    def _print_routes(self) -> None:
        """Process routes (withdrawn and announced) and either export or parse the data."""

        for withdrawn in self._withdrawn:
            if self._type == 'BGP4MP':
                self._flag = 'W'
            if self._export_to_file:
                self._export_line(withdrawn)
            else:
                self._parse_data(withdrawn)
        for nlri in self._nlri:
            if self._type == 'BGP4MP':
                self._flag = 'A'
            for _ in self._next_hop:
                if self._export_to_file:
                    self._export_line(nlri)
                else:
                    self._parse_data(nlri)

    def _td_v2(self, m) -> None:
        """
        Handle TABLE_DUMP_V2 type BGP messages.

        :param m: Message data.
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
                self._print_routes()

    def _bgp_attr(self, attr) -> None:
        """
        Process BGP path attributes to extract necessary routing information.

        :param attr: Path attribute data.
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

    def export_json(self, destination_dir: str | Path = "") -> None:
        """
        Export parsed AS data to a JSON file.

        :param destination_dir: Directory path where the JSON file will be saved.
        :return: None
        """

        if not destination_dir:
            destination_dir = Paths.PARSED_DIR
        else:
            destination_dir = Path(destination_dir)

        logger.info(f"Exporting data to JSON")

        formatted_date_time = self.snapshot_time.strftime('%d/%m/%Y %H:%M')

        as_info = dict()
        for as_id in self.known_as:
            as_info[as_id] = self.known_as[as_id].export()

        output_data = {
            "snapshot_time": formatted_date_time,
            "as": {
                "as_total": len(self.known_as),
                "as_info": as_info
            }
        }

        parsed_data_file_path = destination_dir / (self._file_path.stem + ".json")
        with open(parsed_data_file_path, "w") as output:
            json_dump(output_data, output, indent=4)

        logger.info(f"Parsed data saved at: {parsed_data_file_path}")

    def export_csv(self, destination_dir: str | Path = "") -> None:
        pass

    def export_pickle(self, destination_dir: str | Path = ""):
        """Save the SnapShot instance to a pickle file."""

        if not destination_dir:
            destination_dir = Paths.PICKLE_DIR
        else:
            destination_dir = Path(destination_dir)

        logger.info(f"Exporting instance to pickle file")

        save_path = destination_dir / (self._file_path.stem + ".pkl")
        with open(save_path, "wb") as file:
            pickle_dump(self, file)

        logger.info(f"SnapShot instance saved successfully at: {save_path}")

    def dump_to_txt(self) -> None:
        """Read an MRT format file, process each message, and dump parsed information into a text file."""

        logger.info(f"Starting dumping")
        self._export_to_file = True
        self._import_bz2()
        logger.info(f"Finished dumping. New file saved at '{Paths.DUMP_DIR}'")

    def reset(self) -> None:
        """
        Reset all instance attributes to their initial state.
        """
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
        self._export_to_file = False
        self.known_as.clear()
        self.snapshot_time = None
