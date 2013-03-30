#!/usr/local/bin/python

REGIONS = {
        'ue': 'us-east-1',
        'uw1': 'us-weat-1',
	'uw2': 'us-west-2',
	'as': 'ap-southeast-1',
	'as2': 'ap-southeast-2',
	'an': 'ap-northeast-1',
}
ICS_ROLES = ["AdminPortal",
        "Alert",
        "ForwardProxy",
        "LogWriter",
        "Misc",
        "Monitor",
        "ProfileCache",
        "ScannerDy",
        # Note: ScannerSt's AMI = ScannerDy's AMI
        # "ScannerSt",
        "Splunk",
        "VpcLdapAuthSync"]

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

    regions = []
    if not options.region:
        print "no region specified..."
    
    if options.region.lower() == "all":
        regions = REGIONS.keys()
    else:
        for region in options.region.split(","):
            if region not in REGIONS:
                print "this region %s is not valid..." % (region)
                sys.exit(0)
            regions.append(region)
        
    roles = []
    if not options.role:
        print "no role specified..."

    if options.role.lower() == "all":
        roles = ICS_ROLES
    else:
        for role in options.role.split(","):
            if role not in ICS_ROLES:
                print "this role %s is not valid..." % (role)
                sys.exit(0)
            roles.append(role)
		
    if not options.build:
        print "no build specified..."
        sys.exit(0)

    skipped = {}

    for region in regions:
        print "----------------------------------------------------------"
        print "===> Region:\t", region
        print "----------------------------------------------------------"
        skipped[region] = []
        for role in roles: 
            print "====> Role:\t", role 
            awskey = first_awskey
            print "=====> Switch to first account:", options.first_account, awskey["account_number"]
            ec2conn = boto.connect_ec2(region=get_region(REGIONS[region]),
    							   aws_access_key_id=awskey['aws_access_key_id'],
    							   aws_secret_access_key=awskey['aws_secret_access_key'])
            image_filters={'tag:Role':role,'tag:Version':options.build}
            ec2images = getImages(ec2conn, image_filters)
            # print ec2images
            if len(ec2images) != 1:
                skipped[region].append(role)
                print "++++++ Error found but skipped : Too many/no such role in the image tags\n"
                continue
                #sys.exit(0)
        
            image_id = ec2images[0].id
            print "=====> Image ID: %s" % image_id
        
            ec2tags = getImageTags(ec2conn, image_id)
        
            tags = {}
            for tag in ec2tags:
        		tags[tag.name] = tag.value
        
            print "=====> AMI Tags: ", tags
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
        
            print "=====> Share AMI now...."
            awskey = second_awskey
            print "=====> Switch to second account:", options.second_account, awskey["account_number"]
            ec2conn = boto.connect_ec2(region=get_region(REGIONS[region]),
        							   aws_access_key_id=awskey['aws_access_key_id'],
        							   aws_secret_access_key=awskey['aws_secret_access_key'])
        
            #print image_id
            ec2tags = getImageTags(ec2conn, image_id)
            tags_old = {}
            for tag in ec2tags:
        		tags_old[tag.name] = tag.value
            #print tags_old
            setImageTags(ec2conn, image_id, tags)
            ec2tags = getImageTags(ec2conn, image_id)
            tags_new = {}
            for tag in ec2tags:
        		tags_new[tag.name] = tag.value
            print "=====> New AMI Tags:\t", tags_new
            print "++++++ Done ++++++\n"
        
            ec2conn.close()
    
    print "-----------------------------------------"
    print "|            Final Result               |"
    print "-----------------------------------------"

    flag = 0
    for region in regions:
        if len(skipped[region]) > 0:
            print "---> Region: \t", region
            print "----> Failed Roles: \t", skipped[region]
            flag = 1
    if flag == 1:
        print "\n"
    else:
        print "Successfuly finished...\n"
