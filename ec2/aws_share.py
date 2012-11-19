#!/usr/local/bin/python

REGIONS = {
        'ue': 'us-east-1',
        'uw1': 'us-weat-1',
	    'uw2': 'us-west-2',
	    'as': 'ap-southeast-1',
		'an': 'ap-northeast-1',
}

All_Roles = ['AdminPortal', 'Alert', 'ForwardProxy', 'LogWriter', 'ProfileCache', 'ScannerDy', 'VpcLdapAuthSync', 'Cacti', 'Monitor', 'Splunk']

import ConfigParser

def zkParser(filePath):
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

import boto
from boto import ec2
from boto.ec2 import image
from boto.ec2 import get_region

def getImages(ec2conn, filters):
	return ec2conn.get_all_images(filters=filters)

def getImageTags(ec2conn, image_id):
	return ec2conn.get_all_tags(filters={'resource-id': image_id, 'resource-type': 'image'})

def setImageTags(ec2conn, image_id, image_tags):
    # print image_id
    imageid = [image_id]
    return ec2conn.create_tags(resource_ids=imageid, tags=image_tags)

def getImagePermissions(image):
    return image.get_launch_permissions()

def setImagePermissions(image, user_ids):
    return image.set_launch_permissions(user_ids=user_ids)


if __name__ == "__main__":
    from optparse import OptionParser
    import sys

    parser = OptionParser()
    parser.add_option("-c", "--config", help="Boto configuration (default: /etc/mboto.cfg)", dest="keycfg", default="/etc/mboto.cfg")
    parser.add_option("-f", "--first-account", help="The first account from boto config", dest="first_account")
    parser.add_option("-s", "--second-account", help="The second account from boto config", dest="second_account")
    parser.add_option("--region", help="Region: ue, uw2, as, etc. (default: ue)", dest="region", default="ue")
    parser.add_option("-b", "--build", help="Specify a number on ICS build", dest="build")
    parser.add_option("-r", "--role", help="Specify a role in ICS build", dest="role")
    (options, args) = parser.parse_args()
    result, awskeys = zkParser(options.keycfg)
    if not result:
        print "%s is corrupt..." % options.keycfg
        sys.exit(0)
        
    if options.first_account and options.second_account and options.first_account in awskeys and options.second_account in awskeys:
        first_awskey = awskeys[options.first_account]
        second_awskey = awskeys[options.second_account]
    else:
        print "accounts are not found in %s..." % (options.keycfg)
        sys.exit(0)

    if options.region not in REGIONS:
        print "this region %s is not valid..." % (options.region)
        sys.exit(0)
		
    if not options.build or not options.role:
        print "no build or role specified..."
        sys.exit(0)

    awskey = first_awskey
    print awskey
    ec2conn = boto.connect_ec2(region=get_region(REGIONS[options.region]),
							   aws_access_key_id=awskey['aws_access_key_id'],
							   aws_secret_access_key=awskey['aws_secret_access_key'])

    image_filters={'tag:Role':options.role,'tag:Version':options.build}
    ec2images = getImages(ec2conn, image_filters)
    # print ec2images
    if len(ec2images) != 1:
        print "Too many/no roles are found in the image under Role %s and Version %s" % (options.role, options.build)
        sys.exit(0)

    image_id = ec2images[0].id
    print "Image ID: %s" % image_id

    ec2tags = getImageTags(ec2conn, image_id)

    tags = {}
    for tag in ec2tags:
		tags[tag.name] = tag.value

    print tags
    permits = getImagePermissions(ec2images[0])
    #print permits
    if "user_ids" in permits:
        permits = permits["user_ids"]
    else:
        permits = []
    #print permits
    permits.append(second_awskey["account_number"])
    #print permits
    setImagePermissions(ec2images[0], permits)
    permits = getImagePermissions(ec2images[0])
    #print permits

    ec2conn.close()

    awskey = second_awskey
    print awskey
    ec2conn = boto.connect_ec2(region=get_region(REGIONS[options.region]),
							   aws_access_key_id=awskey['aws_access_key_id'],
							   aws_secret_access_key=awskey['aws_secret_access_key'])

    # print ec2conn
    #print image_id
    ec2tags = getImageTags(ec2conn, image_id)
    tags_old = {}
    for tag in ec2tags:
		tags_old[tag.name] = tag.value
    print tags_old
    setImageTags(ec2conn, image_id, tags)
    ec2tags = getImageTags(ec2conn, image_id)
    tags_new = {}
    for tag in ec2tags:
		tags_new[tag.name] = tag.value
    print tags_new

    ec2conn.close()
