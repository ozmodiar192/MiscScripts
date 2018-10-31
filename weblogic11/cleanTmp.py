
import sys
from java.util import Properties
from java.io import FileInputStream
from java.io import File
import time as pytime
import threading
import re
import os
import commands 
# Path Variables
domain_name='mydomain'
java_home='/path/to/jdk'
middleware_home='/path/to/weblogic'
weblogic_home='/path/to/weblogic/wlserver'
domain_home='/path/to/weblogic/domain/'
node_manager_home='/path/to/weblogic/oracle_common/common/nodemanager'
weblogic_template=weblogic_home + '/common/templates/wls/wls.jar'
admin_server_url = 't3://127.0.0.1:9913'
# Assumes you've used STOREUSERCONFIG to generate these.  If you haven't, modify your connect() string to use un/pw
user_file = "/path/to/wladmin_user.secure"
key_file = "/path/to/wladmin_key.secure"

# Script Variables
targetExp = sys.argv[1]
targetDict = {}
targetList = []
runningServers = []
serverNameList = []
machineNameList = []
clusterNameList = []
svrObjList = []
machObjList = []
clustObjList = []
isCluster = False

def usage():
  usageString=""" 
  **************************************************************************************************************************************************************************************************************
  *   Cleans remote weblogic tmp and cache directories
  *   USAGE:
  *            ${WEBLOGIC_HOME}/oracle_common/common/bin/wlst.sh  ${WLCTL_PATH}/cleanTmp.py <target expression>
  *   Target expressions:
  *          Machine name = This targets all weblogic managed servers on a single machine.  This should be the machine name from the Weblogic console, which is usually the same as the hostname of the server.
  *          Managed server name = This targets a single managed server, e.g, prod_store01.
  *          Managed server wildcard expression = Matches managed servers based on a wildcard.  prod* matches prod_store01, prod_bcc01, etc.  Prod_store* matches all prod_store servers.
  ******************************************************************************************************************************************************************************************************************
"""
  print(usageString)

# Get a list of all the server objects
def genSvrObjList():
  svrObjList = cmo.getServers()
  return svrObjList

# Get a list of all the machine objects
def genMachObjList():
  machObjList = cmo.getMachines()
  return machObjList

# Get a list of all the cluster objects
def genClustObjList():
  clustObjList = cmo.getClusters()
  return clustObjList

# From the list of server objects, generate a list of the names of each server
def genServerList(svrObjList):
  for server in svrObjList:
    currentServer=server.getName()
    serverNameList.append(currentServer)
  return serverNameList

# From the list of machine objects, generate a list of the names of each machine
def genMachineList(machObjList):
  machineNames = cmo.getMachines()
  for machine in machineNames:
    currentMach=machine.getName()
    machineNameList.append(currentMach)
  return machineNameList

# From the list of server objects, generate a list of the names of each cluster
def genClusterList(clustObjList):
  for cluster in clustObjList:
    currentClust=cluster.getName()
    clusterNameList.append(currentClust)
  return clusterNameList

#Checks if the target is a cluster
def checkIsCluster(target,clusterNameList):
  if target in clusterNameList:
    # We're going to set a global variable so the whole script knows we're dealing with a cluster here.
    isCluster = True
  else:
    isCluster = False
  return isCluster

#Determine the targets based on the argument
def findTargets(target,serverNameList,machineNameList):
  # look for commas in the target expression.  If they're there, we've got a list.
  if "," in target:
    print("You provided a list of servers")
    targList = target.split(',')
    for targ in targList:
      if targ in serverNameList:
        print(targ + " is a valid target")
        targetList.append(targ)
      else:
        print("\nWARNING! You tried to target " + targ + ", but that's not a valid managed server!\nSkipping " + targ + "\n")
  # Look for the target in the list of machines
  for currentMachine in machineNameList:
    #Look for explicit matches
    if target == currentMachine:
      print(target + ' is an explicitly set machine')
      # We've found the machine, now we iterate through the servers and try to cd into the machine we're interested in.  If we're unable to, machCheck will be none and we'll skip it.  Otherwise we'll add it to our list of targgts.
      addByMachine(serverNameList,currentMachine)
  # We couldn't find any machines that match what the user gave us, so we'll check if it's a managed server.
  if target in serverNameList:
    print(target  + ' is an explicitly set managed server')
    targetList.append(target)
    # The target the user passed in wasn't a managed server.  We'll check for *'s to see if they wanted to use a wildcard.  If they did, we'll convert it to an ugly regex and search for it.
  if re.search(".*[*].*",target) is not None:
    sanitizedTarget=target.replace("*",".*")
    # Now we need to append start and end of line characters to the ugly regex so prod* doesn't match, but *prod* does.
    sanitizedTarget="^"+sanitizedTarget+"$"
    for currentServer in serverNameList:
      if re.search(sanitizedTarget,currentServer) is not None:
        print(target + ' is a wildcard match that matches ' + currentServer + '.')
        if currentServer != 'AdminServer':
          targetList.append(currentServer)
        else:
          print("Skipping AdminServer")
