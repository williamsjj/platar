#!/usr/bin/python
####################################################################
# FILENAME: mysql_snapback.py
# PROJECT: Miscellaneous Tools
# DESCRIPTION: Quiesces a MySQL server and uses ZFS to pull a backup
#       by snapshotting both the database and log filesystems during
#       the quiesced state. SnapBack is InnoDB aware/safe (sets 
#       AUTOCOMMIT=0 before beginning). Also, it will record the 
#       current master replication log file name and position in the
#       ZFS snapshot name. 
#
#
# $Id: mysql_snapback.py 1524 2008-01-16 19:08:14Z  $
########################################################################################
# (C)2008 DigiTar, All Rights Reserved
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

import ConfigParser
import MySQLdb
from optparse import OptionParser
import sys,os,time,commands,re

### Globals & Constants
_txt_program_revision = "0.1"
_txt_program_name = "DigiTar SnapBack (MySQL)"

### Find the configuration file

_args_parser = OptionParser(usage="%prog --filename snapback.cfg", version=_txt_program_name + " " + _txt_program_revision)
_args_parser.add_option("-f", "--filename", dest="FN_CONFIG",help="Configuration file containing MySQL and ZFS settings to use for backup run.")

_arg_program_options, _arg_leftover = _args_parser.parse_args()

if _arg_program_options.FN_CONFIG==None:
    print "\nMust supply a configuration filename. Please use --help for syntax."
    sys.exit(-1)

### Load in configuration settings
_config_parser = ConfigParser.SafeConfigParser()
try:
    _f_config = open(_arg_program_options.FN_CONFIG)
except IOError, e:
    print "\nCannot find " + _arg_program_options.FN_CONFIG + ". Please check the argument and try again."
    sys.exit(-2)

_config_parser.readfp(_f_config)

# Validate individual required options
try:
    _mysql_server = _config_parser.get("MySQL","server")
    _mysql_user = _config_parser.get("MySQL","user")
    _mysql_pass = _config_parser.get("MySQL","password")

    _fn_zfs_cmd = _config_parser.get("ZFS","zfs_command")
    _fn_zfs_db_fs = _config_parser.get("ZFS","db_fs_name")
    _bool_master_naming = _config_parser.getboolean("ZFS","masterinfo_naming")
except ConfigParser.NoOptionError, e:
    print "\n" + repr(e)
    print "Please make sure all required sections and options are supplied and try again."
    _f_config.close()
    sys.exit(-3)

# Treat log_fs_name option separately as it is optional. If not present, we will
# set it to the same as db_fs_name.
try:
    _fn_zfs_log_fs = _config_parser.get("ZFS","log_fs_name")
except ConfigParser.NoOptionError:
    _fn_zfs_log_fs = _fn_zfs_db_fs
    pass
_f_config.close()


### Verify ZFS FS are present
_zfs_list_status,_zfs_list_output  = commands.getstatusoutput(_fn_zfs_cmd + " list")
if not re.compile(_fn_zfs_db_fs).search(_zfs_list_output, 1):
    print "\nNo ZFS DB filesystem named " + _fn_zfs_db_fs + " exists. Please check your configuration and try again."
    sys.exit(-4)
if _fn_zfs_db_fs != _fn_zfs_log_fs:
    if not re.compile(_fn_zfs_log_fs).search(_zfs_list_output, 1):
        print "No ZFS Log filesystem named " + _fn_zfs_log_fs + " exists. Please check your configuration and try again."
        sys.exit(-4)
print "\nAll specified ZFS filesystems are present."

### Connect to MySQL
print "\n\nSnapBack is connecting to MySQL:"
try:
    _db_backup = MySQLdb.connect(host=_mysql_server, user=_mysql_user, passwd=_mysql_pass)
except MySQLdb.OperationalError:
    print "Unable to connect to MySQL server " + _mysql_server + ". Please check the configuration file and try again."
    sys.exit(-5)
print "\tConnected to " + _mysql_server + "."
_cu_backup = _db_backup.cursor()

_time_snapshot = time.strftime("%Y%m%d%H%M%S")

# Make operation InnoDB safe/consistent.
_cu_backup.execute("SET AUTOCOMMIT=0;")
print "\tPrepared MySQL to ensure InnoDB consistency."

### Pull ZFS snapshots.

print "\n\nSnapBack is commencing snapshot run:"
print "\tLocking tables (if this is taking awhile please check the MySQL process list)."
_cu_backup.execute("FLUSH TABLES WITH READ LOCK;")
print "\tTables locked."
_cu_backup.execute("SHOW MASTER STATUS;")
_rows_master_status = _cu_backup.fetchone()
# Notate current master log file and position if master_naming is on
if _bool_master_naming == True:
    _txt_master_status = "_" + str(_rows_master_status[0]) + "_" + str(_rows_master_status[1])
else:
    _txt_master_status = ""
print "\tMaster status retrieved."

try:
    # Snapshot DB
    print "\tSnapping ZFS DB filesystem."
    _zfs_dbsnap_status,_zfs_dbsnap_output = commands.getstatusoutput(_fn_zfs_cmd + " snapshot " + _fn_zfs_db_fs + "@" + _time_snapshot + _txt_master_status)
    if str(_zfs_dbsnap_status) != "0":
        print "An error occurred while executing the ZFS snapshot on " + _fn_zfs_db_fs + ". Unlocking tables and quitting."
        _cu_backup.execute("UNLOCK TABLES;")
        sys.exit(-7)
    # Snapshot Logs (if specified)
    if _fn_zfs_db_fs != _fn_zfs_log_fs:
        print "\tSnapping ZFS Log filesystem."
        _zfs_logsnap_status,_zfs_logsnap_output = commands.getstatusoutput(_fn_zfs_cmd + " snapshot " + _fn_zfs_log_fs + "@" + _time_snapshot + _txt_master_status)
        if str(_zfs_logsnap_status) != "0":
            print "An error occurred while executing the ZFS snapshot on " + _fn_zfs_log_fs + ". Unlocking tables and quitting."
            _cu_backup.execute("UNLOCK TABLES;")
            sys.exit(-7)
except:
    _cu_backup.execute("UNLOCK TABLES;")
    print "\tAn unrecoverable error occurred while trying to pull the snapshots. We have unlocked the tables. Please check your system logs for details as to the ZFS error."
    sys.exit(-7)

print "\tUnlocking tables."
_cu_backup.execute("UNLOCK TABLES;")
print "\tTables unlocked."
print "SnapBack snapshot run completed."

print "\n\nSnapshots created:"
print "\t" + _fn_zfs_db_fs + "@" + _time_snapshot + _txt_master_status
if _fn_zfs_db_fs != _fn_zfs_log_fs:
    print "\t" + _fn_zfs_log_fs + "@" + _time_snapshot + _txt_master_status
