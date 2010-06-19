#!/usr/bin/python
####################################################################
# FILENAME: nagios/amqp_queue_check
# PROJECT: Platar
# DESCRIPTION: Nagios healthcheck. Verifies that the configured 
#   queue on the specified AMQP server exists and that the queue's
#   count of unacknowledged messages is below a particular threshold.
# 
#   Requires:
#       * py-amqplib >= 0.5 (http://barryp.org/software/py-amqplib/)
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
import sys, os, socket, struct
from amqplib import client_0_8 as amqp
from optparse import OptionParser


### Constants
EXIT_NAGIOS_OK = 0
EXIT_NAGIOS_WARN = 1
EXIT_NAGIOS_CRITICAL = 2

### Validate Commandline Arguments
opt_parser = OptionParser()

opt_parser.add_option("-s", "--server", dest="server",
                      help="AMQP server to connect to.")
opt_parser.add_option("-v", "--vhost", dest="vhost",
                      help="Virtual host to log on to.")
opt_parser.add_option("-u", "--user", dest="user",
                      help="Username to use when authenticating with server.")
opt_parser.add_option("-p", "--password", dest="password",
                      help="Password to use when authenticating with server.")
opt_parser.add_option("-q", "--queue", dest="queue_name",
                      help="Queue name to check.")
opt_parser.add_option("-d", "--durable", action="store_true", dest="durable",
                      default="False", help="Declare queue as durable. (Default: False)")
opt_parser.add_option("-a", "--auto-delete", action="store_true", dest="auto_delete",
                      default="False", help="Declare queue as auto-delete. (Default: False)")
opt_parser.add_option("-w", "--warn", dest="warn_threshold",
                      help="Number of unacknowledged messages that triggers a warning status.")
opt_parser.add_option("-c", "--critical", dest="critical_threshold",
                      help="Number of unacknowledged messages that triggers a critical status.")


args = opt_parser.parse_args()[0]

if args.server == None:
    print "An AMQP server (--server) must be supplied. Please see --help for more details."
    sys.exit(-1)
if args.vhost == None:
    print "A virtual host (--vhost) must be supplied. Please see --help for more details."
    sys.exit(-1)
if args.user == None:
    print "A username (--user) to use when authenticating with AMQP server must be supplied. " \
          "Please see --help for more details."
    sys.exit(-1)
if args.password == None:
    print "A password (--password) to use when authenticating with AMQP server must be supplied. " \
          "Please see --help for more details."
    sys.exit(-1)
if args.queue_name == None:
    print "A queue name (--queue) must be supplied. Please see --help for more details."
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
    mq_conn = amqp.Connection(host=args.server, 
                              userid=args.user, 
                              password=args.password,
                              virtual_host=args.vhost,
                              connect_timeout=5)
    mq_chan = mq_conn.channel()
    queue_stats = mq_chan.queue_declare(queue=args.queue_name,
                                        durable=args.durable,
                                        auto_delete=args.auto_delete,
                                        passive=True)
except (socket.error,
      amqp.AMQPConnectionException,
      amqp.AMQPChannelException), e:
    print "CRITICAL: Problem establishing MQ connection to server %s: %s " \
          % (str(args.server), str(repr(e)))
    sys.exit(EXIT_NAGIOS_CRITICAL)
except struct.error, e:
    print "CRITICAL: Authentication error connecting to vhost '%s' on server '%s'." % \
          (str(args.vhost), str(args.server))
    sys.exit(EXIT_NAGIOS_CRITICAL)

mq_chan.close()
mq_conn.close()

if int(queue_stats[1]) >= critical_threshold:
    print "CRITICAL: %s unacknowledged messages in queue '%s' on vhost '%s', server '%s'." % \
          (str(queue_stats[1]), args.queue_name, str(args.vhost), str(args.server))
    sys.exit(EXIT_NAGIOS_CRITICAL)
elif int(queue_stats[1]) >= warn_threshold:
    print "WARN: %s unacknowledged messages in queue '%s' on vhost '%s', server '%s'." % \
          (str(queue_stats[1]), args.queue_name, str(args.vhost), str(args.server))
    sys.exit(EXIT_NAGIOS_WARN)
else:
    print "OK: %s unacknowledged messages in queue '%s' on vhost '%s', server '%s'." % \
          (str(queue_stats[1]), args.queue_name, str(args.vhost), str(args.server))
    sys.exit(EXIT_NAGIOS_OK)
