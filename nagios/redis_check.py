#!/usr/bin/python
####################################################################
# FILENAME: nagios/redis_check
# PROJECT: Misc Scripts
# DESCRIPTION: Nagios healthcheck. Verifies that the configured 
#   queue on the specified AMQP server exists and that the queue's
#   count of unacknowledged messages is below a particular threshold.
#
# $Id$
####################################################################
# (C)2009 DigiTar, All Rights Reserved
# CONFIDENTIAL
####################################################################

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
    print "OK: Redis is using %dMB of RAM. Days Up: %s Clients: %s Version: %s Polling API: %s" % \
          (redis_stats["used_memory"]/1024/1024, 
           redis_stats["uptime_in_days"],
           redis_stats["connected_clients"], 
           redis_stats["redis_version"],
           redis_stats["multiplexing_api"])
    sys.exit(EXIT_NAGIOS_OK)
