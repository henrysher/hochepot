#!/usr/local/bin/python


"""
Simple Mail Tool via AWS SES
--------------------------------
@author: 
Allen Wang

@Contributor:
Henry Huang
--------------------------------
"""

import os
import sys
import argparse
import tempfile
from subprocess import call
from boto.ses import SESConnection
from email.mime.text import MIMEText

access_key = ""
secret_key = ""
EDITOR = os.environ.get('EDITOR', 'vim')


def parse_list(cfg):
    with open(cfg, "r") as file:
        names = file.readlines()
    return [name.strip() for name in names]


class mailform(object):

    def __init__(self, senders="", recipients="", subject=""):
        self.senders = senders
        self.recipients = recipients
        self.subject = subject

    def load_content(self, mode=None):
        if mode is True:
            data = 'From:' + ','.join(self.senders) + "\n"
            data += 'To:' + ','.join(self.recipients) + "\n"
            data += 'Subject:' + self.subject + "\n"
            data += sys.stdin.read()
            return data
        else:
            global EDITOR
            global initial_message
            message = initial_message
            with tempfile.NamedTemporaryFile(suffix=".tmp") as tmpfile:
                tmpfile.write(message)
                tmpfile.flush()
                cmd = [EDITOR, tmpfile.name]
                call(cmd)
                return open(tmpfile.name, "r").read()

    def form_msg(self, data=None, mode=None):
        if "\n" in data:
            text = data.split("\n")
            senders_to_string = text[0][5:].strip()
            recipients_to_string = text[1][3:].strip()
            subject_to_string = text[2][8:].strip()
            clean_data = data.replace(text[0], "")
            clean_data = clean_data.replace(text[1], "")
            clean_data = clean_data.replace(text[2], "")
            # FIXME
            if mode is True:
                msg = MIMEText(clean_data, 'plain', 'utf-8')
            else:
                msg = MIMEText(clean_data, 'html', 'utf-8')
            msg['From'] = senders_to_string
            msg['To'] = recipients_to_string
            msg['Subject'] = subject_to_string
            return msg


def send_mail(msg):
    global access_key
    global secret_key

    client = SESConnection(
        aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    senders = msg["From"].split(",")
    recipients = msg["To"].split(',')
    for sender in senders:
        client.send_raw_email(msg.as_string(), sender, recipients)
    client.close()


def main():

    parser = argparse.ArgumentParser(
        description='Simple Mail Tool via AWS SES')
    parser.add_argument('--from', '-f', type=str, default="",
                        dest='senders',
                        help='mail sender: x1@xxx.com,x2@xxx.com')
    parser.add_argument('--to', '-t', type=str, default="",
                        dest='recipients',
                        help='mail recipients: x1@xxx.com,x2@xxx.com')
    parser.add_argument('--from-cfg', '-fc', type=str,
                        dest='cfg_senders',
                        help='config file contains the list of senders')
    parser.add_argument('--to-cfg', '-tc', type=str,
                        dest='cfg_recipients',
                        help='config file contains the list of recipients')
    parser.add_argument('--subj', '-s', type=str, default="",
                        dest='subject',
                        help='mail subject')
    parser.add_argument('--stdin', '-i', action='store_true',
                        dest='stdin',
                        help='use pipe to transfer contents')
    parser.add_argument('--plain', '-p', action='store_true',
                        dest='plain',
                        help='use pipe to transfer contents')
    parser.add_argument('--verbose', '-v', action='store_true',
                        dest='verbose',
                        help='enable debug log')
    parser.add_argument(
        '--version', '-V', action='version', version='SES Sender v0.01')
    args = parser.parse_args()

    if "," in args.senders:
        senders = args.senders(",")
    else:
        senders = [args.senders]
    senders_to_string = args.senders

    if "," in args.recipients:
        recipients = args.recipients.split(",")
    else:
        recipients = [args.recipients]
    recipients_to_string = args.recipients

    if args.cfg_senders is not None:
        senders = parse_list(args.cfg_senders)
        senders_to_string = ','.join(senders)

    if args.cfg_recipients is not None:
        recipients = parse_list(args.cfg_recipients)
        recipients_to_string = ','.join(recipients)
    subject = args.subject

    global initial_message
    initial_message = "From: %s\n" % senders_to_string + \
                      "To: %s\n" % recipients_to_string + \
                      "Subject: %s\n" % subject
    mailf = mailform(senders, recipients, subject)
    data = mailf.load_content(args.stdin)
    msg = mailf.form_msg(data, args.plain)
    send_mail(msg)

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
