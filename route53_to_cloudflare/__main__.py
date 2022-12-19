#!/usr/bin/env python3

## TODO jinja templates to spesific folders
## TODO set modules for renders and set records

import argparse
from threading import activeCount
import jinja2
import re
import boto3
import logging
import os
from .mod.MX import set_MX_value
from .mod.TXT import fix_TXT_Value, set_TXT_value

globals
ENV = jinja2.Environment(loader=jinja2.PackageLoader(
    'route53_to_cloudflare', 'templates'))

# used to count records that were created
resources = {
    'A': {},
    'AAAA': {},
    'CNAME': {},
    'MX': {},
    'NS': {},
    'SPF': {},
    'SRV': {},
    'TXT': {},
}

def checkIfFolderExists(folderPath):
    try:
        # check if folder exists
        if not os.path.exists(f'{folderPath}'):
            os.mkdir(f'{folderPath}')
        logging.info(f"Created new folder: {folderPath}")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to create new folder: {folderPath}")
        exit()

def set_ZoneName(zone):
    # set zone name
    zoneName=zone['Name'].replace('.', '_')
    # slice the last '_' from the folder name
    if zoneName.endswith('_'):
        zoneName=zoneName[0:-1]
    return zoneName

def set_ResourceName(record):
    """sets the name of the resources in
    for example resources['A'][the name of the resource]"""
    if record['Name'].endswith('.'):
        name = record['Name'][0:-1].replace('.', '_')
    else:
        name = record['Name'].replace('.', '_')
    if re.match(pattern=r'^\d', string=name):
        name = '_{}'.format(name)
    if name.startswith('\\052'):
        name = name.replace('\\052', 'star')
    return name

# sets the of the name of the record
# removing the . at the end of the name
# changeing boto3 output of \052 back to star
# if subDomain - get only the subDomain name - remove the xxx.com from the name
def set_RecordName(name):
    if name.startswith('\\052'):
        recordName = name.replace('\\052', '*')
    else:
        recordName = name
        
    if recordName.endswith('.'):
        recordName = recordName[0:-1]

    # if 2 means that it must be the parrent zone so we dont need any change
    # else means we have more than 1 subdomain so we will add the subdomains name for example test.tikal.updater.com ->
    # the name of the record will be test.tikal -> we will strip the last 2 names
    if len(recordName.split('.')) != 2:
        subDomainRecordName = ""
        for i in range(0, len(recordName.split('.'))-2):
            subDomainRecordName = subDomainRecordName +"."+ recordName.split('.')[i]
        # set records name after the loop
        recordName = subDomainRecordName[1:]
    return recordName

def removeDotFromEnd(value):
    """Remove trailing . for values"""
    if value.endswith('.'):
        value=value[0:-1]
    return value


def render_single_value_records(recordType, zoneName, recordName, ttl, value, resource, aws_account_id,):        
    try:
        template = ENV.get_template(f'{recordType}.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/{recordType}.tf', 'a') as target:
            target.write(template.render(name=recordName, ttl=ttl, value=value, 
            terrafromResource=resource, zone_id=zoneName))
        logging.info(f"Added {recordType} record name: {recordName} to {recordType}.tf")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write {recordType} record name: {recordName} to file: {recordType}.tf")
        exit()

def render_MX_records(recordType, zoneName, recordName, ttl, resource, aws_account_id,
    value1, praiority1, value2="", praiority2="", value3="", praiority3="", 
    value4="", praiority4="", value5="", praiority5=""):

    try:
        template = ENV.get_template(f'{recordType}.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/MX.tf', 'a') as target:
            target.write(template.render(name=recordName, ttl=ttl, 
                    value1=value1, priority1=praiority1, 
                    value2=value2, priority2=praiority2,
                    value3=value3, priority3=praiority3,
                    value4=value4, priority4=praiority4,
                    value5=value5, priority5=praiority5,
                    terrafromResource=resource, zone_id=zoneName)) 
        logging.info(f"Added {recordType} record name: {recordName} to {recordType}.tf")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write {recordType} record name: {recordName} to file: {recordType}.tf")
        exit()

