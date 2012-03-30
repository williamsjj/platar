#!/usr/bin/python
# -*- coding: utf-8-*-
####################################################################
# FILENAME: dtar_sophos_updater.py
# PROJECT: Miscellaneous Scripts
# DESCRIPTION: Updates Sophos databases and IDEs
#
# $Id$
####################################################################
# (C)2012 DigiTar, All Rights Reserved
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
####################################################################

from argparse import ArgumentParser
import re, sys, os, logging, signal, urllib2
import time, zipfile, cStringIO, pwd, grp, gc

re_pid_file = re.compile(r"^\s*pidfile:\s*(.*)")
re_ide_dir = re.compile(r"^\s*idedir:\s*(.*)")
re_sav_user = re.compile(r"^\s*user:\s*(.*)")
re_sav_group = re.compile(r"^\s*group:\s*(.*)")

logging_levels = {"debug" : logging.DEBUG,
                  "info" : logging.INFO,
                  "warning" : logging.WARNING,
                  "error" : logging.ERROR}

parser = ArgumentParser()
parser.add_argument("--sav-version", dest="sav_version", required=True,
                    help="Version of SAV you're running. Ex. 4.75 (4.75.0 should shortened to 4.75)")
parser.add_argument("--conf-file", dest="conf_file",
                    default="/etc/savdi/savdid.conf",
                    help="Location of the SAVDI configuration file.")
parser.add_argument("--ide-update-url", dest="ide_update_url",
                    default="http://www.sophos.com/downloads/ide/",
                    help="Base URL for downloading IDE files.")
parser.add_argument("--update-interval", dest="update_interval", type=int,
                    default=15,
                    help="Interval (in minutes) to wake up and check for IDE updates.")
parser.add_argument("--pid-file", dest="pid_file",
                    default="/var/run/dtar_sophos_updater.pid",
                    help="Full path where updater should store its PID file.")
parser.add_argument("--log-file", dest="log_file",
                    default="/var/log/dtar_sophos_updater.log",
                    help="Path to updater's log file.")
parser.add_argument("--log-level", dest="log_level", default="info",
                    help="Logging verbosity. Values: debug, info, warning, error")

args = parser.parse_args()

## Service functions
def read_savdi_conf(path):
    """Reads the SAVDI config file and extracts the necessary parameters."""
    try:
        f = open(path, "r")
    except IOError:
        print "ERROR: Could not open SAVDI config file '%s'." % args.conf_file
        sys.exit(-1)
    
    pid_file = ""
    ide_dir = ""
    sav_user = ""
    sav_group = ""
    
    for line in f.readlines():
        if re_pid_file.match(line):
            pid_file = re_pid_file.match(line).groups()[0]
        if re_ide_dir.match(line):
            ide_dir = re_ide_dir.match(line).groups()[0]
        if re_sav_user.match(line):
            sav_user = re_sav_user.match(line).groups()[0]
        if re_sav_group.match(line):
            sav_group = re_sav_group.match(line).groups()[0]
    
    if not pid_file:
        print "ERROR: Could not locate 'pidfile' directive in SAVDI config file."
        sys.exit(-1)
    if not ide_dir:
        print "ERROR: Could not locate 'idedir' directive in SAVDI config file."
        sys.exit(-1)
    if not sav_user:
        print "ERROR: Could not locate 'user' directive in SAVDI config file."
        sys.exit(-1)
    if not sav_group:
        print "ERROR: Could not locate 'group' directive in SAVDI config file."
        sys.exit(-1)
    
    try:
        pid = int(open(pid_file, "r").read())
    except Exception, e:
        print "ERROR: Error reading contents of SAVDI PID file. (%s)" % str(e)
        sys.exit(-1)
    
    return (pid, ide_dir, sav_user, sav_group)
    
def validate_ide_dir(path, user, group):
    """Validate the existence of the IDE dir and make it if it doesn't exist."""
    if not os.path.exists(path):
        os.mkdir(path, int(0644))
        os.chown(path, user, group)
    return

def terminate_handler(signum, frame):
    """Handles shutdown termination."""
    logging.info("Shutting down.")
    logging.debug("Removing PID file.")
    try:
        os.remove(args.pid_file)
    except Exception, e:
        logging.error("Could not remove PID file '%s'. (%s)" % (args.pid_file, str(e)))
        sys.exit(-4)
    
    sys.exit(0)

