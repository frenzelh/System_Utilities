#!/usr/bin/env python3
#
# This script checks if any of the compute nodes went down.
# Requires the Bright Computing tools (cmsh).
#
# Author: H Frenzel, School of Oceanography, University of Washington
# hfrenzel@uw.edu
#
# First version: August 13, 2018


# Import subprocess for the shell command
import subprocess

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.message import EmailMessage


def get_status():
    """
    Runs shell command "echo device status | cmsh" and returns
    its output.
    """

    p1 = subprocess.Popen(["echo", "device", "status"],
                          stdout=subprocess.PIPE)
    output = subprocess.check_output('/cm/local/apps/cmd/bin/cmsh', 
                                     stdin=p1.stdout).decode("utf-8") 
    return output

def check_status(output):
    """
    Checks if lines in output do not have "UP" in it.
    Returns those lines.
    """

    lines = output.split('\n')
    problems = ''
    for line in lines:
        if len(line) > 0 and not 'device status' in line:
            if not 'UP' in line:
                print(line)
                problems += line + '\n'
    return problems            

def send_email(output, address):
    """
    Sends an email with "output" in the body to "address".
    """

    msg = EmailMessage()
    msg.set_content(output)
    msg['Subject'] = 'server nodes down'
    msg['From'] = 'system@server'
    msg['To'] = address
    
    # Send the message via our own SMTP server.
    s = smtplib.SMTP('localhost')
    s.send_message(msg)
    s.quit()

if __name__ == '__main__':
    """
    Main program: checks status, looks for problems, sends an
    email to root if there are any.
    """

    output = get_status()
    problems = check_status(output)
    if len(problems):
        send_email(problems, 'root')