def render_NS_records(recordType, zoneName, recordName, ttl, resource, aws_account_id, 
    value1, value2="", value3="", value4=""):

    try:
        template = ENV.get_template(f'{recordType}.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/NS.tf', 'a') as target:
            target.write(template.render(name=recordName, ttl=ttl, 
            value1=value1, value2=value2, value3=value3,
            value4=value4,
            terrafromResource=resource, zone_id=zoneName)) 
        logging.info(f"Added {recordType} record name: {recordName} to {recordType}.tf")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write {recordType} record name: {recordName} to file: {recordType}.tf")
        exit()

def render_TXT_records(recordType, zoneName, recordName, ttl, resource, aws_account_id,
    value1, value2="", value3="", 
    value4="", value5="", value6="", 
    value7="", value8="", value9="", 
    value10=""):

    try:
        template = ENV.get_template(f'{recordType}.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/TXT.tf', 'a') as target:
            target.write(template.render(name=recordName, ttl=ttl, 
            value1=value1, value2=value2, value3=value3,
            value4=value4, value5=value5, value6=value6,
            value7=value7, value8=value8, value9=value9,
            value10=value10,
            terrafromResource=resource, zone_id=zoneName))
        logging.info(f"Added {recordType} record name: {recordName} to {recordType}.tf")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write {recordType} record name: {recordName} to file: {recordType}.tf")
        exit()

def set_ResourceAndRecordName(record):
    resource = set_ResourceName(record)
    recordName = set_RecordName(record['Name'])
    return resource, recordName

# addes resources to resources to the recordType list
def a_aaa_cname(zoneName, record, aws_account_id):
    recordType = record['Type']
    # check if A or AAAA record
    if recordType == 'A' or recordType == 'AAAA':
        resource, recordName = set_ResourceAndRecordName(record)
        if 'ResourceRecords' in record:
            # add to A record dictinary
            resources[recordType][resource] = { 'name': recordName }
            # render to A.tf
            render_single_value_records(recordType, zoneName, recordName, 1, 
                removeDotFromEnd(record['ResourceRecords'][0]['Value']), resource, aws_account_id)
        elif 'AliasTarget' in record:
            # add to CNAME record dictinary
            resources['CNAME'][resource] = { 'name': recordName }
            # render to CNAME.tf
            render_single_value_records("CNAME", zoneName, recordName, 1,
                removeDotFromEnd(record['AliasTarget']['DNSName']), resource, aws_account_id)
        return True
    # check if CNAME record
    elif recordType == 'CNAME':
        resource, recordName = set_ResourceAndRecordName(record)
        # add to CNAME record dictinary
        resources['CNAME'][resource] = { 'name': recordName }
        if 'ResourceRecords' in  record:
            render_single_value_records("CNAME", zoneName, recordName, 1,
                removeDotFromEnd(record['ResourceRecords'][0]['Value']), resource, aws_account_id)
        elif 'AliasTarget' in record:
            render_single_value_records("CNAME", zoneName, recordName, 1,
                removeDotFromEnd(record['AliasTarget']['DNSName']), resource, aws_account_id)
        return True

    return False

# addes resources to resources['MX']
def mx(zoneName, record, aws_account_id):
    if record['Type'] == 'MX':
        resource, recordName = set_ResourceAndRecordName(record)
        resources['MX'][resource] = { 'name': recordName }
        # set priority and value
        setPV, setPV2, setPV3, setPV4, setPV5 = set_MX_value(record['ResourceRecords'])

        if (len(record['ResourceRecords'])) == 1:
            render_MX_records("MX", zoneName, recordName, 1, resource, aws_account_id,
                removeDotFromEnd(setPV[1]), setPV[0])

        elif (len(record['ResourceRecords'])) == 2:
            render_MX_records("MX2", zoneName, recordName, 1, resource, aws_account_id,
                removeDotFromEnd(setPV[1]), setPV[0],
                removeDotFromEnd(setPV2[1]), setPV2[0])

        elif (len(record['ResourceRecords'])) == 3:
            render_MX_records("MX3", zoneName, recordName, 1, resource, aws_account_id,
                removeDotFromEnd(setPV[1]), setPV[0],
                removeDotFromEnd(setPV2[1]), setPV2[0],
                removeDotFromEnd(setPV3[1]), setPV3[0])

        elif (len(record['ResourceRecords'])) == 4:
            render_MX_records("MX4", zoneName, recordName, 1, resource, aws_account_id,
                removeDotFromEnd(setPV[1]), setPV[0],
                removeDotFromEnd(setPV2[1]), setPV2[0],
                removeDotFromEnd(setPV3[1]), setPV3[0],
                removeDotFromEnd(setPV4[1]), setPV4[0])

        elif (len(record['ResourceRecords'])) == 5:
            render_MX_records("MX5", zoneName, recordName, 1, resource, aws_account_id,
                removeDotFromEnd(setPV[1]), setPV[0],
                removeDotFromEnd(setPV2[1]), setPV2[0],
                removeDotFromEnd(setPV3[1]), setPV3[0],
                removeDotFromEnd(setPV4[1]), setPV4[0],
                removeDotFromEnd(setPV5[1]), setPV5[0])
        return True
    return False