def ide_update_available(url, path):
    """Checks to see if an IDE update is available."""
    local_rev = ""
    
    if os.path.exists(path + "/ide.rev"):
        logging.debug("Opening local IDE revision number file.")
        f = open(path + "/ide.rev")
        local_rev = f.read()
        logging.debug("Local IDE revision: '%s'" % local_rev)
        f.close()
    
    logging.debug("Retrieving remote IDE revision (%s)" % (url + "ide_dgst.txt"))
    remote_rev = urllib2.urlopen(url + "ide_dgst.txt").read()[:-1]
    logging.debug("Remote IDE revision: '%s'" % remote_rev)
    
    if remote_rev != local_rev:
        logging.info("New IDE package available. Rev: %s" % remote_rev)
        return True
    else:
        logging.info("Current IDE files are up-to-date. Rev: %s" % remote_rev)
        return False

def ide_download_update(url, path, version, pid, user, group):
    """Download the latest IDE update."""
    
    version = "".join(version.split("."))
    
    # Retrieve remote revision
    logging.debug("Retrieving remote IDE revision (%s)" % (url + "ide_dgst.txt"))
    remote_rev = urllib2.urlopen(url + "ide_dgst.txt").read()[:-1]
    
    # Retrieve remote IDE ZIP contents
    logging.info("Retrieving new IDE package (%s)" % ("%s%s_ides.zip" % (url, version)))
    try:
        ide_contents = urllib2.urlopen("%s%s_ides.zip" % (url, version))
        c_ide_contents= cStringIO.StringIO(ide_contents.read())
        del(ide_contents)
    except Exception, e:
        logging.error("Could not download %s%s_ides.zip! Skipping update." % (url, version))
        return
    
    # Unpack new IDE
    logging.info("Unpacking new IDE (%s) into %s." % (remote_rev, path))
    try:
        zf = zipfile.ZipFile(c_ide_contents)
        ide_list = zf.namelist()
        zf.extractall(path)
        del(c_ide_contents)
        del(zf)
        for ide_file in ide_list:
            os.chown("%s/%s" % (path,ide_file), user, group)
    except Exception, e:
            logging.error("Could not unpack IDE. Skipping update. (%s)" % str(e))
            return
    
    # Notify SAVDI to reload it's databases
    try:
        logging.info("Sending reload signal to SAVDI PID (%s)" % pid)
        os.kill(pid, signal.SIGHUP)
    except Exception, e:
        logging.error("Problem sending SIGHUP to SAVDI PID (%s). (%s)" % (pid, str(e)))
        return
    
    # Unpack and reload successful, so update local revision file
    try:
        logging.debug("Updating local IDE revision file.")
        f = open(path + "/ide.rev", "w")
        f.write(remote_rev)
        f.close()
    except Exception, e:
        logging.error("Could not write new revision # to '%s'. (%s)" % (path + "/ide.rev", str(e)))
        return
    
    return

## Main
if __name__ == "__main__":
    
    # Load SAVDI configuration file
    savdi_pid, ide_dir, sav_user, sav_group = read_savdi_conf(args.conf_file)
    
    # Validate UID and GID
    try:
        sav_user = pwd.getpwnam(sav_user)[2]
    except Exception, e:
        print "ERROR: Could find user '%s'." % sav_user
        sys.exit(-2)
    
    try:
        sav_group = grp.getgrnam(sav_group)[2]
    except Exception, e:
        print "ERROR: Could find group '%s'." % sav_group
        sys.exit(-2)
    
    # Prepare IDE directory for downloads
    try:
        validate_ide_dir(ide_dir, sav_user, sav_group)
    except Exception, e:
        print "ERROR: Could not create IDE directory '%s'. (%s)" % (ide_dir, str(e))
        sys.exit(-2)
    
    # Write this daemon's PID file
    try:
        f = open(args.pid_file, "w")
        f.write(str(os.getpid()))
        f.close()
    except Exception, e:
        print "ERROR: Error writing own PID file. (%s)" % str(e)
        sys.exit(-3)
    
    # Setup logging & SIGTERM handler
    FORMAT = '%(asctime)-15s - %(levelname)s:\t %(message)s'
    logging.basicConfig(filename=args.log_file,format=FORMAT,level=logging_levels[args.log_level.lower()])
    signal.signal(signal.SIGTERM, terminate_handler)
    
    # Start main updater loop
    logging.info("Starting DigiTar Sophos Updater...")
    while True:
        logging.info("---------STARTING UPDATE RUN---------")
        if ide_update_available(args.ide_update_url, ide_dir):
            ide_download_update(args.ide_update_url, ide_dir, args.sav_version, savdi_pid, sav_user, sav_group)
        
        # Force garbage collection
        gc.collect()
        logging.debug("GC Objects: " + str(gc.get_count()))
        logging.info("---------ENDING UPDATE RUN---------")
        logging.info("Sleeping for %d minutes." % args.update_interval)
        time.sleep(args.update_interval * 60)
    