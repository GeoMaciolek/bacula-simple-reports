#!/usr/bin/env python2
"""
Simple Bacula Reporting (HTML Mail)

Requirements:
 "mysql.connector"
 RedHat / CentOS:
   yum install mysql-connector-python
 Debian/Ubuntu
   ..?

2015-06-22

Send via email:
./report.py | /usr/sbin/sendmail -f "email@domain.com" "email@domain.com"
"""

__author__ = "Geoff Maciolek (GeoffMaciolek@gmail.com)"

# Set these variables
reportfrom = "backupreports@yourdomain.com"

myconfig = {
  'user': 'bacula',
  'password': 'xxYYbacBACulllaaaAAAAa',
  'host': '127.0.0.1',
  'database': 'bacula',
  'raise_on_warnings': True
}

#: how far back to search. (Parameter, figure that bit out!)
history_hours=1440

fancyemail = True


# End setup variables #
#######################

import mysql.connector
import datetime
if fancyemail:
	import premailer #requires installation of pip, python-lxml, and "premailer" via pip

from premailer import transform

from mysql.connector import errorcode
import sys


#: The actual query

myquery = ("SELECT JobId, Name, StartTime, EndTime, Level, JobStatus, JobFiles, JobBytes, Type FROM Job "
"WHERE RealEndTime >= DATE_ADD(NOW(), INTERVAL -%s HOUR) ORDER BY JobID;")
#myquery = ("SELECT JobId, Name, StartTime, EndTime, Level, JobStatus, JobFiles, JobBytes FROM Job WHERE Type='B' AND RealEndTime >= DATE_ADD(NOW(), INTERVAL -%s HOUR) ORDER BY JobID;")
		
# If we support it, enable native MySQL
#if mysql.connector.__version__ > (2, 1) and mysql.connector.HAVE_CEXT:
#  myconfig['use_pure'] = False


#: Dictionary of backup level codes
backuplevelcode = {
	"F": "Full backup",
	"I": "Incremental backup",
	"D": "Dfferential backup",
	"C": "Verify from catalog",
	"V": "Verify init db",
	"O": "Verify volume to catalog",
	"d": "Verify disk to catalog",
	"A": "Verify data on volume",
	"B": "Base job"}

#: Dictionary of job type codes
jobtypecode = {
	"B": "Backup",
	"M": "Previous job that has been migrated",
	"V": "Verify",
	"R": "Restore",
	"c": "Console",
	"C": "Copy",
	"I": "Internal system job",
	"D": "Admin job",
	"A": "Archive",
	"C": "Copy",
	"g": "Migration",
	"S": "Scan"}
	
#: Dictionary of job status codes
jobstatuscode = {
	"A": "Cancelled by user",
	"B": "Blocked",
	"C": "Created, but not running",
	"c": "Waiting for client resource",
	"D": "Verify differences",
	"d": "Waiting for maximum jobs",
	"E": "Terminated in error",
	"e": "Non-fatal error",
	"f": "fatal error",
	"F": "Waiting on File Daemon",
	"j": "Waiting for job resource",
	"M": "Waiting for mount",
	"m": "Waiting for new media",
	"p": "Waiting for higher priority jobs to finish",
	"R": "Running",
	"S": "Scan",
	"s": "Waiting for storage resource",
	"T": "Terminated normally",
	"t": "Waiting for start time"}

header="""Backup History for the past X hours
--------------------------------------

JobId        Name           Start Time            Stop Time       Level  Status   Files       Bytes
-----   --------------  -------------------  -------------------  -----  ------  --------  -----------"""
htmlemailheader="From: <" + reportfrom + """>
Subject: Backup Report
MIME-Version: 1.0
Content-Type: text/html; charset=ISO-8859-1"""
simplehtmlheader="<html><body>"
fancyhtmlheader="""<html><head><style>
.datagrid table { border-collapse: collapse; text-align: left; width: 100%; }
.datagrid {font: normal 12px/150% Arial, Helvetica, sans-serif; background: #fff; overflow: hidden; border: 1px solid #8C8C8C; -webkit-border-radius: 3px; -moz-border-radius: 3px; border-radius: 3px; }
.datagrid table td, .datagrid table th { padding: 3px 10px; }
.datagrid table thead th {background:-webkit-gradient( linear, left top, left bottom, color-stop(0.05, #808088), color-stop(1, #484868) );background:-moz-linear-gradient( center top, #808088 5%, #484868 100% );filter:progid:DXImageTransform.Microsoft.gradient(startColorstr='#808088', endColorstr='#484868');background-color:#808088; color:#FFFFFF; font-size: 13px; font-weight: bold; border-left: 1px solid #A3A3C0; }
.datagrid table thead th:first-child { border: none; }
.datagrid table tbody td { color: #7D7D7D; border-left: 1px solid #DBDBDB;font-size: 12px;font-weight: normal; }
.datagrid table tbody .alt td { background: #EBEBF0; color: #7D7D7D; }
.datagrid table tbody .fail td { background: #D07878; color: #002020; }
.datagrid table tbody td:first-child { border-left: none; }
.datagrid table tbody tr:last-child td { border-bottom: none; }
</style></head><body>"""

