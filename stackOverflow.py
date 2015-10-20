import requests
import json
import time
from BeautifulSoup import BeautifulSoup
import html2text
import re


request_url = "https://api.stackexchange.com/2.2/questions?order=desc&pagesize=5&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody"


response = requests.get(request_url)
question_data = response.json()

# print question_data['items']
ids = []

for question in question_data["items"]:
	if question['is_answered'] == True:
		answer_url = 'https://api.stackexchange.com/2.2/questions/' + str(question['question_id']) + '/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody'
		time.sleep(1)
		answer_response = requests.get(answer_url).json()
		for answer in answer_response["items"]:
			if answer['is_accepted']:
				# print question["title"].encode('utf-8')
				# print '-----------------------------------'
				# print question['body'].encode('utf-8')
				# print '-----------------------------------'
				# print answer['body'].encode('utf-8')
				# print '==================================='
				question 	  = question["title"].encode('utf-8')
				print question
				if 'body' in question:
					question_body = question['body'].encode('utf-8')

				answer_body	  = answer['body'].encode('utf-8')
				soup 		  = BeautifulSoup(answer_body)
				code_snippets = soup.find('code').getText()
				# print answer_body
				# print soup.getText()
				qid = answer['question_id']

				# for i in range(len(soup.find('code'))):
					# cid = 'so' + str(i) + '_' + str(qid)

				cid = '------------------'
				answer_body = re.sub(r'<code>(.|\n)*?<\/code>', cid, answer_body)
				# answer_body = re.sub(r'<code>([^\n]*?\n+?)+?</code>', cid, answer_body)



				# answer_body = re.sub(r'<code>.*</code>', '', answer_body)
				answer_body = html2text.html2text(answer_body)
				print answer['body'].encode('utf-8')
				print '-----------------------------------'
				print answer_body

				# print answer_body

				# print code_snippets
				print '==================================='


# ';'.join(ids)