# adds resources to resources['TXT']
def txt(zoneName, record, aws_account_id):
    if record['Type'] == 'TXT':
        resource, recordName = set_ResourceAndRecordName(record)
        resources['TXT'][resource] = { 'name': recordName }
        # set TXT value
        value1, value2, value3, value4, value5, value6,value7, value8, value9, value10 = set_TXT_value(record['ResourceRecords'])

        if (len(record['ResourceRecords'])) == 1:
            render_TXT_records("TXT", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1)
        elif (len(record['ResourceRecords'])) == 2:
            render_TXT_records("TXT2", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2)
        elif (len(record['ResourceRecords'])) == 3:
            render_TXT_records("TXT3", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3)
        elif (len(record['ResourceRecords'])) == 4:
            render_TXT_records("TXT4", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4)
        elif (len(record['ResourceRecords'])) == 5:
            render_TXT_records("TXT5", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5)
        elif (len(record['ResourceRecords'])) == 6:
            render_TXT_records("TXT6", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6)
        elif (len(record['ResourceRecords'])) == 7:
            render_TXT_records("TXT7", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6,
                value7=value7)
        elif (len(record['ResourceRecords'])) == 8:
            render_TXT_records("TXT8", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6,
                value7=value7, value8=value8)
        elif (len(record['ResourceRecords'])) == 9:
            render_TXT_records("TXT9", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6,
                value7=value7, value8=value8, value9=value9)
        elif (len(record['ResourceRecords'])) == 10:
            render_TXT_records("TXT10", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6,
                value7=value7, value8=value8, value9=value9,
                value10=value10)
        elif (len(record['ResourceRecords'])) > 10:
            render_TXT_records("TXT10", zoneName, recordName, 1, resource, aws_account_id,
                value1=value1, value2=value2, value3=value3,
                value4=value4, value5=value5, value6=value6,
                value7=value7, value8=value8, value9=value9,
                value10="##TODO_MORE_THAN_10_VALUES")
        return True
    return False

# addes resources to resources['NS']
def ns(zoneName, record, aws_account_id):
    if record['Type'] == 'NS':
        resource, recordName = set_ResourceAndRecordName(record)
        resources['NS'][resource] = { 'name': recordName }
      # check the number of values in the ns record

        if (len(record['ResourceRecords'])) == 1:
            resources['NS'][resource] = {'name': recordName}
            render_NS_records("NS", zoneName, recordName, 1, resource, aws_account_id,
                value1=removeDotFromEnd(record['ResourceRecords'][0]['Value']))
        elif (len(record['ResourceRecords'])) == 2:
            resources['NS'][resource] = {'name': recordName}
            render_NS_records("NS2", zoneName, recordName, 1, resource, aws_account_id,
                value1=removeDotFromEnd(record['ResourceRecords'][0]['Value']), 
                value2=removeDotFromEnd(record['ResourceRecords'][1]['Value']))
        elif (len(record['ResourceRecords'])) == 3:
            resources['NS'][resource] = {'name': recordName}
            render_NS_records("NS3", zoneName, recordName, 1, resource, aws_account_id,
                value1=removeDotFromEnd(record['ResourceRecords'][0]['Value']), 
                value2=removeDotFromEnd(record['ResourceRecords'][1]['Value']), 
                value3=removeDotFromEnd(record['ResourceRecords'][2]['Value']))
        elif (len(record['ResourceRecords'])) == 4:
            resources['NS'][resource] = {'name': recordName}
            render_NS_records("NS3", zoneName, recordName, 1, resource, aws_account_id,
                value1=removeDotFromEnd(record['ResourceRecords'][0]['Value']), 
                value2=removeDotFromEnd(record['ResourceRecords'][1]['Value']), 
                value3=removeDotFromEnd(record['ResourceRecords'][2]['Value']),
                value4=removeDotFromEnd(record['ResourceRecords'][3]['Value']))
        return True
    return False

