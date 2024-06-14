from bgp_parser import BGPParser
from pickle import dump
import mrtparse
from mrt2bgpdump import BgpDump
from collections import OrderedDict


def main():
    data: OrderedDict = OrderedDict()
    args = parse_args()
    d = mrtparse.Reader("../bgp_data/rib.20131101.1200.bz2")
    count = 0
    for m in d:
        if m.err:
            continue
        b = BgpDump(args)
        data = m.data
        t = list(data['type'])[0]
        if t == MRT_T['TABLE_DUMP']:
            b.td(data, count)
        elif t == MRT_T['TABLE_DUMP_V2']:
            b.td_v2(data)
        elif t == MRT_T['BGP4MP']:
            b.bgp4mp(data, count)
        count += 1


if __name__ == '__main__':
    main()
