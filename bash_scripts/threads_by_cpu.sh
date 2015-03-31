#!/bin/bash
if ps -eo pcpu,pid,args | sort -k 1 -n -r | tr -s " " | head -n 1 | grep -q java;
	then
		echo "These are the thread IDs of the Java threads using the CPU, and the amount of CPU they're using:"
		#Get the ps output for the Java process, then print the thread ID and CPU utilization, excluding any with 0% cpu
		ps -eLo pid,lwp,nlwp,ruser,pcpu,stime,etime | grep `ps -eo pcpu,pid | sort -k 1 -n -r | tr -s " " | sed 's/^ *//' | head -n 1 | cut -d " " -f 2` | tr -s " " | sort -k 5 -n -r | awk '{print $2, $5}' | grep -v " 0.0"
		printf "\n\nHere are the converted Hex IDs of the threads using CPU, sorted by cpu utilization. Find them in the thread dump below as \"nid\" to identify problematic processes: \n"
		#create an array of thread IDs in decimal
		topthreads=$(ps -eLo pid,lwp,nlwp,ruser,pcpu,stime,etime | grep `ps -eo pcpu,pid | sort -n -k 1 -r | sed 's/^ *//' | tr -s " " | head -n 1 | cut -d " " -f 2` | tr -s " " | sort -n -k 5 -r | grep -v " 0.0"| awk '{print $2}' )
		#Iterate through the array and output the value as hex.
		printf '%x\n' ${topthreads[@]}
		# get the path to jstack, (assumes it's in the bin folder of the JDK that launched the process), the pid of the java process with the highest utilization, and the user it's running as.
		javapid=$(ps -eo pcpu,pid | sort -k 1 -n -r | tr -s " " | sed 's/^ *//' | head -n 1 | cut -d " " -f 2)
		javabin=$(ps -eo pid,args | grep ${javapid} | grep -v grep | tr -s " " | sed 's/^ *//' | cut -d " " -f 2 | rev | cut -d "/" -f2- | rev)
		javauser=$(ps -eo pid,user | grep ${javapid} | grep -v grep | sed 's/^ *//' | cut -d " " -f 2)
		printf "\n Dumping PID ${javapid} using jstack in ${javabin} as user ${javauser} \n\n"
		su - ${javauser} -c "${javabin}/jstack -l ${javapid}"
	else
		topproc=$(ps -eo pcpu,pid,args | sort -k 1 -n -r | tr -s " " | sed 's/^ *//' | head -n 1 )
		printf "top utilization process is \n ${topproc} \n"
fi