# addes resources to resources['SPF']
def spf(zoneName, record, aws_account_id):
    if record['Type'] == 'SPF':
        # fix replace '"' with ''  and fix DKIM value
        value = fix_TXT_Value(record['ResourceRecords'][0]['Value'])
        resource, recordName = set_ResourceAndRecordName(record)
        resources['SPF'][resource] = { 'name': recordName }  
        # render spf record
        render_single_value_records("SPF", zoneName, recordName, 1, value, resource, aws_account_id)
        return True
    return False

# input parametes for script
def parse_arguments():
    """
    Function to handle argument parser configuration (argument definitions, default values and so on).
    :return: :obj:`argparse.ArgumentParser` object with set of configured arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-id',
        '--account_id',
        help='cloudlfare account id',
        default=str(),
        required=True,
        type=str
    )
    parser.add_argument(
        '-ns',
        '--cloudflare_ns_record',
        help='cloudlfare ns record, required for nslookup testing. Example Record: "guy.ns.cloudflare.com"',
        default=str(),
        required=True,
        type=str
    )
    parser.add_argument(
        '-awsID',
        '--aws_account_id',
        help='aws account id',
        default=str(),
        required=True,
        type=str
    )
    return parser

# parsing through the records
def parse_zone(zone, rs, aws_account_id):
    for record in rs['ResourceRecordSets']:
        # if not comment(record=record):
        if a_aaa_cname(set_ZoneName(zone), record, aws_account_id):
            continue
        if mx(set_ZoneName(zone), record, aws_account_id):
            continue
        if txt(set_ZoneName(zone), record, aws_account_id):
            continue
        if spf(set_ZoneName(zone), record, aws_account_id):
            continue
        # exclude NS records of the parent zone
        if record['Name'] != zone['Name'] and ns(set_ZoneName(zone), record, aws_account_id):
            continue

# render main.tf
def renderMain_TF(zoneName, account_id, aws_account_id):
    try:
    # main.tf
        template = ENV.get_template('main.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/main.tf', 'w') as target:
            target.write(template.render(account_id=account_id, zoneName=zoneName))
        logging.info(f"Rendered main.tf for zone {zoneName}")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write main.tf for zone {zoneName}")
        exit()

# render zone.tf
def renderZone_TF(zoneName, aws_account_id):
    try:
        # Zone.tf
        # cloudflare_zone_name=zoneName - replacing the _ with .
        template = ENV.get_template('zone.tf.j2')
        with open(f'./{aws_account_id}/{zoneName}/zone.tf', 'w') as target:
            target.write(template.render(terrafromResource=zoneName, cloudflare_zone_name=zoneName.replace('_', '.')))
        logging.info(f"Rendered zone.tf for zone {zoneName}")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write zone.tf for zone {zoneName}")
        exit()

# render validate file countRecords.txt
def renderValidationFileCountRecords(rs, zoneName, aws_account_id):

    # get the number of each record type that was added to the TF files
    recordA         = len(resources['A'])
    recordAAAA      = len(resources['AAAA'])
    recordCANME     = len(resources['CNAME'])
    recordMX        = len(resources['MX'])
    recordSRV       = len(resources['SRV'])
    recordTXT       = len(resources['TXT'])
    recordNS        = len(resources['NS'])
    recordSPF       = len(resources['SPF'])

    # get the number of records from the hosted zone
    recordsCreated  = recordA + recordAAAA + recordCANME + recordMX + recordSRV + recordTXT + recordNS + recordSPF
    awsArecord      = 0
    awsAAAArecord   = 0
    awsMXrecord     = 0
    awsTXTrecord    = 0
    awsCNAMErecord  = 0
    awsSRVrecord    = 0
    awsNSrecord     = 0
    awsSPFrecord    = 0
    for i in rs['ResourceRecordSets']:
        if i['Type'] == 'A':
            awsArecord += 1
        elif i['Type'] == 'NS':
            awsNSrecord += 1
        elif i['Type'] == 'AAAA':
            awsAAAArecord += 1
        elif i['Type'] == 'MX':
            awsMXrecord += 1
        elif i['Type'] == 'TXT':
            awsTXTrecord += 1
        elif i['Type'] == 'CNAME':
            awsCNAMErecord += 1
        elif i['Type'] == 'SRV':
            awsSRVrecord += 1
        elif i['Type'] == 'SPF':
            awsSPFrecord += 1

    # render count records file
    try:
        template = ENV.get_template('countRecords.txt.j2')
        with open(f'./{aws_account_id}/{zoneName}/countRecords.txt', 'w') as target:
            target.write(template.render(recordsCreated=recordsCreated, recordA=recordA, recordAAAA=recordAAAA,
            recordCANME=recordCANME, recordMX=recordMX, recordSRV=recordSRV, recordTXT=recordTXT,
            recordNS=recordNS, awsArecord=awsArecord, awsAAAArecord=awsAAAArecord, awsMXrecord=awsMXrecord,
            awsTXTrecord=awsTXTrecord, awsCNAMErecord=awsCNAMErecord, awsSRVrecord=awsSRVrecord, awsNSrecord=awsNSrecord,
            awsSPFrecord=awsSPFrecord, recordSPF=recordSPF, rs=(len(rs['ResourceRecordSets']))))
        logging.info(f"Rendered countRecords.txt for zone {zoneName}")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write countRecords.txt for zone {zoneName}")
        exit()

# render subzones files
def renderSubZoneFiles(zoneName, aws_account_id):
    recordNS        = len(resources['NS'])
    try:
        # 0 subzones
        if recordNS == 0 and len(zoneName.split('_')) == 2:
            with open(f'./{aws_account_id}/{aws_account_id}_noSubZones.txt', 'a') as target:
                target.write(zoneName.replace('_', '.') + "\n")
        logging.info(f"Added zone {zoneName} to 0 sub domains file: ./{aws_account_id}/{aws_account_id}_noSubZones.txt")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write noSubZones.txt for zone {zoneName}")
        exit()

    try:
        # zones With Sub Domains
        if recordNS == 0 and len(zoneName.split('_')) != 2:
            with open(f'./{aws_account_id}/{aws_account_id}_zonesWithSubDomains.txt', 'a') as target:
                target.write(zoneName.replace('_', '.') + "\n")
        logging.info(f"Added zone {zoneName} to 0 sub domains file: ./{aws_account_id}/{aws_account_id}_zonesWithSubDomains.txt")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to write zonesWithSubDomains.txt for zone {zoneName}")
        exit()

# render validation scripts
def renderValidationScripts(zone, zoneName, cloudflare_ns_record, aws_account_id):
    # nslookup
    for recordType in resources:
        # create file only for the necessary records
        if not len(resources[recordType]) == 0:

            parentDomain=zoneName.replace('_', '.')
            #set parent domain name if subDomain has seperated Subzone
            if int(len(zoneName.split("_"))) > 2:
                parentDomainName = ""
                for i in range(len(zoneName.split('_'))-2, len(zoneName.split('_'))):
                    parentDomainName = parentDomainName +"."+ zoneName.split('_')[i]
                    # remove the '.' from the start of the parent domain name
                    parentDomain = parentDomainName[1:].replace('_', '.')

            try:
                template = ENV.get_template(f'nslookup{recordType}.sh.j2')
                with open(f"./{aws_account_id}/{zoneName}/validateRecords/nslookup{recordType}.sh", 'a') as target:
                    target.write(template.render(resources=resources[recordType], parentDomain=parentDomain,
                    cloudflare_ns_record=cloudflare_ns_record, space=" "))
                logging.info(f"Created file nslookup{recordType}.sh for zone: {zoneName} ")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to write nslookup{recordType}.sh for zone: {zoneName}")
                exit()

            try:
                # Read in the file
                with open(f"./{aws_account_id}/{zoneName}/validateRecords/nslookup{recordType}.sh", 'r') as file :
                    filedata = file.read()
                # Replace the target string
                # replace duplicate parent domain name in nslookup file
                # for example: facebook.com.facebook.com -> facebook.com
                filedata = filedata.replace(f"{zone['Name'][0:-1]}.{zone['Name'][0:-1]}", f"{zone['Name'][0:-1]}")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to read file: {file}")
                exit()

            try:
                # Write the file out again
                with open(f"./{aws_account_id}/{zoneName}/validateRecords/nslookup{recordType}.sh", 'w') as file:
                    file.write(filedata)
                logging.info(f"Added validation script to file nslookup{recordType}.sh for zone: {zoneName} ")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to write nslookup{recordType}.sh for zone: {zoneName}")
                exit()

def main():
    # # Write log to file
    # logging.basicConfig(level=logging.INFO, filename='./app.log', filemode='a', format= '%(asctime)s - %(levelname)s - %(message)s')
    
    # Write log to screen
    logging.basicConfig(level=logging.INFO, format= '%(asctime)s - %(levelname)s - %(message)s')

    try:
        # get input parameters
        args = parse_arguments().parse_args()
        account_id = args.account_id
        cloudflare_ns_record = args.cloudflare_ns_record
        aws_account_id = args.aws_account_id
        logging.info(f"Got input parameters succesfully: account_id {account_id}, cloudflare_ns_record {cloudflare_ns_record}, {aws_account_id}")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to get input parametrs")
        exit()

    # load boto3 route53 client
    try:
        client = boto3.client('route53')
        logging.info(f"Loaded boto route53 client succesfully")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to load boto route53 client")
        exit()

    # get zones list
    try:
        hostedzone=client.list_hosted_zones()
        logging.info(f"Extracted hosted zone list")
    except Exception as e:
        logging.error(f"Error {e}\nWas not able to extract hosted zone list")
        exit()

    checkIfFolderExists(f"./{aws_account_id}")

    for zone in hostedzone["HostedZones"]:
        # filter out private domains
        if not zone["Config"]["PrivateZone"]:
            try:
                # get all the records from the zone
                rs=client.list_resource_record_sets(HostedZoneId=zone["Id"],MaxItems='2000')
                logging.info(f"Extracted list resource record sets for {zone}")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to extract list resource record sets for {zone}")
                exit()


            # set zone name for folder name and resource name
            zoneName = set_ZoneName(zone)

            checkIfFolderExists(f"./{aws_account_id}/{zoneName}")
            checkIfFolderExists(f"./{aws_account_id}/{zoneName}/validateRecords")
            
            # parsing through the records list and write records to 'record_type.tf'
            parse_zone(zone, rs, aws_account_id)

            # render main.tf
            renderMain_TF(zoneName, account_id, aws_account_id)
            # render zone.tf
            renderZone_TF(zoneName, aws_account_id)
            # render validate file countRecords.txt
            renderValidationFileCountRecords(rs, zoneName, aws_account_id)
            # render subzones files
            renderSubZoneFiles(zoneName, aws_account_id)
            # render validation scripts
            renderValidationScripts(zone, zoneName, cloudflare_ns_record, aws_account_id)

            # terraform fmt check
            try:
                os.system(f'cd ./{aws_account_id}/{zoneName} && terraform fmt && cd -')
                logging.info(f"Terraform fmt was successful for zone: {zoneName}")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to run Terraform")
                exit()

            # change premissions:
            try:
                os.system(f'cd ./{aws_account_id}/{zoneName}/validateRecords && chmod +x *.sh && cd -')
                logging.info(f"Added +x permissiosn to validation scripts under: {zoneName}/validateRecords")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to add permissions to validation scripts under: {zoneName}/validateRecords")
                exit()

            # empty resources dict for new zone
            for i in resources:
                resources[i].clear()

        # if it's a private zone - write the filtered zone name to file
        else:
            zoneName = set_ZoneName(zone)
            try:
                with open(f'./{aws_account_id}/{aws_account_id}_PrivateZoneFiltered.txt', 'a') as target:
                    target.write(zoneName.replace('_', '.') + "\n")
                logging.info(f"Found private zone and added it file: ./{aws_account_id}/{aws_account_id}_PrivateZoneFiltered.txt")
            except Exception as e:
                logging.error(f"Error {e}\nWas not able to write private zone to file: ./{aws_account_id}/{aws_account_id}_PrivateZoneFiltered.txt")
                exit()

if __name__ == '__main__':
    main()
