#!/usr/bin/python
import boto3
import json

client = boto3.client('ec2')
instancedata = {"Instances": []}

try:
    response = client.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instancetags = {"InstanceTags": {}}
            securitygroups = {"SecurityGroup": {}}
            instanceid = instance['InstanceId']
            instancetags["InstanceTags"] = instance['Tags']
            combined = {instanceid: {}}
            combined[instanceid] = instancetags
            for securityGroup in instance['SecurityGroups']:
                response = client.describe_security_groups(
                    GroupIds=[
                        securityGroup["GroupId"]
                    ],
                )
                sgname = response['SecurityGroups'][0]['GroupName']
                currentsg = {sgname: {}}
                currentsg[sgname]["SGDesc"] = response['SecurityGroups'][0]['Description']
                currentsg[sgname ]["IPPermissions"] = response['SecurityGroups'][0]['IpPermissions']
                securitygroups["SecurityGroup"].update(currentsg)
                combined[instanceid].update(securitygroups)
        instancedata["Instances"].append(combined)
    print(json.dumps(instancedata, indent=2))

except Exception as E:
    print(E)
