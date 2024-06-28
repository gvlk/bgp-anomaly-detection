from copy import copy
from datetime import datetime
from json import dump
from pathlib import Path

from mrtparse import Reader, MRT_T, TD_V2_ST, BGP_ATTR_T, AS_PATH_SEG_T

from .logging import *
from .autonomous_system import AS

peer = None


class SnapShot:
    __slots__ = ['raw_file_path', 'reader', 'dump_folder', 'parsed_folder', 'type', 'ts', 'flag', 'peer_ip', 'peer_as',
                 'nlri',
                 'withdrawn', 'as_path', 'next_hop', 'as4_path', 'export_to_file', 'known_as']

    def __init__(self, raw_file_path: str | Path):
        """
        :param raw_file_path: Path to the raw BGP data file.
        """

        self.raw_file_path = Path(raw_file_path)
        self.reader = Reader(str(self.raw_file_path))
        self.dump_folder = Path("data", "dumps")
        self.parsed_folder = Path("data", "parsed")
        self.dump_folder.mkdir(parents=True, exist_ok=True)
        self.parsed_folder.mkdir(parents=True, exist_ok=True)

        self.type = ''
        self.ts = 0
        self.flag = ''
        self.peer_ip = ''
        self.peer_as = 0
        self.nlri = []
        self.withdrawn = []
        self.as_path = []
        self.next_hop = []
        self.as4_path = []

        self.known_as: dict[str, AS] = dict()

        self.export_to_file = False

        self.iterate()

    def parse_data(self, prefix: str):
        """
        Parse AS path data, updating statistics for each AS in the path.

        :param prefix: The prefix being announced or withdrawn.
        """

        path = self.merge_as_path().split()
        for as_id in path:
            if as_id not in self.known_as:
                try:
                    self.known_as[as_id] = AS(as_id)
                except ValueError:  # Caso em que o AS está entre {}. O caminho é ignorado
                    return

        for i, as_id in enumerate(path):
            current_as = self.known_as[as_id]
            current_as.times_seen += 1

            if i < len(path) - 1:
                next_as = self.known_as[path[i + 1]]
                current_as.neighbours.add(next_as)
                next_as.neighbours.add(current_as)
            if i == 0 or i == len(path) - 1:
                current_as.n_end_path += 1
            else:
                current_as.n_mid_path += 1

        origin_as = self.known_as[path[-1]]
        origin_as.path_sizes.append(len(path) - 1)
        origin_as.announced_prefixes.add(prefix)

    def export(self):
        """
        Export parsed AS data to a JSON file.
        """

        logging.info(f"Exporting data to JSON")

        base_name = self.raw_file_path.stem.split('.')
        date_part = base_name[1]
        time_part = base_name[2]
        date_time_str = date_part + time_part
        date_time_obj = datetime.strptime(date_time_str, '%Y%m%d%H%M')
        formatted_date_time = date_time_obj.strftime('%d/%m/%Y %H:%M')

        as_info = dict()
        for as_id, as_obj in self.known_as.items():
            n_paths = len(as_obj.path_sizes)
            if n_paths == 0:
                mean_path_size = 0
            else:
                mean_path_size = round(sum(as_obj.path_sizes) / n_paths, 1)
            as_info[as_id] = {
                "times_seen": as_obj.times_seen,
                "n_mid_path": as_obj.n_mid_path,
                "n_end_path": as_obj.n_end_path,
                "path": {
                    "mean_path_size": mean_path_size,
                    "path_sizes": tuple(as_obj.path_sizes)
                },
                "prefix": {
                    "total_prefixes": len(as_obj.announced_prefixes),
                    "announced_prefixes": tuple(as_obj.announced_prefixes)
                },
                "neighbour": {
                    "total_neighbours": len(as_obj.neighbours),
                    "neighbours": tuple(neighbour.id for neighbour in as_obj.neighbours)
                },
            }

        output_data = {
            "snapshot_time": formatted_date_time,
            "as": {
                "as_total": len(self.known_as),
                "as_info": as_info
            }
        }

        parsed_data_file_path = self.parsed_folder / (self.raw_file_path.stem + ".json")
        with open(parsed_data_file_path, "w") as output:
            dump(output_data, output, indent=4)

        logging.info(f"Parsed data saved at: {parsed_data_file_path}")

    def export_line(self, prefix):
        """
        Write a single line of parsed data to a text file.

        :param prefix: The prefix being announced or withdrawn.
        """

        with open(self.dump_folder / (self.raw_file_path.stem + ".txt"), "a") as output:
            if self.flag == 'B' or self.flag == 'A':
                output.write('%s|%s|%s|%s|%s|%s|%s' % (
                    self.type, self.ts, self.flag, self.peer_ip, self.peer_as, prefix, self.merge_as_path()))
                output.write('\n')
            elif self.flag == 'W':
                output.write(
                    '%s|%s|%s|%s|%s|%s\n' % (self.type, self.ts, self.flag, self.peer_ip, self.peer_as, prefix))

    def print_routes(self):
        """
        Process routes (withdrawn and announced) and either export or parse the data.
        """

        for withdrawn in self.withdrawn:
            if self.type == 'BGP4MP':
                self.flag = 'W'
            if self.export_to_file:
                self.export_line(withdrawn)
            else:
                self.parse_data(withdrawn)
        for nlri in self.nlri:
            if self.type == 'BGP4MP':
                self.flag = 'A'
            for _ in self.next_hop:
                if self.export_to_file:
                    self.export_line(nlri)
                else:
                    self.parse_data(nlri)

    def td_v2(self, m):
        """
        Handle TABLE_DUMP_V2 type BGP messages.

        :param m: Message data.
        """

        global peer
        self.type = 'TABLE_DUMP2'
        self.flag = 'B'
        self.ts = list(m['timestamp'])[0]
        st = list(m['subtype'])[0]
        if st == TD_V2_ST['PEER_INDEX_TABLE']:
            peer = copy(m['peer_entries'])
        elif (st == TD_V2_ST['RIB_IPV4_UNICAST'] or st == TD_V2_ST['RIB_IPV4_MULTICAST'] or st == TD_V2_ST[
            'RIB_IPV6_UNICAST'] or st == TD_V2_ST['RIB_IPV6_MULTICAST']):
            self.nlri.append('%s/%d' % (m['prefix'], m['length']))
            for entry in m['rib_entries']:

                self.peer_ip = peer[entry['peer_index']]['peer_ip']
                self.peer_as = peer[entry['peer_index']]['peer_as']
                self.as_path = []
                self.next_hop = []
                self.as4_path = []
                for attr in entry['path_attributes']:
                    self.bgp_attr(attr)
                self.print_routes()

    def bgp_attr(self, attr):
        """
        Process BGP path attributes to extract necessary routing information.

        :param attr: Path attribute data.
        """

        attr_t = list(attr['type'])[0]
        if attr_t == BGP_ATTR_T['NEXT_HOP']:
            self.next_hop.append(attr['value'])
        elif attr_t == BGP_ATTR_T['AS_PATH']:
            self.as_path = []
            for seg in attr['value']:
                seg_t = list(seg['type'])[0]
                if seg_t == AS_PATH_SEG_T['AS_SET']:
                    self.as_path.append('{%s}' % ','.join(seg['value']))
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self.as_path.append('(' + seg['value'][0])
                    self.as_path += seg['value'][1:-1]
                    self.as_path.append(seg['value'][-1] + ')')
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self.as_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self.as_path += seg['value']
        elif attr_t == BGP_ATTR_T['MP_REACH_NLRI']:
            self.next_hop = attr['value']['next_hop']
            if self.type != 'BGP4MP':
                return
            for nlri in attr['value']['nlri']:
                self.nlri.append('%s/%d' % (nlri['prefix'], nlri['length']))
        elif attr_t == BGP_ATTR_T['MP_UNREACH_NLRI']:
            if self.type != 'BGP4MP':
                return
            for withdrawn in attr['value']['withdrawn_routes']:
                self.withdrawn.append('%s/%d' % (withdrawn['prefix'], withdrawn['length']))
        elif attr_t == BGP_ATTR_T['AS4_PATH']:
            self.as4_path = []
            for seg in attr['value']:
                seg_t = list(seg['type'])[0]
                if seg_t == AS_PATH_SEG_T['AS_SET']:
                    self.as4_path.append('{%s}' % ','.join(seg['value']))
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self.as4_path.append('(' + seg['value'][0])
                    self.as4_path += seg['value'][1:-1]
                    self.as4_path.append(seg['value'][-1] + ')')
                elif seg_t == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self.as4_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self.as4_path += seg['value']

    def merge_as_path(self):
        """
        Merge AS paths, including AS4 paths if available.

        :return: Merged AS path as a string.
        """

        if len(self.as4_path):
            n = len(self.as_path) - len(self.as4_path)
            return ' '.join(self.as_path[:n] + self.as4_path)
        else:
            return ' '.join(self.as_path)

    def dump_to_txt(self) -> None:
        """
        Read an MRT format file (BGP routing data), process each message, and dump parsed information into a text file.

        :return: None
        """

        self.export_to_file = True
        self.iterate()
        logging.info(f"Finished. New file saved at '{self.dump_folder}'")

    def iterate(self):
        """
        Iterate over messages in the BGP data file, processing them and logging progress.

        :return: None
        """

        if not self.export_to_file:
            logging.info(f"Reading file: {self.raw_file_path}")
        else:
            logging.info(f"Dumping file: {self.raw_file_path}")
        count = 0
        for m in self.reader:
            if m.err:
                continue
            self.nlri = []
            t = list(m.data['type'])[0]
            if t == MRT_T['TABLE_DUMP_V2']:
                self.td_v2(m.data)
            else:
                print(f"This MRT Format {t} is not supported.")

            count += 1
            if count % 5000 == 0:
                logging.info(f"Processed {count} messages")

        logging.info(f"Total messages: {count}")
