#!/usr/local/bin/python

import sys
from pprint import pprint
from operator import attrgetter
from optparse import OptionParser

import boto
from boto.ec2 import regions
from boto.ec2 import get_region

REGIONS = {
        'ue': 'us-east-1',
        'uw1': 'us-weat-1',
        'uw2': 'us-west-2',
        'as': 'ap-southeast-1',
        'an': 'ap-northeast-1',
}


HEADERS = {
    'ID': {'get': attrgetter('id'), 'length':15},
    'Zone': {'get': attrgetter('placement'), 'length':20},
    'Groups': {'get': attrgetter('groups'), 'length':30},
    'Hostname': {'get': attrgetter('public_dns_name'), 'length':50},
    'PrivateHostname': {'get': attrgetter('private_dns_name'), 'length':50},
    'State': {'get': attrgetter('state'), 'length':20},
    'Image': {'get': attrgetter('image_id'), 'length':15},
    'Type': {'get': attrgetter('instance_type'), 'length':20},
    'PrivateIP': {'get': attrgetter('private_ip_address'), 'length':16},
    'PublicIP': {'get': attrgetter('ip_address'), 'length':16},
    'Key': {'get': attrgetter('key_name'), 'length':25},
    'LaunchTime': {'get': attrgetter('launch_time'), 'length':20},
    'StateReason': {'get': attrgetter('state_reason'), 'length':20},
    'T:': {'length': 30},
}

def zkParser(filePath):
    import ConfigParser
    configInfo = {}
    config = ConfigParser.ConfigParser()
    try:
        config.read(filePath)
    except:
        msgerr = "cannot find this file %s % filePath"
        return False, msgerr

    for section in config.sections():
        configInfo[section] = {}

    for section in config.sections():
        for option in config.options(section):
            configInfo[section][option] = config.get(section, option)

    if configInfo:
        return True, configInfo
    else:
        msgerr = "empty file %s % filePath"
        return False, msgerr

def get_column(name, instance=None):
    if name.startswith('T:'):
        if '.filter=' in name:
            key = name.split(':')[1].split('.filter=')[0]
            value = name.split(':')[1].split('.filter=')[1]
            result = instance.tags.get(key, '')
            if value not in result:
                return name, None
            else:
                return name, result
        elif '=' in name:
            key = name.split(':')[1].split('=')[0]
            value = name.split(':')[1].split('=')[1]
            if value != instance.tags.get(key, ''):
                return name, None
            else:
                return name, value
        else:
            _, tag = name.split(':', 1)
            return name, instance.tags.get(tag, '')

    elif '.filter=' in name:
        key = name.split('.filter=')[0]
        value = name.split('.filter=')[1]
        result = HEADERS[key]['get'](instance)
        if value not in result:
            return name, None
        else:
            return name, result
    elif '=' in name:
        key = name.split('=')[0]
        value = name.split('=')[1]
        if value != HEADERS[key]['get'](instance):
            return name, None
        else:
            return name, value
    return name, HEADERS[name]['get'](instance)

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", help="Boto configuration (default: /etc/mboto.cfg)", dest="keycfg", default="/etc/mboto.cfg")
    parser.add_option("-a", "--account", help="The aws account from boto config", dest="account")
    parser.add_option("-r", "--region", help="Region: ue, uw2, as, etc. (default: ue)", dest="region", default="ue")
    parser.add_option("-H", "--headers", help="Set headers - use 'T:tagname' for including tags; use 'Status=running' to filter; use 'T:Name.filter=6016 to filter more. ", default="ID,Zone,State,PublicIP,PrivateIP,T:Name,T:Role", action="store", dest="headers", metavar="ID,Zone,State,PublicIP,PrivateIP,T:Name,T:Role")
    (options, args) = parser.parse_args()
    result, awskeys = zkParser(options.keycfg)
    if not result:
        print "%s is corrupt..." % options.keycfg
        sys.exit(0)
        
    if options.account in awskeys:
        awskey = awskeys[options.account]
    else:
        print "accounts are not found in %s..." % (options.keycfg)
        sys.exit(0)

    # Connect the region
    if options.region not in REGIONS:
        print "Region %s not found." % options.region
        sys.exit(1)

    ec2conn = boto.connect_ec2(region=get_region(REGIONS[options.region]),
							   aws_access_key_id=awskey['aws_access_key_id'],
							   aws_secret_access_key=awskey['aws_secret_access_key'])

    # Read headers
    if options.headers:
        headers = tuple(options.headers.split(','))
    else:
        headers = ("ID", 'Zone', "Groups", "Hostname")

    # Create format string
    format_string = ""
    for h in headers:
        if h.startswith('T:'):
            format_string += "%%-%ds" % HEADERS['T:']['length']
        elif '.filter=' in h:
            format_string += "%%-%ds" % HEADERS[h.split('.filter=')[0]]['length']
        elif '=' in h:
            format_string += "%%-%ds" % HEADERS[h.split('=')[0]]['length']
        else:
            format_string += "%%-%ds" % HEADERS[h]['length']

    # List and print
    print format_string % headers
    print "-" * len(format_string % headers)

    for r in ec2conn.get_all_instances():
        groups = [g.name for g in r.groups]
        for i in r.instances:
            i.groups = ','.join(groups)
            prints = []
            for h in headers:
                key, value = get_column(h, i)
                if value:
                    prints.append(value)
            if len(prints) == len(headers):
                print format_string % tuple(prints)
if __name__ == "__main__":
    main()
