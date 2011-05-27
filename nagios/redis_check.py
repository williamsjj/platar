#!/usr/bin/python
####################################################################
# FILENAME: nagios/redis_check
# PROJECT: Misc Scripts
# DESCRIPTION: Nagios healthcheck. Verifies that the configured 
#   queue on the specified AMQP server exists and that the queue's
#   count of unacknowledged messages is below a particular threshold.
#
# $Id$
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

import sys, os, socket, struct
import redis
from optparse import OptionParser


### Constants
EXIT_NAGIOS_OK = 0
EXIT_NAGIOS_WARN = 1
EXIT_NAGIOS_CRITICAL = 2

### Validate Commandline Arguments
opt_parser = OptionParser()

opt_parser.add_option("-s", "--server", dest="server",
                      help="Redis server to connect to.")
opt_parser.add_option("-p", "--port", dest="port",
                      help="Redis port to connect to.")
opt_parser.add_option("-w", "--warn", dest="warn_threshold",
                      help="Memory utlization (in MB) that triggers a warning status.")
opt_parser.add_option("-c", "--critical", dest="critical_threshold",
                      help="Memory utlization (in MB) that triggers a critical status.")


args = opt_parser.parse_args()[0]

if args.server == None:
    print "A Redis server (--server) must be supplied. Please see --help for more details."
    sys.exit(-1)
if args.port == None:
    print "A Redis port number must be supplied. " \
          "Please see --help for more details."
    sys.exit(-1)
if args.warn_threshold == None:
    print "A warning threshold (--warn) must be supplied. Please see --help for more details."
    sys.exit(-1)
try:
    warn_threshold = int(args.warn_threshold)
    if warn_threshold < 0:
        raise ValueError
except ValueError, e:
    print "Warning threshold (--warn) must be a positive integer. Please see --help for more details."
    sys.exit(-1)
if args.critical_threshold == None:
    print "A critical threshold (--critical) must be supplied. Please see --help for more details."
    sys.exit(-1)
try:
    critical_threshold = int(args.critical_threshold)
    if critical_threshold < 0:
        raise ValueError
except ValueError, e:
    print "Critical threshold (--critical) must be a positive integer. Please see --help for more details."
    sys.exit(-1)


### Check Queue Count
try:
    redis_conn = redis.Redis(host=args.server, port=int(args.port))
    redis_stats = redis_conn.info()
except (socket.error,
        redis.exceptions.ConnectionError), e:
    print "CRITICAL: Problem establishing connection to Redis server %s: %s " \
          % (str(args.server), str(repr(e)))
    sys.exit(EXIT_NAGIOS_CRITICAL)


if redis_stats["used_memory"]/1024/1024 >= critical_threshold:
    print "CRITICAL: Redis is using %dMB of RAM." % (redis_stats["used_memory"]/1024/1024)
    sys.exit(EXIT_NAGIOS_CRITICAL)
elif redis_stats["used_memory"]/1024/1024 >= warn_threshold:
    print "WARN: Redis is using %dMB of RAM." % (redis_stats["used_memory"]/1024/1024)
    sys.exit(EXIT_NAGIOS_WARN)
else:
    db_key_count = ""
    for key in redis_stats.keys():
        if key[:2] == "db":
            db_key_count = db_key_count + ", DB-%s: %s keys" % (key[2:], redis_stats[key]["keys"])
    print "OK: Redis is using %dMB of RAM. Days Up: %s, Clients: %s, Version: %s, Polling API: %s%s" % \
          (redis_stats["used_memory"]/1024/1024, 
           redis_stats["uptime_in_days"],
           redis_stats["connected_clients"], 
           redis_stats["redis_version"],
           redis_stats["multiplexing_api"],
           db_key_count)
    sys.exit(EXIT_NAGIOS_OK)
