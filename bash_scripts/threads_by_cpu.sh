#!/bin/bash

#ps with no headers and the cpu, pid, and args fields, trim extra spaces, trim leading spaces, sort numerically reverse, cut to the appropriate field, show only the first line.
if [ -z "$1" ]
  then
	printf "No PID was provided, finding the top utilizing process \n"
        topprocpid=`ps --no-headers -eo pcpu,pid,args | tr -s " " | sed 's/^ *//g' |  sort -n -r | cut -d' ' -f2 | head -1`
        topprocname=`ps --no-headers -eo pcpu,pid,args | tr -s " " | sed 's/^ *//g' |  sort -n -r | cut -d' ' -f3 | head -1`
        topprocutil=`ps --no-headers -eo pcpu,pid,args | tr -s " " | sed 's/^ *//g' |  sort -n -r | cut -d' ' -f1 | head -1`
  else
        topprocpid=$1
        topprocname=`ps --no-headers -eo pcpu,pid,args | grep $1 | grep -v grep | grep -v $0 | tr -s " " | sed 's/^ *//g' | cut -d' ' -f3`
        topprocutil=`ps --no-headers -eo pcpu,pid,args | grep $1 | grep -v grep | grep -v $0 | tr -s " " | sed 's/^ *//g' | cut -d' ' -f1`
fi
if echo $topprocname | grep -q java;
        then
                echo "The Java process ${topprocname} with PID ${topprocpid} is using ${topprocutil}% of the CPU.  Dumping utilization of individual threads."
                # Store the lwps in an array, store the cpu utilization in an array, and then convert the lwps to hex and store the new values in an array
                lwps=($(ps -eLo pid,lwp,nlwp,ruser,pcpu,stime,etime | grep $topprocpid | tr -s " " | sed 's/^ *//g' | sort -k 5 -n -r | awk '{print $2, $5}' | grep -v "0.0" | awk '{print $1}'))
                cpu=($(ps -eLo pid,lwp,nlwp,ruser,pcpu,stime,etime | grep $topprocpid | tr -s " " | sed 's/^ *//g' | sort -k 5 -n -r | awk '{print $2, $5}' | grep -v "0.0" | awk '{print $2}'))
                lwphex=($(printf '%x\n' ${lwps[@]}))
                i=0
                #no associative arrays in bash 3, so we will iterate through the hex and cpu arrays in unison.
                while [ $i -lt ${#lwphex[*]} ]; do
                        echo Thread NID ${lwphex[$i]} is using ${cpu[$i]}% CPU
                        i=$(( $i + 1));
                        done
                #Try to find jstack from the process arguments and take a thread dump.  This is a best-effort kind of deal, obviously won't work in implementations that don't have jstack, like Websphere.
                javabin=$(ps -eo pid,args | grep ${topprocpid} | grep -v grep | grep -v $0 |  tr -s " " | sed 's/^ *//' | cut -d " " -f 2 | rev | cut -d "/" -f2- | rev)
                javauser=$(ps -eo pid,user | grep ${topprocpid} | grep -v grep | grep -v $0 | sed 's/^ *//' | cut -d " " -f 2)
                printf "\n Attempting to dump PID ${topprocpid} using jstack in ${javabin} as user ${javauser} \n\n"
                su - ${javauser} -c "${javabin}/jstack -l ${topprocpid}"
        else
                echo "${topprocpid} is not Java, it is $topprocname, and it's using $topprocutil% CPU"
fi