# Return a list of intersting servers.
  return targetList

def addByCluster(svrObjList,target):
  print("You specified a cluster")
#Iterate through the server object list
  for server in svrObjList:
  # Check if the server is in a cluster, and the cluster is named the same as the target.  If so, add it to the targetlist.
    if server.getCluster() != None and server.getCluster().getName() == target:
      print("Found server " + server.getName() + " in cluster " + target)
      targetList.append(server.getName())
  return targetList

def addByMachine(serverNameList,machine):
  print("Checking for servers on " + machine + ".  Please ignore stack trace messages")
  for currentServer in serverNameList:
    if currentServer != 'AdminServer':
      machCheck = getMBean('/Servers/'+currentServer+'/Machine/'+machine)
      if machCheck != None:
        print('Appending ' + currentServer + ' to your list of targets')
        targetList.append(currentServer)
  return targetList

# This function takes a list of servers and all the machine objects, and builds a diction with the keys being the nodemanager name, and the values being the managed servers that live on them.
def buildDictByServerList(targetServers,machineNameList):
  print("Searching for targets, please ignore any Stacktrace messages")
  targetDict = {}
  for machine in machineNameList:
    for server in targetServers:
      machCheck = getMBean('/Servers/'+server+'/Machine/'+machine)
      if machCheck != None:
        if machine in targetDict:
          targetDict[machine].append(server)
        else:
          targetDict[machine]=[server]
  return targetDict

# get Server status
def getMSserverStatus(server):
  for attempt in range(2):
    try:
      cd('/ServerLifeCycleRuntimes/' + server)
      serverState=cmo.getState()
    except:
      print('error for ' + server)
      pytime.sleep(5)
      continue
    else:
      break
  return serverState

def genStateDict(targetList):
  stateDict = {}
  for target in targetList:
    targStatus=getMSserverStatus(target)
    stateDict[target]=targStatus
  return stateDict
                    
# disconnect from  adminserver
def disconnectFromAdminServer():
  print 'Disconnect from the Admin Server...';
  disconnect();

def connectToAdminServer(user,key,url):
  print 'Connecting to Admin'
  connect(userConfigFile=user,userKeyFile=key,url=url)

def deleteTmpDirs(user,machine,mserver):
  sshstring = 'ssh ' + user + '@' + machine + " \"rm -rf " + domain_home + "/servers/" + mserver + "/cache && rm -rf " + domain_home + "/servers/" + mserver + "/tmp\""
  print('trying to ' + sshstring)
  sshcmd = os.popen(sshstring)
  out = sshcmd.read()
  print(out)
 
 
# ================================================================
#           Main Code Execution
# ================================================================
if len(sys.argv) != 2:
  usage()
  sys.exit("Invalid arguments, please specify a target expression")
# connect to the admin server
connectToAdminServer(user_file,key_file,admin_server_url)
# Must be in domain confing to view domain configuration
domainConfig()
# Generate a bunch of lists about the configuration up front.
svrObjList = genSvrObjList()
machObjList = genMachObjList()
clustObjList = genClustObjList()
serverNameList = genServerList(svrObjList)
machineNameList = genMachineList(machObjList)
clusterNameList = genClusterList(clustObjList)
# Check if we're dealing with a cluster
isCluster = checkIsCluster(targetExp,clusterNameList)
if not isCluster:
  targetList = findTargets(targetExp,serverNameList,machineNameList)
else:
  targetList = addByCluster(svrObjList,targetExp)
print("Taking action on " + str(targetList))
targetDict = buildDictByServerList(targetList,machineNameList)
domainRuntime()
currentState = genStateDict(targetList)
for k,v in currentState.iteritems():
  if (v == "RUNNING" or v == "ADMIN"):
    runningServers.append(k)
domainConfig()
#if len(targetDict) < 1:
#  usage()
#  sys.exit("ERROR! Could not find any servers based on your target expression!")
for k,values in targetDict.iteritems():
  for v in values:
    if v in runningServers:
      print("Refusing to delete temp files on a running server")
    else:
      deleteTmpDirs('ecom',k,v)
disconnectFromAdminServer()
print("Terminating main thread")
