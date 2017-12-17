#!/usr/bin/env python
#    This file is part of evtx_parser.
#
#   No copyright 2017
#   see Event ID (EVT/EVTX)	for more details
#   https://library.netapp.com/ecm/ecm_download_file/ECMLP2494084
#

EVENTIDCODES = {
    '4656': "Open Object/Create Object",
    '4659': "Open Object with the Intent to Delete",
    '4663': "Read Object/Write Object/Get Object Attributes/Set Object Attributes",
    '4907': "SACL changes"
}

AID = {
    '%%1537' : 'DELETE',
    '%%1539' : 'WRITE_DAC',
    '%%1540' : 'WRITE_OWNER',
    '%%4416' : 'ReadData (or ListDirectory)',
    '%%4417' : 'WriteData (or AddFile)',
    '%%4418' : 'AppendData (or AddSubdirectory)',
    '%%4419' : 'ReadEA',
    '%%4420' : 'WriteEA',
    '%%4421' : 'Execute',
    '%%4422' : 'DeleteChild',
    '%%4423' : 'ReadAttributes',
    '%%4424' : 'WriteAttributes'
}
    