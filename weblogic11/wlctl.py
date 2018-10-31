import sys
from java.util import Properties
from java.io import FileInputStream
from java.io import File
import time as pytime
import threading
import re
import os

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

# Script variables
target = sys.argv[2]
action = sys.argv[1]
targetList = []
possibleActions = ["start", "stop", "restart", "status"]
svrObjList = []
machObjList = []
clustObjList = []
serverNameList = []
machineNameList = []
clusterNameList = []
isCluster = False

# This class is used for multithreading control commands.  The init class is executed when called and sets up variables.  The run function executes the thread and carries out the action requested by the user.
class controlThread (threading.Thread):
  def __init__(self,mserver,action):
    threading.Thread.__init__(self)
    self.mserver = mserver
    self.action = action
  def run(self):
    print('Starting thread ' + self.getName() + ' to ' + self.action + " " + self.mserver)
    if self.action == "start":
      startManagedServer(self.mserver)
    elif self.action == "stop":
      stopManagedServer(self.mserver)
    elif self.action == "restart":
      stopManagedServer(self.mserver)
      startManagedServer(self.mserver)
    print('Terminating thread ' + self.getName())

def usage():
  usageString=""" 
  **************************************************************************************************************************************************************************************************************
  *   USAGE:
  *            ${WEBLOGIC_HOME}/oracle_common/common/bin/wlst.sh  ${WLCTL_PATH}/wlctl.py stop dev* wlctl.py <action> <target expression>
  *   Actions:
  *          start = start the weblogic managed servers returned by the target expression.  Only starts servers with a state of "SHUTDOWN", "FAILED" or "FAILED_NOT_RESTARTABLE".
  *          stop  = stop the weblogic managed servers returned by the target expression.  Only stops servers with a state of "RUNNING"
  *          restart = stop, then start the weblogic managed servers returned by the target expression.  Only restarts servers with a state of "RUNNING"
  *   Target expressions:
  *          Machine name = This targets all weblogic managed servers on a single machine.  This should be the machine name from the Weblogic console, which is usually the same as the hostname of the server.
  *          Managed server name = This targets a single managed server, e.g, prod_store01.
  *          Managed server wildcard expression = Matches managed servers based on a wildcard.  prod* matches prod_store01, prod_bcc01, etc.  Prod_store* matches all prod_store servers.  If you use *, enter it as \* so the shell doesn't expand it.
  *          Managed server list = Matches managed servers based on an explicit, non-spaced, comma-deliniated list.  i.e, prod_store01,prod_store03,prod_store05 
  *          Cluster = Matches an explicitly set cluster name, like "store_cluster".  Targets every member of the cluster
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
  
# From the list of server objects, generate a list of the names of each server
def genClusterList(clustObjList):
  for cluster in clustObjList:
    currentClust=cluster.getName()
    clusterNameList.append(currentClust)
  return clusterNameList

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

def addByMachine(serverNameList,machine):
  print("Checking for servers on " + machine + ".  Please ignore stack trace messages")
  for currentServer in serverNameList:
    if currentServer != 'AdminServer':
      machCheck = getMBean('/Servers/'+currentServer+'/Machine/'+machine)
      if machCheck != None:
        print('Appending ' + currentServer + ' to your list of targets')
        targetList.append(currentServer)
  return targetList
      
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

# Starts a singleton managed server
def startManagedServer(server):
  try:
    start(server,'Server')
  except:
    print("Failed to start " + server)
    dumpStack()

# Starts a cluster
def startCluster(cluster):
  try:
    print('starting cluster ' + cluster)
    start(cluster,'Cluster')
  except:
    print("Failed to start " + cluster)
    dumpStack()

# Stops a singleton managed server
def stopManagedServer(server):
  try:
    shutdown(server,'Server','true',1000,force='true', block='true')
  except:
    print("Failed to stop server " + server + "!")
    dumpStack()

#Stops a cluster
def stopCluster(cluster):
  try:
    shutdown(cluster,'Cluster')
  except:
    print("Failed to stop cluster " + cluster + "!")
    dumpStack()

# Gets the status of all the managed servers in a cluster.
def statusCluster(cluster):
  try:
    state(cluster,'Cluster')
  except:
    print("Error getting state for cluster " + cluster + "!")
    dumpStack()

#Generates a dictionary of servers and their status based on a given list of managed servers.  Not applicable to clusters.
def genStateDict(targetList):
  for target in targetList:
    targStatus=getMSserverStatus(target)
    stateDict[target]=targStatus
  return stateDict
                    
# disconnect from  adminserver
def disconnectFromAdminServer():
  print 'Disconnect from the Admin Server...';
  disconnect();

#Connects to the admin server
def connectToAdminServer(user,key,url):
  print 'Connecting to Admin'
  connect(userConfigFile=user,userKeyFile=key,url=url)
 
 
# ================================================================
#           Main Code Execution
# ================================================================
if action not in possibleActions:
  usage()
  sys.exit("ERROR! Invalid action specified: " + action)
if len(sys.argv) != 3:
  usage()
  sys.exit("ERROR! Incorrect number of arguments given")
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
isCluster = checkIsCluster(target,clusterNameList)
# If we're dealing with some permutation of managed servers, we need a final list of targets and everything.
if not isCluster:
  findTargets(target,serverNameList,machineNameList)
  if len(targetList) < 1:
    usage()
    sys.exit("ERROR! Could not find any servers based on your target expression!")
  print("\nDone determining targets.  Taking action on the following managed servers:\n" + str(targetList))
  # Create an empty list to use for thread joining, and a dictionary to store the current state.  We have to use the dictionary because switching between domainConfig and domainRuntime in a threaded environment doesn't work right.  That's why we can't get state within the start/stop functions :(.
  threadList=[]
  stateDict={}
  # Enter domainRuntime so we can get the curret status
  domainRuntime()
  # This calls the stateDict function that creates a dictionary of the servers and their current state.
  stateDict=genStateDict(targetList)
  # BACK TO DOMAIN CONFIG!
  domainConfig()
  # Iterate through our state dictionary and take the action when appropriate.  k = servername, v=state.
  for k,v in stateDict.iteritems():
    if ( action == "start" ) and ( v == "SHUTDOWN" or v == "FAILED" or v == "FAILED_NOT_RESTARTABLE" or v == "ADMIN"):
      print("Before " + action + " attempt, " + k + " has a state of " + v)
      ctlThread = controlThread(k,action)
      ctlThread.start()
      threadList.append(ctlThread)
    elif ( action == "stop" ) and ( v == "RUNNING" or v == "ADMIN"):
      print("Before " + action + " attempt, " + k + " has a state of " + v)
      ctlThread = controlThread(k,action)
      ctlThread.start()
      threadList.append(ctlThread)
    elif ( action == "restart" ) and ( v == "RUNNING"):
      print("Before " + action + " attempt, " + k + " has a state of " + v)
      ctlThread = controlThread(k,action)
      ctlThread.start()
      threadList.append(ctlThread)
    elif ( action == "status"):
      pass
    else:
      print("Either I didn't recognize the action \"" + action +"\", or the state of server " + k +":" + v + " is incompatible with the " + action + " action.  Possible actions are: start, stop, restart.")
  # Now we must wait for all the threads to return so we don't pull the connection out from under them.
  for myThread in threadList:
    myThread.join()
  # Back into domainRunTime to get the state of everything now that the command has run.
  domainRuntime()
  stateDict=genStateDict(targetList)
  for k,v in stateDict.iteritems():
    print("After " + action +" attempt, " + k + " has a state of " + v)
  print("\n")
# We're dealing with a cluster so weblogic does all the lifting for us.
else:
  print("You specified a cluster " + target)
  if action == "start":
    startCluster(target)
    statusCluster(target)
  elif action == "stop":
    stopCluster(target)
    statusCluster(target)
  elif action == "restart":
    stopCluster(target)
    startCluster(target)
    statusCluster(target)
  elif action == "status":
    statusCluster(target)
disconnectFromAdminServer()
print("Terminating main thread")
