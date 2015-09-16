import java.io.File
import java.io.FileWriter
import java.io.IOException
import java.io.Writer

print 'CREATE PATHS';
domain_home=/path/to/your/domain/home

print 'Open Domain';
readDomain(domain_home);

envcsv = open('/path/to/datasources.csv')
# skip the header row ya'll
# create some empty dictionaries.  The first is to create the machines, the second to create the instances, and the third to populate the JVM args.
datasources={}
instances={}
args={}
for row in envcsv:
	#Ignore them comments and header row!
	if row.strip().startswith('#') or row.strip().startswith('DSNAME'):
		continue
	else:
		# since we can't use the stupid CSV libs without a bunch of rigamarol we'll split it at the , and strip unnecessary characters
		items = row.split(',')
		items = [item.strip() for item in items]
		#name each items in the list
		dsname=items[0]
		dburl=items[1]
		user=items[2]
		password=items[3]
		targets=items[4]	
		onsnodes=items[5]
		#update the dictionaries
		datasources.setdefault(dsname, []).append(dburl) 
		datasources.setdefault(dsname, []).append(user) 
		datasources.setdefault(dsname, []).append(password) 
		datasources.setdefault(dsname, []).append(targets) 
		datasources.setdefault(dsname, []).append(onsnodes) 
print(datasources)

#convert dicts to lists of tuples for easier iteration
wldatasources = datasources.items()
#wlinstances = instances.items()
#wljvmargs = args.items()
#
##Create the machines
for dsname,(dburl, user, password, targets, onsnodes) in wldatasources:
	print("creating " + dsname + " with url " + dburl + " and username " + user + " on targets " + targets) 
	cd('/')

	print("create datasource")
	create(dsname,'JDBCSystemResource')
	
	print("Create JdbcDatasourceParams and set JNDI Name")
	cd('/JDBCSystemResource/' + dsname + '/JdbcResource/' + dsname)
	create('myJdbcDataSourceParams','JDBCDataSourceParams')
	cd('JDBCDataSourceParams/NO_NAME_0')
	print ("setting JNDI name to " + dsname)
	set('JNDINames',java.lang.String(dsname))
	set('GlobalTransactionsProtocol', java.lang.String('TwoPhaseCommit'))

	print("Create JDBCDriverParams and set URL, driver, and password info")
	cd('/JDBCSystemResource/' + dsname + '/JdbcResource/' + dsname)
	create('driverparams','JDBCDriverParams')
	cd('JDBCDriverParams/NO_NAME_0')
	print("Setting URL to " + dburl + " and username to " + user)
	set('URL',dburl)
	set('DriverName','oracle.jdbc.xa.client.OracleXADataSource')
	set('PasswordEncrypted', password)
	create('myproperties','Properties')
	cd('Properties/NO_NAME_0')
	create('user',('Property'))
	cd('Property')
	cd('user')
	set('Value',user)

	print("Create JDBCConnectionPoolParams and set Pool properties")
	cd('/JDBCSystemResource/' + dsname + '/JdbcResource/' + dsname)
	create('myJdbcConnectionPoolParams','JDBCConnectionPoolParams')
	cd('JDBCConnectionPoolParams/NO_NAME_0')
	set('TestTableName','SQL SELECT 1 FROM DUAL')

	print("Create JDBCOracleParams and set ONS settings")
	cd('/JDBCSystemResource/' + dsname + '/JdbcResource/' + dsname)
	create('oracleParams','JDBCOracleParams')
	cd('JDBCOracleParams/NO_NAME_0')
	set('FanEnabled','true')                                                                                                                                                                                                                            
        set('OnsWalletFile','')                                                                                                                                                                                                                             
        set('ActiveGridlink','true')                                                                                                                                                                                                                        
        onsnodelist=onsnodes.replace(' ',',')                                                                                                                                                                                                               
	print("Setting ONS Nodes to " + onsnodelist)
        set('OnsNodeList', java.lang.String(onsnodelist))

	print("Set Targets to " + targets)
	cd('/JDBCSystemResources/' + dsname)
	targetlist = targets.replace(' ',',')
	print("coverted " + targets + " to " + targetlist)
	#set('Targets',jarray.array([ObjectName('com.bea:Name=' + targetlist + ',Type=Server')], ObjectName))
	set('Target', java.lang.String(targetlist))


print 'SAVE CHANGES';
updateDomain();
closeDomain();
