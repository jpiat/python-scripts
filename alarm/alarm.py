#!/usr/bin/env python

DEST_ADDR	= ENTER_THE_DESTINATION_EMAIL_HERE

SMTP_MAIL_SERVER = ENTER_THE_SMTP_ADDRESS_OF_THE_INCOMING_EMAIL
SMTP_MAIL_PORT = ENTER_SMTP_PORT_TO_USE
IMAP_MAIL_SERVER = ENTER_THE_IMAP_ADDRESS_OF_THE_INCOMING_EMAIL
SENDER_ADDR	= ENTER_THE_MAIL_ADDRESS_OF_THE_INCOMING_EMAIL


US_CHANNEL = 2

USERNAME = USER_NAME_FOR_INCOMING_MAIL
PASSWORD = USER_PASSWORD_FOR_INCOMING_MAIL

import smtplib
import sys
import cv
import datetime
import mimetypes
import imaplib
import math
import time
import string
import email

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

def send_mail(title, body, nb_frames):
	now = datetime.datetime.now()
	msg = MIMEMultipart()
	try:
		capture = cv.CaptureFromCAM(0)
		for i in range(nb_frames):
			frame = cv.QueryFrame(capture)
			cv.SaveImage("/tmp/webcam"+str(i)+".jpg", frame)
			time.sleep(1)
	except:
		print "webcam error"
		return
	for i in range(nb_frames):
		fp = open("/tmp/webcam"+str(i)+".jpg", 'rb')
		ctype, encoding = mimetypes.guess_type("/tmp/webcam"+str(i)+".jpg")
		maintype, subtype = ctype.split('/', 1)
		img = MIMEImage(fp.read(), _subtype=subtype)
		img.add_header('Content-Disposition', 'attachment', filename = "webcam"+str(i)+".jpg")
		msg.attach(img)
		fp.close()
	txt = MIMEText(body + str(now))
	msg.preamble = body + str(now)
	msg['Subject'] = title
	msg['From'] = SENDER_ADDR
	msg['To'] = DEST_ADDR
	msg.attach(txt)
	try:
		s = smtplib.SMTP(SMTP_MAIL_SERVER, SMTP_MAIL_PORT)
		s.login(USERNAME, PASSWORD)
		s.sendmail(SENDER_ADDR, DEST_ADDR, msg.as_string())
		s.close()
	except:
		return
	return

def check_mail():
	try:
		m = imaplib.IMAP4(IMAP_MAIL_SERVER)
		m.login(USERNAME, PASSWORD)
		m.select()
		typ, [msgnums] = m.search(None, 'FROM', DEST_ADDR)
		msgnums = msgnums.split(' ')
		print msgnums
		for num in msgnums:
			if len(num) > 0:
				typ, msg_data = m.fetch(num, '(RFC822)')
				m.store(num, '+FLAGS', r'(\Deleted)')
				m.expunge()
				for response_part in msg_data:
					msg = email.message_from_string(response_part[1])
					if string.find(msg['Subject'], "grab") >= 0:
						print "grab !"
						return 1
					elif string.find(msg['Subject'], "disengage") >= 0:
						print "disengage !"
						return 2
					elif string.find(msg['Subject'], "engage") >= 0:
						print "engage !"
						return 3
		m.close()
	except:
		print "connection problem"
	return 0


def readADC(chan):
	anp = open("/sys/devices/platform/atmel_adc/ani"+str(chan), 'rb')
	val = anp.read()
	anp.close()
	return int(val)

def readDistance():
	raw = readADC(US_CHANNEL)
	quantum = 5.0/1023.0
	valv = raw * quantum
	dist = (valv / (5.0/512.0)) * 2.54
	return 	dist

def compute_mean(vals):
	sum = 0.0
	for v in vals :
		sum = sum + v
	return (sum/len(vals))

def shift_list(vals,new_val):
	new_list = vals[1:]
	new_list.append(new_val)
	return new_list
	

def shift_mean(vals, new_val):
	lval = shift_list(vals, new_val)
	m = compute_mean(lval)
	return m, lval

def mean_adc(old_vals):
	new_dist = readDistance()
	m, vals = shift_mean(old_vals, new_dist)
	return m, vals, new_dist


#send_mail("python_test", "capture from cam @ ")
#check_mail()
#readDistance()
engaged = 0
init_vals = [0.0, 0.0, 0.0]
timeout = len(init_vals)
loop_counter = 0
while 1 :
	m, init_vals, dist = mean_adc(init_vals)
	if math.fabs(m-dist) > 20 and timeout == 0 and engaged == 1:
		print init_vals
		send_mail("event !!", "variance of sensor exceded 20cm", 4)
		timeout = len(init_vals) + 2
	else:
		if timeout > 0 :
			timeout = timeout - 1 
	
	if loop_counter >= 5 :
		response = check_mail()
		if response == 1:
			send_mail("grab !", "answer to grab request", 1)
		elif response == 2 :
			engaged = 0
		elif response == 3 :
			engaged = 1
			timeout = len(init_vals)
		loop_counter = 0
	else:	
		loop_counter = loop_counter + 1
	time.sleep(1)
