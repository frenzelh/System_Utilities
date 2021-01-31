#!/usr/bin/env python
# This script parses /var/log/messages (or a similar file, e.g., a backed up
# version) for messages from MRMON (MegaRAID monitor). Anything regarding
# "fan speed" and "power state" is skipped. If there are any other messages,
# they will be sent in an email to root of the host that the script is run on.
# The script creates an empty file as a time stamp for the last time it
# was run. By default, only newer messages are considered.
#
# H. Frenzel, School of Oceanography, University of Washington
#
# First version: October 20, 2020

import argparse
import os
import smtplib
import subprocess
import time

from email.message import EmailMessage


def get_month(month):
    ''' Return the 3-letter short string for the given month (1-offset).
    Throw an exception if month < 1 or month > 12.
    '''
    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct',
              'Nov','Dec']
    if mth < 1 or mth > 12:
        raise RuntimeError('value out of range (1-12)')
    else:
        return months[mth-1]

def send_email(address, content, day, month):
    ''' Format an email alert regarding the messages from MRMON in the
    input file (/var/log/messages or similar) from the given day and month.
    Send it to the given address.
    '''
    body = 'Messages from MSM were found for {0:s} {1:d}:\n\n'.format(month,
                                                                      day)
    body += content
    host = subprocess.getoutput('hostname -s')
    
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = 'MegaRAID messages'
    msg['From'] = 'system_{0:s}'.format(host) 
    msg['To'] = address

    # send the message via localhost SMTP server
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

def find_new_content(content, file_last_run):
    ''' Parse the content for items that were added after the file named
    "file_last_run" was created and return them. 
    If the file doesn't exist, the full content will be returned instead. 
    '''
    if not os.path.exists(file_last_run):
        return content
    # get the modification time of the empty "time stamp" file
    # and convert it to an epoch time for easy comparison
    mtime = time.ctime(os.path.getmtime(file_last_run))
    mtime_obj = time.strptime(mtime, '%a %b %d %H:%M:%S %Y')
    mtime_epoch = time.mktime(mtime_obj)
    this_year = mtime_obj.tm_year
    new_content = ''
    for line in content.split('\n'):
        date_time = '{0:s} {1:d}'.format(line[0:15], this_year)
        this_time_obj = time.strptime(date_time,
                                      '%b %d %H:%M:%S %Y')
        this_time_epoch = time.mktime(this_time_obj)
        # add a minute of tolerance so we won't miss anything
        if this_time_epoch > mtime_epoch - 60:
            new_content += line
    return new_content

def parse_file(filename, day, month, check_all):
    '''Parse the file with the given filename for entries for the
    given day and month (or the given day of the current month,
    or today if neither day nor month is specified).
    Look for lines that include MRMON, but exclude messages about
    "fan speed" and "power state".
    If check_all is set or a day other than today is selected, 
    send all messages from the selected day; 
    otherwise, send only those recorded since this script was last run.
    '''
    if day and month:
        mth = get_month(month)
    else:
        mth = time.strftime('%B')[0:3]
    if not day:
        day = int(time.strftime('%d'))

    cmd1 = 'grep "{0:s} {1:2d}" {2:s}'.format(mth, day, filename)
    cmd2 = 'grep MRMON | grep -vi "fan speed" | grep -vi "power state"'
    cmd = '{0:s} | {1:s}'.format(cmd1, cmd2)
    content = subprocess.getoutput(cmd)
    today = '{0:s} {1:2d}'.format(time.strftime('%B')[0:3],
                                  int(time.strftime('%d')))
    date = '{0:s} {1:2d}'.format(mth, day)
    if today == date:
        file_last_run = '{0:s}_last_check'.format(filename)
        if not check_all and content:
            content = find_new_content(content, file_last_run)
        # update the "last run" file if script was run for today    
        subprocess.run(['touch', file_last_run])
            
    if content:
        send_email('root', content, day, mth)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', default = '/var/log/messages',
                        help='name of the input file (default: /var/log/messages)')
    parser.add_argument('-d', '--day', type = int, default = None,
                        help='day to search for (default: today)')
    parser.add_argument('-m', '--month', type = int, default = None,
                        help="month to search for (default: today's month)")
    parser.add_argument('-a', '--all', action = 'store_true', default = False,
                        help='send all entries from the selected day (default: only new ones)')
    
    args = parser.parse_args()
    parse_file(args.filename, args.day, args.month, args.all)