#htmltableheader="<table><tr><th>JobID</th><th>Name</th><th>Start Time</th><th>Stop Time</th><th>Level</th><th>Status</th><th>Files</th><th>Bytes</th><th>Job Type</th> </tr>"
fancyhtmltableheader='<div class="datagrid"><table><thead><tr><th>JobID</th><th>Name</th><th>Start Time</th><th>Stop Time</th><th>Level</th><th>Status</th><th>Files</th><th>Bytes</th><th>Job Type</th></tr></thead><tbody>'

simplehtmltablefooter="</table>"
fancyhtmltablefooter="</tbody></table>"
htmlfooter="</body></div></html>"
class job:
	def __init__(self, jobid, name, starttime, endtime, level, jobstatus, jobfiles, jobbytes, jobtype):
		self.jobid = jobid
		self.name = name
		self.starttime = starttime
		self.endtime = endtime
		self.level = level
		self.jobstatus = jobstatus
		self.jobfiles = jobfiles
		self.jobbytes = jobbytes
		self.jobtype = jobtype

def tprint(stringtoprint):
	"""Basic Timestamped Printing"""
	#replace me with real logging ala http://stackoverflow.com/questions/28330317/print-timestamp-for-logging-in-python
	print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " " + stringtoprint	


# Begin the whole script thing!


try:
	#: this is the var var var
	baculadb = mysql.connector.connect(**myconfig)
	#print baculadb

except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    tprint("Access Denied (username / password?)")
    sys.exit(1)
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    tprint("Database does not exist")
    sys.exit(1)
  else:
    print(err)
    sys.exit(1)
#else:	
	#tprint("Connection Succeeded")
	#print "Hmmm... " + "$baculadb"

cursor = baculadb.cursor()
cursor.execute(myquery,(history_hours,))

jobs = []

#print header

reporttext = ""


reporttext+=fancyhtmlheader
reporttext+=fancyhtmltableheader
for (JobId, Name, StartTime, EndTime, Level, JobStatus, JobFiles, JobBytes, Type) in cursor:
	#print "{}, {}, {}, {}, {}, {}, {}, {}".format(JobId, Name, StartTime, EndTime, Level, JobStatus, JobFiles, JobBytes)
	
	tmpjob = job(JobId, Name, StartTime, EndTime, Level, JobStatus, JobFiles, JobBytes, Type)
	jobs.append(tmpjob)

row=0
for (j) in jobs:
	#print "{}, {}, {}, {}, {}, {}, {}, {}, {}".format(j.jobid, j.name, j.starttime, j.endtime, backuplevelcode[j.level], jobstatuscode[j.jobstatus], j.jobfiles, j.jobbytes, jobtypecode[j.jobtype])
	if j.jobstatus != "T":
		rowstr='<tr class="fail">'
	else:
		if row % 2 == 0:
			rowstr="<tr>"
		else:		
			rowstr='<tr class="alt">'
	reporttext+= rowstr + "<td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(j.jobid, j.name, j.starttime, j.endtime, backuplevelcode[j.level], jobstatuscode[j.jobstatus], j.jobfiles, j.jobbytes, jobtypecode[j.jobtype])
	row+=1
reporttext+=fancyhtmltablefooter
reporttext+=htmlfooter
cursor.close()
baculadb.close()

#print reporttext #vanilla
#print htmlemailheader+reporttext 
print htmlemailheader + transform(reporttext)
