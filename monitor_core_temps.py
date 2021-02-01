#!/usr/bin/env python

# monitor_core_temps.py: Run the 'sensors' command to get overall CPU and 
# individual core temperatures. Write them to csv file and create daily
# plots. If a given maximum temperature is exceeded, an email is sent
# to root.
# This script is typically run as a cron job by root, at least hourly.
#
# Author: Hartmut Frenzel, School of Oceanography, University of Washington
#
# First version: June 9, 2017

import argparse
import datetime
import time 
import os.path
import subprocess
import re
import csv
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import smtplib
from email.message import EmailMessage


def check_directory(path):
    '''Check if a directory with the given path exists. If not, create it.
    PermissionError exception is raised if this can't be done by user
    invoking the script.
    '''
    if not os.path.exists(path):
        os.mkdir(path, mode=0o700) # access for owner only

def open_output_file(fn_out, num_cpus, num_cores):
    '''Create a new output file if it doesn't exist yet, otherwise open
    the existing one. Determine current time and write it to the file.
    Return the file handle.'''
    if not os.path.exists(fn_out):
        f = open(fn_out, 'w+')
        f.write('hour,min,tot_min,')
        for cpu in range(0, num_cpus):
            f.write('cpu{0:d}'.format(cpu))
            for core in range(0, num_cores):
                f.write(',cpu{0:d}_c{1:d}'.format(cpu, core))
            if cpu < num_cpus-1:
                f.write(',')
            else:
                f.write('\n')
    else:
        f = open(fn_out, 'a')
    # determine current time, write it to the file
    hour = int(time.strftime('%H'))
    min = int(time.strftime('%M'))
    tot_min = hour * 60 + min
    # this is only the first part of line, don't end it with \n :
    f.write('{0:d},{1:d},{2:d}'.format(hour, min, tot_min) )
    return f

def analyze_output_sensors(f, temp_limit):
    '''Run the 'sensors' command, determine CPU and core temperatures,
    write them to the output file with given file handle f.
    Return a string with temperatures over the given temp_limit (empty if none),
    and all output of the 'sensors' command.'''
    output_sensors = subprocess.getoutput('sensors')
    output_lines = output_sensors.split('\n')
    problems = ''
    for line in output_lines:
        matchObj = re.match( r'(.*:)\s+\+([0-9\.]+)', line)
        if matchObj:
            temp = float(matchObj.group(2))
            f.write(',{0:.1f}'.format(temp))
            if temp > temp_limit:
                problems += '{0:s} {1:.1f} dg C\n'.format(matchObj.group(1),
                                                          temp)

    f.write('\n') # write one line per invocation of script
    f.close()
    return (problems, output_lines)

def read_csv(fn):
    '''Read the csv file that was created by this script and
    return its content as a numpy array.'''
    with open(fn, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader) # header line can be discarded
        data_line = []
        for row in reader:
            data_line.append( [float(x) for x in row if x != ''] )

    return np.array(data_line)

def make_plot(fn_out, date_str, path, num_cpus, num_cores):
    '''Read temperature data from given output file, create a png
    plot and save it (without showing it).'''
    data = read_csv(fn_out)
    x = data[:,2] # total time in minutes

    plt.xticks(range(0,60*24,60),range(24))
    for cpu in range(num_cpus):
        plt.plot(x, data[:,3+num_cores*cpu], color='black',linewidth=2)
        for core in range(num_cores):
            plt.plot(x, data[:,4+num_cores*cpu+core], color='gray')

    plt.xlim(0,1440)   # minutes of the day
    plt.title('CPU and core temperatures for {0:s}'.format(date_str))
    plt.xlabel('Hour')
    plt.ylabel('Temperature')
    fn_png = '{0:s}/core_temps_{1:s}.png'.format(path,date_str.replace('-','_'))
    plt.savefig(fn_png)

def get_current_load():
    '''Get output from the 'top' command and parse it to get the current
    load. Also get the current top 5 processes.
    Return a message string.'''
    top_line1 = subprocess.getoutput('top -b | head -1')
    matchObj = re.match(r'.*load average: ([\d\.]+),.*', top_line1)
    if matchObj:
        load = '\nCurrent load: ' + str(matchObj.group(1))
    else:
        load = top_line1
    load += '\n\nThe top 5 processes are:\n'
    load += subprocess.getoutput('top -b | head -12|tail -6')
    return load

def send_email(output, address):
    '''
    Sends an email with 'output' in the body to 'address'.
    '''
    hostname = subprocess.getoutput('hostname -s')
    msg = EmailMessage()
    msg.set_content(output)
    msg['Subject'] = '{0:s} overheating'.format(hostname)
    msg['From'] = 'system@{0:s}'.format(hostname)
    msg['To'] = address

    # Send the message via the local SMTP server
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

def parse_input_args():
    '''Parse the command line arguments and return them as object.'''
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', '--cpus', default=2, type=int,
                        help='Number of CPUs (default: 2)')
    parser.add_argument('-c', '--cores', default=8, type=int,
                        help='Number of cores per CPU (default: 8)')
    parser.add_argument('-p', '--path', default='/var/log/temperature',
                        help='Directory for output files (default: /var/log/temperature)')
    parser.add_argument('-w', '--warn_level', default=63, type=int,
                        help='Temperature that triggers a warning (default: 63)')
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_input_args()

    # get today's date and current time
    today = time.strftime('%d%m%Y')

    # create output directory if needed
    check_directory(args.path)

    # determine the name of the output file
    fn_out = '{0:s}/temp_{1:s}.csv'.format(args.path, today)
    f = open_output_file(fn_out, args.cpus, args.cores)

    # run sensors command, write values to file
    (high_temps, output_lines) = analyze_output_sensors(f, args.warn_level)

    # make a plot
    make_plot(fn_out, str(datetime.date.today()), args.path, args.cpus,
              args.cores)

    # send warning email to root if limit is exceeded
    if len(high_temps):
        load = get_current_load()
        send_email(high_temps + load, 'root')
