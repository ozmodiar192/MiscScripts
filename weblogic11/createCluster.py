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
for row in envcsv:
	#Ignore them there comments and header row
	if row.strip().startswith('#') or row.strip().startswith('APP SERVER'):
		continue
	else:
		# since we can't use the stupid CSV libs without a bunch of rigamarol we'll split it at the , and strip unnecessary characters
		items = row.split(',')
		items = [item.strip() for item in items]
		#name each items in the list for easier reference
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

#convert dicts to lists of tuples for easier iteration
wlmachines = machines.items()
wlinstances = instances.items()
wljvmargs = args.items()

#Create the machines
for host,ip in wlmachines:
	print("creating machine for " + host + " with IP of " + ip)
	cd('/');
	create(host, 'Machine');
	cd('/Machine/' + host);
	create(host, 'NodeManager');
	cd('NodeManager/' + host);
	set('ListenAddress', ip);
	set('NMType', 'plain');

# Create the instances and assign them to the correct machine and cluster.
for mgsvr,(mach, ip, port, cluster) in wlinstances:
	print("creating instance " + mgsvr + " on host " + mach + " with ip " + ip + " and port " + port + " in cluster " + cluster)
	cd('/')
	create(mgsvr, 'Server')
	cd('Servers/'+mgsvr)
	set('ListenAddress',ip)
	set('ListenPort',int(port))
	set('Machine', mach)
	# Check if the server should be in a cluster or not.
	if cluster != "":
		cd('/')
		try:
			#Try to create the cluster.  If it errors, continue.  Should probably find the correct exception and add it to except......
			create(cluster, 'Cluster')
		except:
			print "Cluster exists, assigning server " + mgsvr + " to it"
		assign('Server',mgsvr,'Cluster',cluster)
	else:
		print mgsvr + " is a standalone server, no cluster specified"

# configure the JVM args, classpath, and logging
for mgsvr,jvmargs in wljvmargs:
	print ("Setting JVM args " + jvmargs + " for instance " + mgsvr)
	print "cd'ing to " + mgsvr
	cd('/')
	cd('/Server')
	cd(mgsvr)
	create(mgsvr,'Log')
	# Should check if ServerStart exists instead of doing it blindly
	create(mgsvr,'ServerStart')
	cd('ServerStart')
	cd(mgsvr)
	cmo.setArguments(jvmargs)
	cmo.setClassPath('/opt/app/lib/protocol.jar')	
	cd('/Servers/' + mgsvr + '/Log/' + mgsvr)
	cmo.setRotationType('byTime')
	cmo.setFileCount(14)
print 'SAVE CHANGES';
updateDomain();
closeDomain();
