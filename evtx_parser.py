#!/usr/bin/env python
#    This file is a simple script to convert EVTx file
#   generated by NetApp nodes running ONTAP clustered
#   to bunch of txt files to grep from
#   Script contains part of python-evtx evtx_filter_records script.
#
#   Copyright 2017 Evgeny Litvinov
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#   In fact I don't care how you can use this file, but if it happens 
#   that you earn something - find me and send a couple of beer cans
#
#   

from lxml import etree, objectify

from Evtx.Evtx import Evtx
from Evtx.Views import evtx_file_xml_view

# need some stuff
from datetime import date, datetime
import copy
import yaml
from os import listdir,stat
from os.path import isfile, join

# Constants
import evtx_parser_dict
SETTINGSFILE = 'evtx_parser.yaml'

### this is part of evtx_filter_records.py script from Evtx.Evtx
# Copyright 2012, 2013 Willi Ballenthin <william.ballenthin@mandiant.com>
#     while at Mandiant <http://www.mandiant.com>
def to_lxml(record_xml):
    """
    @type record: Record
    """
    #xml = .encode('utf-8')
    return etree.fromstring("<?xml version=\"1.0\" encoding=\"utf-8\" standalone=\"yes\" ?>%s" %
                         record_xml.encode('utf-8'))


def xml_records(filename):
    """
    If the second return value is not None, then it is an
      Exception encountered during parsing.  The first return value
      will be the XML string.

    @type filename str
    @rtype: generator of (etree.Element or str), (None or Exception)
    """
    with Evtx(filename) as evtx:
        for xml, record in evtx_file_xml_view(evtx.get_file_header()):
            try:
                yield to_lxml(xml), None
            except etree.XMLSyntaxError as e:
                yield xml, e


def get_child(node, tag, ns="{http://schemas.microsoft.com/win/2004/08/events/event}"):
    """
    @type node: etree.Element
    @type tag: str
    @type ns: str
    """
    return node.find("%s%s" % (ns, tag))

#####

# parse a single file
def parse_file(file):
    strings_tuples = []
    for node, err in xml_records(file):
        if err is not None:
            continue

        # we get XML dom besause evtx has xml compressed events
        root = objectify.fromstring(etree.tostring(node))

        # filter eids
        eid = root.System.EventID.text
        if eid in evtx_parser_dict.EVENTIDCODES.keys(): 
            # evtx_parser_dict.EVENTIDCODES:
            # '4656': Open Object/Create Object
            # '4659': Open Object with the Intent to Delete
            # '4663': Read Object/Write Object/Get Object Attributes/Set Object Attributes
            # '4907': SACL changes

            # data from System node
            eventname = evtx_parser_dict.EVENTIDCODES[eid] 

            # init the string elements to fetch from EventData.Data subtree
            timestamp = datetime.strptime(root.System.TimeCreated.attrib['SystemTime'], '%Y-%m-%d %H:%M:%S.%f')
            path = ''
            user = ''
            domain = ''
            ip = ''
            aids = ''          

            for data in root.EventData.Data:
                if data.attrib['Name'] == 'ObjectName':
                    path = data.text
                elif data.attrib['Name'] == 'SubjectUserName':
                    user = data.text
                elif data.attrib['Name'] == 'SubjectDomainName':
                    domain = data.text
                elif data.attrib['Name'] == 'SubjectIP':
                    ip = data.text
                elif data.attrib['Name'] == 'DesiredAccess ':
                    aids = data.text
                else:
                    pass
        
            # string assemble:
            string = "\t%s\t%s\t%s\t%s\t%s".expandtabs() % (
                    path, user, domain, ip, aids
                )
            strings_tuples.append((timestamp, string))

    return strings_tuples


# seek evtx-es in dir, regarging to last parsed file end offset
# return the dict of { <filename> : [ strings ]}
#TODO use offset for _last file only
def parse_dir(scrdir, dstdir, lastfile, offset):
    # do not parse '*_last' evtx, beacause it is still filled
    files = [f for f in listdir(scrdir) if (isfile(join(scrdir, f)) and f.find('_last') == -1)]

    # filter out files older than lastfile's ctime
    evtxfiles = []
    if isfile(join(scrdir, lastfile)):
        lasttimestamp = stat(join(scrdir, lastfile)).st_mtime
        # select files newer than lastfile
        for f in files:
            if stat(join(scrdir, f)).st_mtime > lasttimestamp:
                evtxfiles.append(f) 
    else:
        evtxfiles = copy.deepcopy(files)

    parsed = {}
    last_parsed_file = ''
    for evtxfile in evtxfiles:
        strings = parse_file(join(scrdir, evtxfile))
        for timestamp, string in strings:
            stamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            fname = timestamp.strftime('%Y-%m-%d.txt')
            fpath = join(dstdir, fname)
            if not fpath in parsed:
                parsed[fpath] = []
            parsed[fpath].append("%s\t%s".expandtabs() % (stamp,string))
        last_parsed_file = evtxfile

    return [ parsed, last_parsed_file, offset ]

# write txt files from parced dict
def dump_events(parsed):
    for outfilename in parsed.keys():
        with open(outfilename, "a") as outfile:
            for string in parsed[outfilename]:
                outfile.write("%s\n" % string)


# main finction
def main():
    # read settings
    with open(SETTINGSFILE, 'r') as stream:
        try:
            settings = yaml.load(stream)
            # to write offset
            wrsettings = copy.deepcopy(settings)
            print(settings)
        except yaml.YAMLError as exc:
            print("ERROR: cannot read settings file %s" % SETTINGSFILE)
            print(exc)
            exit(1)

    # Cycle for src directories
    try:
        srcdids_settings = settings['srcdirs']
        for srcdir in srcdids_settings.keys():
            [ parsed, lastfile, offset ] = parse_dir(srcdir, settings['dstdir'], 
                srcdids_settings[srcdir]['lastfile'], srcdids_settings[srcdir]['offset'])
            wrsettings['srcdirs'][srcdir]['lastfile'] = lastfile
            wrsettings['srcdirs'][srcdir]['offset'] = offset
    except Exception as exc:
            print("ERROR: cannot read evtx files")
            print(exc)
            exit(1)

    # write files and exit
    try:
        dump_events(parsed)
        with open(SETTINGSFILE, "w") as outfile:
            outfile.write(yaml.dump(wrsettings, default_flow_style=False, allow_unicode=True))
    except Exception as exc:
            print("ERROR: cannot write events and settings")
            print(exc)
            exit(1)

    # success
    exit(0)

if __name__ == "__main__":
    main()