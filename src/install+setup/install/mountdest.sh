#!/bin/sh

echo "Scanning for possible destination drives"

# scan IDE devices
echo "--> IDE"
for DEVICE in $(kudzu -qps -t 30 -c HD -b IDE | grep device: | cut -d ' ' -f 2 | sort | uniq); do
		echo -n "---> $DEVICE"
    mount /dev/${DEVICE}1 /harddisk 2> /dev/null
    if [ -n "$(ls /harddisk/ipfire-*.tbz2 2>/dev/null)" ]; then
			umount /harddisk 2> /dev/null
			echo "${DEVICE} is source drive - skipping"
			continue
    else
    	umount /harddisk 2> /dev/null
    	echo -n "$DEVICE" > /tmp/dest_device
    	echo " - yes, it is our destination"
    	exit 0
		fi
done

    mount /dev/${DEVICE}1 /cdrom 2> /dev/null
    if [  ]; then
	     echo -n ${DEVICE} > /tmp/source_device
	     echo "Found Sources in ${DEVICE}"
    else
       umount /cdrom 2> /dev/null
	     echo "Found no Sources in ${DEVICE} skipping"
    fi
    umount /cdrom 2> /dev/null



# scan USB/SCSI devices
echo "--> USB/SCSI"
for DEVICE in $(kudzu -qps -t 30 -c HD -b SCSI | grep device: | cut -d ' ' -f 2 | sort | uniq); do
    echo -n "---> $DEVICE"
		mount /dev/${DEVICE}1 /harddisk 2> /dev/null
    if [ -n "$(ls /harddisk/ipfire-*.tbz2 2>/dev/null)" ]; then
			umount /harddisk 2> /dev/null
			echo "${DEVICE} is source drive - skipping"
			continue
    else
    	umount /harddisk 2> /dev/null
    	echo -n "$DEVICE" > /tmp/dest_device
    	echo " - yes, it is our destination"
    	exit 1
		fi
done

# scan RAID devices
echo "--> RAID"
for DEVICE in $(kudzu -qps -t 30 -c HD -b RAID | grep device: | cut -d ' ' -f 2 | sort | uniq); do
    echo -n "---> $DEVICE"
			mount /dev/${DEVICE}p1 /harddisk 2> /dev/null
    if [ -n "$(ls /harddisk/ipfire-*.tbz2 2>/dev/null)" ]; then
			umount /harddisk 2> /dev/null
			echo "${DEVICE} is source drive - skipping"
			echo " is source drive"
			continue
    else
			umount /harddisk 2> /dev/null
			echo -n "$DEVICE" > /tmp/dest_device
			echo " - yes, it is our destination"
			exit 2
		fi
done

exit 10 # Nothing found
