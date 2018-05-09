import re
from sets import Set

# Variables with dummy values that you should update. I assumed you're using user and key files for authentication.
domain_name='mydomain'
java_home='/path/to/java/home'
middleware_home='/opt/app/weblogic'
weblogic_home='/opt/app/weblogic/wlserver'
domain_home='/opt/app/weblogic/atg/domains/mydomain'
node_manager_home='/opt/app/weblogic/oracle_common/common/nodemanager'
weblogic_template=weblogic_home + '/common/templates/wls/wls.jar'
admin_server_url = 't3://127.0.0.1:9913'
# User must have rights to modify configuration (admin)
user_file = "/path/to/userfile"
key_file = "/path/to/keyfile"
#This list of arguments is for demonstration and testing only, some of these I just made up.  This will break if you use it!
new_arguments = "-Xms8192m -Xmx8g -XX:MaxPermSize=2048m -Dweblogic.diagnostics.DisableDiagnosticRuntimeControlService=true -DSomeargument -Dweblogic.debug.DebugClusterFragments=true -Dweblogic.debug.DebugClusterSomethingElse=true"
    
#This function takes a list of JVM arguments and converts it to a dictionary of key,value pairs with the dict key being the jvm argument name, and the value being a complete copy of the argument broken into key, separator, value
def argdict ( arglist ):
    parsedargdict = {}
    for arg in arglist:
        # Check for args delimited by :.  We do this before = because I've found some args that have multiple trailing ='s and let me tell you, that ain't pretty.
        if ":" in arg:
            #-XX options have trailing colons, so that won't do at all.
            if "-XX" in arg:
                # If it's an XX with an =, we'll split at the =, otherwise we'll just add it with no value and pray like hell that it works.
                if "=" in arg:
                    try:
                        key,value=arg.split("=",1)
                        parsedargdict[key] = (key,'=',value)
                    except:
                        print("\n")
                        print('ERROR! Unable to break up ' + str(arg) + " into key/value pairs.  If you are attempting to modify this value, it likely will be incorrect.")
                        print("\n")
                        parsedargdict[arg] = None
                else:
                    parsedargdict[arg] = None
            # Not an -XX so we can split at : safely. Hopefully. 
            else:
                try:
                    key,value=arg.split(":",1)
                    parsedargdict[key] = (key,':',value)
                except:
                    print("\n")             
                    print('ERROR! Unable to break up ' + str(arg) + " into key/value pairs.  If you are attempting to modify this value, it likely will be incorrect.")
                    print("\n")
                    parsedargdict[arg] = None 
        # Check for args delimited by =
        elif "=" in arg:
            try:
                key,value=arg.split("=",1)
                parsedargdict[key] = (key,'=',value)
            except:
                print("\n")             
                print('ERROR! Unable to break up ' + str(arg) + " into key/value pairs.  If you are attempting to modify this value, it likely will be incorrect.")
                print("\n")
                parsedargdict[arg] = None 
        # Check for args with numeric values but no delimiter like our old pal xmx. Note the sloppy .* after the number part of the regex; that'll grab anything so be careful.
        elif re.match(r"(-[a-z]+)([0-9]+.*)", arg, re.I):
            nondelimited_match = re.match(r"(-[a-z]+)([0-9]+.*)", arg, re.I)
            if nondelimited_match:
                nond_arg=nondelimited_match.groups()
                parsedargdict[nond_arg[0]] = (nond_arg[0],"",nond_arg[1])
        # I'm out of ideas so we'll just add the arg with a key of "none". This will grab flags with no value, like -XX:-DisableExplicitGC.
        else:
            parsedargdict[arg] = None
    return parsedargdict

#this function takes a key value pair and determines if it's got a none value.  Returns the key if the value is none, otherwise joins the values.
def flagchecker ( key,value ):
    if value is None:
        argtouse = key
    else:
        argtouse = ("".join(value))
    print(argtouse)
    return argtouse

#This function takes a string of JVM arguments, compares them to the existing arguments on a server, and returns an updated string containing updated vlues for existing args, unchanged arguments from the existing server, and any new args.
def genargs ( newargs, server ):
    try:
        cd('/Servers/' + server)
        # Get the arguments from Weblogic with this command.
        currentargs = cmo.getServerStart().getArguments()
        # Create a list of new and existing JVM args by splitting the strings.
        newarglist = newargs.split()
        currentarglist = currentargs.split()
        # Create some empty dictionaries for fun.
        finalargs = []
        argstonuke = []
        # push the new and current args into dictionaries
        newargdict = argdict(newarglist)
        currentargdict = argdict(currentarglist)
        # Look through the new args, and check if they're also in the current arguments.  If they are, we know they are existing args with updated values.  We'll  stick them in the final arguments with the updated values from the new args. Follow that?
        for nk,nv in newargdict.iteritems():
            if nk in currentargdict:
                # Check if we have an argument with a key and a value, or just a key.
                newargtoadd = flagchecker(nk,nv)
                finalargs.append(newargtoadd)
                # Pull the current argument out of the current arg dictionary because we're going to wholesale add those later. Should these be pushed to a different dictionary and handled later?  Maybe.
                del currentargdict[nk]
        #Now that we've purged any updated args from the current arguments list, we'll add whatever is left to the final args.  These are unaltered arguments.  Script doesn't support nuking arguments yet.
        for ck,cv in currentargdict.iteritems():
            curargtoadd = flagchecker(ck,cv)
            finalargs.append(curargtoadd)
        # Final args now has any carried over arguments, and the arguments with updated values.  Now we need to add any args that are totally new.  We'll convert finalargs to a dict because I like that function, then look through the new args for any that didn't get added during the check for updated values.
        finalargdict = argdict(finalargs)
        for nk,nv in newargdict.iteritems():
            if nk not in finalargdict:
                missingarg = flagchecker(nk,nv)
                finalargs.append(missingarg)
        # Now we'll tell the user what we've done and hope it's pleasing.  If you're the cautionous type you could get user verification before calling setargs.
        print("You specified these arguments")
        for arg in newargs.split():
            print(arg)
        print("\n")
        print("and the current arguments are")
        for arg in currentargs.split():
            print(arg)
        print("\n")
        finalargset = Set(finalargs) 
        finalstring = " ".join(finalargset)
        print("And the final args I would use for " + currentserver + " are:")
        for arg in finalstring.split():
            print(arg)
    except:
       print 'ERROR';
       dumpStack();
    return finalstring

# This function sets the arguments on a server to a provided value.
def setargs ( mgsvr,jvmargs ):
    print ("Setting JVM args " + jvmargs + " for instance " + mgsvr)
    cd('/Servers')
    cd(mgsvr)
    cd('ServerStart')
    cd(mgsvr)
    cmo.setArguments(jvmargs)
    return
 
# disconnect from adminserver with a positive note because feelings matter.
def disconnectFromAdminserver():
        print 'Disconnecting from the Admin Server.  Have a nice day.';
        disconnect();

connect(userConfigFile=user_file,userKeyFile=key_file,url=admin_server_url)
edit()
startEdit()
# This iterates through all the servers in the environment.  You probably don't want to do this in real life unless your environment is highly homogenous.
try:
    serverNames = cmo.getServers()
    for server in serverNames:
        currentserver=server.getName()
        # Skip the AdminServer because come on.
        if currentserver == 'AdminServer':
            print('skipping Admin Server')
        else:
            finalargstring = genargs(new_arguments,currentserver)
            setargs(currentserver, finalargstring)
except:
    print("ERROR")
    dumpStack()
activate(block="true")
disconnect()
