#!/usr/bin/env python

import uuid
from common.pcapstreams import create_streams
from collections import OrderedDict
from common.pcaptools import *
from common.hashmethods import *
from common.dbconnect import mongo_connect, find_session
from common.entities import pcapFile
from canari.maltego.message import UIMessage
from canari.framework import configure
from canari.config import config

__author__ = 'catalyst256'
__copyright__ = 'Copyright 2014, sniffmypacketsv2 Project'
__credits__ = []

__license__ = 'GPL'
__version__ = '0.1'
__maintainer__ = 'catalyst256'
__email__ = 'catalyst256@gmail.com'
__status__ = 'Development'

__all__ = [
    'dotransform'
]


@configure(
    label='Get TCP/UDP Streams',
    description='Extract TCP/UDP streams from pcap file',
    uuids=['sniffMyPackets.v2.pcap_2_streams'],
    inputs=[('[SmP] - Streams', pcapFile)],
    debug=True
)
def dotransform(request, response):
    pcap = request.value
    folder = ''
    usedb = config['working/usedb']
    # Check to see if we are using the database or not
    if usedb > 0:
        # Connect to the database so we can insert the record created below
        x = mongo_connect()
        c = x['STREAMS']
        # Hash the pcap file
        try:
            md5hash = md5_for_file(pcap)
            d = find_session(md5hash)
            pcap_id = d[0]
            folder = d[2]
        except Exception as e:
            return response + UIMessage(str(e))
    else:
        w = config['working/directory'].strip('\'')
        try:
            if w != '':
                w = w + '/' + str(uuid.uuid4())[:12].replace('-', '')
                if not os.path.exists(w):
                    os.makedirs(w)
                folder = w
            else:
                return response + UIMessage('No working directory set, check your config file')
        except Exception as e:
            return response + UIMessage(e)

    # Create TCP/UDP stream files
    s = create_streams(pcap, folder)
    if usedb > 0:
        for i in s:
            # Create StreamID
            streamid = str(uuid.uuid4())[:8]
            # Get a count of packets available
            try:
                pkcount = packet_count(i)
            except Exception as e:
                return response + UIMessage(str(e))
            # Get the start/end time of packets
            try:
                pcap_time = get_time(i)
            except Exception as e:
                return response + UIMessage(str(e))
            # Hash the pcap file
            try:
                md5hash = md5_for_file(i)
                sha1hash = sha1_for_file(i)
            except Exception as e:
                return response + UIMessage(str(e))

            # Pull out the details of the packets
            l = len(folder) + 1
            raw = i[l:-5]
            pkt = raw.replace('-', ' ').replace(':', ' ').split()

            # Create the dictonary object to insert into database
            data = OrderedDict({'PCAP ID': pcap_id, 'Stream ID': streamid, 'Folder': folder, 'Packet Count': pkcount,
                                'File Name': i, 'First Packet': pcap_time[0], 'Last Packet': pcap_time[1],
                                'MD5 Hash': md5hash, 'SHA1 Hash': sha1hash,
                                'Packet': {'Protocol': pkt[0], 'Source IP': pkt[1], 'Source Port': pkt[2],
                                           'Destination IP': pkt[3], 'Destination Port': pkt[4]}})

            # Check to see if the record exists
            try:
                t = x.STREAMS.find({"File Name": i}).count()
                if t > 0:
                    pass
                else:
                    c.insert(data)
            except Exception as e:
                return response + UIMessage(str(e))
    else:
        pass
    # Create Maltego entities for each pcap file
    for p in s:
        e = pcapFile(p)
        response += e
    return response
