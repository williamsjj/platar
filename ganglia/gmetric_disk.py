#!/usr/bin/python
####################################################################
# FILENAME: gmetric_disk.py
# PROJECT: gmetric For Disk IO 
# DESCRIPTION: Pulls disk IO stats and publishes them to Ganglia as
#       Gmetrics.
#
# REQUIRES:
#       gmetric
#       pminfo
#
########################################################################################
# (C)2010 DigiTar, All Rights Reserved
# Distributed under the BSD License
# 
# Redistribution and use in source and binary forms, with or without modification, 
#    are permitted provided that the following conditions are met:
#
#        * Redistributions of source code must retain the above copyright notice, 
#          this list of conditions and the following disclaimer.
#        * Redistributions in binary form must reproduce the above copyright notice, 
#          this list of conditions and the following disclaimer in the documentation 
#          and/or other materials provided with the distribution.
#        * Neither the name of DigiTar nor the names of its contributors may be
#          used to endorse or promote products derived from this software without 
#          specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
# SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, 
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED 
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN 
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH 
# DAMAGE.
#
########################################################################################


import os, re, time

### Set Sampling Interval (in secs)
interval = 1

### Set PCP Config Parameters
cmdPminfo = "/usr/bin/pminfo -f "
reDiskIO = re.compile(r'"(\w+)"] value (\d+)\n')	# RegEx To Compute Value

### Set Ganglia Config Parameters
gangliaMetricType = "uint32"
gangliaMcastPort = "8649"
### NOTE: To add a new PCP disk metric, add the appropriate entry to each dictionary item of gangliaMetrics
###       Each "vertical" column of the dictionary is a different metric entry group.
gangliaMetrics = { "pcpmetric": ["disk.dev.read", "disk.dev.write", "disk.dev.blkread", "disk.dev.blkwrite"], \
		   "name": ["diskio_readbytes", "diskio_writebytes", "diskio_readblks", "diskio_writeblks"], \
		   "unit": ["Kbytes/s", "Kbytes/s", "Blocks/s", "Blocks/s"], \
	   	   "type": ["uint32", "uint32", "uint32", "uint32"]}
cmdGmetric = "/usr/bin/gmetric"

### Zero Sample Lists
### NOTE: Make sure each sample array has as many (device) sub-arrays as there are pcpmetrics being sampled
### NOTE: Sub-arrays are artificially sized at 4 disk devices...if you have more disk devices than 4, increase this size.
lastSample = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
currSample = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]

### Read PCP Metrics
while(1):
	# Interate Through Each PCP Disk IO Metric Desired
	for x in range(0, len(gangliaMetrics["pcpmetric"])):
		pminfoInput, pminfoOutput = os.popen2(cmdPminfo + gangliaMetrics["pcpmetric"][x], 't')
		deviceLines = pminfoOutput.readlines()
		pminfoInput.close()
		pminfoOutput.close()
		
		# Output Metric Data For Each Device Returned By The PCP Metric
		deviceIndex = 2		# Skip the first two lines in the buffer
		while(deviceIndex < len(deviceLines)):
			result = reDiskIO.search(deviceLines[deviceIndex])
			if(result):
				currSample[x][deviceIndex] = int(result.group(2))
				cmdExec = cmdGmetric + " --name=" + gangliaMetrics["name"][x] + "_" + \
						   result.group(1) + " --value=" + str((currSample[x][deviceIndex] - lastSample[x][deviceIndex])) + \
						   " --type=" + gangliaMetrics["type"][x] + " --units=\"" + gangliaMetrics["unit"][x] + "\"" +  \
						   " --mcast_port=" + gangliaMcastPort
				gmetricResult = os.system(cmdExec)
			lastSample[x][deviceIndex] = currSample[x][deviceIndex]
			deviceIndex = deviceIndex + 1
	time.sleep(interval)