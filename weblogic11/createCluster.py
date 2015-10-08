import java.io.File
import java.io.FileWriter
import java.io.IOException
import java.io.Writer

domain_home=/path/to/your/domain/home
 
print 'Open Domain';
readDomain(domain_home);

envcsv = open('/path/to/env.csv')
# create some empty dictionaries.  The first is to create the machines, the second to create the instances, and the third to populate the JVM args.
machines={}
instances={}
args={}
admin={}
for row in envcsv:
        #Ignore them comments and header row!
        if row.strip().startswith('#') or row.strip().startswith('APP SERVER'):
                continue
	#if the row is for AdminServer, grab the machine.
        elif row.strip().startswith('AdminServer'):
                adminitems = row.split(',')
                adminitems = [adminitem.strip() for adminitem in adminitems]
                adminsvr = adminitems[0]
                adminmach = adminitems[1]
                continue
        else:
                # since we can't use the stupid CSV libs without a bunch of rigamarol we'll split it at the , and strip unnecessary characters
                items = row.split(',')
                items = [item.strip() for item in items]
                #name each items in the list
                managedsvr=items[0]
                mach=items[1]
                ip=items[2]
                port=items[3]
                jvmargs=items[4]
                cluster=items[5]
                #update the dictionaries
                machines.update({mach:ip})
                instances.setdefault(managedsvr, []).append(mach)
                instances.setdefault(managedsvr, []).append(ip)
                instances.setdefault(managedsvr, []).append(port)
                instances.setdefault(managedsvr, []).append(cluster)
                args.update({managedsvr:jvmargs})

def createmachine( host,ip ):
        print("creating machine for " + host + " with IP of " + ip)
        cd('/')
        create(host, 'Machine');
        cd('/Machine/' + host);
        create(host, 'NodeManager');
        cd('NodeManager/' + host);
        set('ListenAddress', ip);
        set('NMType', 'plain');
        return;

def createserver ( mgsvr,mach,ip,port,cluster ):
        print("Creating server " + mgsvr + " on machine " + mach + " with ip of " + ip + " and a listen port of " + port)
        cd('/')
        create(mgsvr, 'Server')
        cd('Servers/'+mgsvr)
        set('ListenAddress',ip)
        set('ListenPort',int(port))
        set('Machine', mach)                                                                                                                                                                                                                                
        if cluster != "":                                                                                                                                                                                                                                   
                cd('/')                                                                                                                                                                                                                                     
                try:                                                                                                                                                                                                                                        
                        create(cluster, 'Cluster')                                                                                                                                                                                                          
                        print "Created cluster " + cluster                                                                                                                                                                                                  
                except:                                                                                                                                                                                                                                     
                        print "Cluster named " + cluster + " exists, assigning server " + mgsvr + " to it"                                                                                                                                                  
                assign('Server',mgsvr,'Cluster',cluster)                                                                                                                                                                                                    
        else:                                                                                                                                                                                                                                               
                print mgsvr + " is a standalone server, no cluster specified"                                                                                                                                                                               
        return;                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                            
def setargs ( mgsvr,jvmargs ):                                                                                                                                                                                                                              
        print ("Setting JVM args " + jvmargs + " for instance " + mgsvr)                                                                                                                                                                                    
        print "cd'ing to " + mgsvr                                                                                                                                                                                                                          
        cd('/Server')                                                                                                                                                                                                                                       
        cd(mgsvr)                                                                                                                                                                                                                                           
        create(mgsvr,'Log')                                                                                                                                                                                                                                 
        create(mgsvr,'ServerStart')                                                                                                                                                                                                                         
        cd('ServerStart')                                                                                                                                                                                                                                   
        cd(mgsvr)                                                                                                                                                                                                                                           
        cmo.setArguments(jvmargs)                                                                                                                                                                                                                           
        cmo.setClassPath('/opt/app/lib/protocol.jar')                                                                                                                                                                                                       
        cd('/Servers/' + mgsvr + '/Log/' + mgsvr)                                                                                                                                                                                                           
        cmo.setRotationType('byTime')                                                                                                                                                                                                                       
        cmo.setFileCount(14)                                                                                                                                                                                                                                
        return;                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                            
def assignadmin ( mach ):                                                                                                                                                                                                                                   
        cd('/Servers/AdminServer')                                                                                                                                                                                                                          
        set('Machine',mach)                                                                                                                                                                                                                                 
        return;                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                            
#Create the machines                                                                                                                                                                                                                                        
for host,ip in machines.iteritems():                                                                                                                                                                                                                        
        try:                                                                                                                                                                                                                                                
                cd('/Machine/');                                                                                                                                                                                                                            
        except:                                                                                                                                                                                                                                             
                print "No machines exist, continuing"                                                                                                                                                                                                       
                createmachine( host, ip )                                                                                                                                                                                                                   
        else:                                                                                                                                                                                                                                               
                existing = ls()                                                                                                                                                                                                                             
                if (existing.find(host) != -1):                                                                                                                                                                                                             
                        print "A machine named " + host + " already exists. Skipping"                                                                                                                                                                       
                        continue                                                                                                                                                                                                                            
                else:                                                                                                                                                                                                                                       
                        createmachine( host, ip )                                                                                                                                                                                                           
                                                                                                                                                                                                                                                            
# Create the instances and assign them to the correct machine and cluster.                                                                                                                                                                                  
for mgsvr,(mach, ip, port, cluster) in instances.iteritems():                                                                                                                                                                                               
        try:                                                                                                                                                                                                                                                
                cd('/Servers')                                                                                                                                                                                                                              
        except:                                                                                                                                                                                                                                             
                print "No servers configured yet, continuing"                                                                                                                                                                                               
                createserver ( mgsvr, mach, ip, port, cluster )                                                                                                                                                                                             
        else:                                                                                                                                                                                                                                               
                existing = ls()                                                                                                                                                                                                                             
                if (existing.find(mgsvr) != -1):                                                                                                                                                                                                                          
                        print "A server named " + mgsvr + " already exists. Skipping"                                                                                                                                                                                     
                        continue                                                                                                                                                                                                                            
                else:                                                                                                                                                                                                                                       
                        createserver( mgsvr, mach, ip, port, cluster )                                                                                                                                                                                      
                                                                                                                                                                                                                                                            
# configure the JVM args, classpath, and logging                                                                                                                                                                                                            
for mgsvr,jvmargs in args.iteritems():                                                                                                                                                                                                                      
        setargs( mgsvr, jvmargs )                                                                                                                                                                                                                           
                                                                                                                                                                                                                                                            
#if adminmach is populated, assign the adminserver.  If the admin server is on a machine that has not been created, this will fail.
if adminmach != "":                                                                                                                                                                                                                                         
        assignadmin ( adminmach)                                                                                                                                                                                                                            
print 'SAVE CHANGES';                                                                                                                                                                                                                                       
updateDomain();                                                                                                                                                                                                                                             
closeDomain();
