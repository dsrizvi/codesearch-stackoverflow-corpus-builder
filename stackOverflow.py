import requests
import json
import time
from BeautifulSoup import BeautifulSoup
import html2text
import re
import sqlite3
import json
# client_id 		= '5836'
# client_secret 	= 'AN8VH9S*GiY9j2MpgfE8jw(('
# api_key			= ')HzqRSuw*14xiB8Yc8cgZw(('
# questions_url	= "https://api.stackexchange.com/2.2/questions?key=KEY&page=PAGEorder=desc&pagesize=100&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody&page=PAGENUM"
# answer_url 		= "https://api.stackexchange.com/2.2/questions/QUESTIONID/answers?order=desc&page=sort=activity&site=stackoverflow&filter=withbody"
# https://api.stackexchange.com/2.0/questions?key=)HzqRSuw*14xiB8Yc8cgZw((&pagesize=50&site=stackoverflow&tagged=xpages&order=desc&sort=creation&page=1


def main():

	client_id 			= '5836'
	client_secret 		= 'AN8VH9S*GiY9j2MpgfE8jw(('
	api_key				= ')HzqRSuw*14xiB8Yc8cgZw(('
	questions_url		= "https://api.stackexchange.com/2.2/questions?key={key}&page={page}&order=desc&pagesize=100&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody"
	answer_url 			= "https://api.stackexchange.com/2.2/questions/{question_id}/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody&key=PLACEHOLDER"
	answer_url 			= answer_url.replace("PLACEHOLDER", api_key)

	page 		   		= 1
	requests_remaining  = 10
	questions_url  		= questions_url.format(key=api_key, page=1)


	while requests_remaining > 0:

		questions, requests_remaining	= get_questions(url=questions_url, page=page)
		page 		  	   				+= 1

		# print questions
		if questions:
			answers, requests_remaining  = build_qa(questions=questions,url=answer_url, requests_remaining=requests_remaining)

		time.sleep(30)

def get_questions(url, page):

	url = url.format(page=page)
	response = requests.get(url)

	print "Fetching questions..."

	if 'error_id' in response:
		print "ERROR"
		if response['error_id'] == 502:
			print response
			wait_time = re.findall(r'\d+', response['error_message'])[0]
			print "API limit reached. Sleeping for " + str(wait_time) + 'seconds'
			time.sleep(float(wait_time))
			print "Resuming..."
	else:
		print "Questions fetched."
		questions = response.json()
		return questions['items'], questions['quota_remaining']


def build_qa(url, questions, requests_remaining):

	print "Building QA..."

	qas = []

	for question in questions:
		if question['is_answered']:
			answers_url			= url.format(question_id=str(question['question_id']))
			# answer_url 	   		= url.replace("QUESTIONID", str(question['question_id']))
			requests_remaining -= 1
			# print answers_url
			response = requests.get(answers_url).json()
			print response
			if 'error_id' in response:
				print "ERROR"
				print response
				if response['error_id'] == 502:
					wait_time = re.findall(r'\d+', response['error_message'])[0]
					print "API limit reached. Sleeping for " + str(wait_time) + 'seconds'
					time.sleep(float(wait_time))
					answers = requests.get(answer_url).json()

			if 'error_id' not in response:
				for answer in response['items']:
					if 'error_id' in answer:
						answer = None
						print "ERROR:"
						print answers
						print 'Question id:' + question['id'].encode('utf-8')
						break
					else:
						if answer['is_accepted']:
							answer_body  = answer['body'].encode('utf-8')


							question_id    = answer['question_id']
							question_title = question['title'].encode('utf-8')
							question_body  = question['body'].encode('utf-8')
							question_link  = question['link'].encode('utf-8')

							soup 		  = BeautifulSoup(answer_body)
							code_extract  = soup.findAll('code')
							code_snippets = {}


							print answer_body
							for i in range(len(code_extract)):
								cid 		       = 'so_' + str(i) + '_' + str(question_id) + '.code'
								code 		       = re.search(r'(?<=<code>)(.|\n)*?(?=\<\/code>)', answer_body)
								# code 		       = re.search(r'<code>(.|\n)*?<\/code>', answer_body)
								answer_body 	   = re.sub(r'<code>(.|\n)*?<\/code>', cid, answer_body, 1)

								code_snippets[cid] = code.group(0)

							answer_body = html2text.html2text(answer_body.decode('utf-8'))
							answer_body = answer_body.replace('\n', '<br>')
							qa 			= { 'qid'  		   : question_id,
									   		'question_body' : question_body,
									   		'question_body' : question_title,
								   	   		'question_link' : answers_url,
								      		 'answer_body'   : answer_body,
								      		 'code_snippets' : code_snippets
										}
							qas.append(answer)
							# print answer
							break
			time.sleep(1)

	print "Building QA complete"
	return qa, requests_remaining

def build_html(qas):

	for qa in qas:

		qa = { 	   'qid'  		   : question_id,
				   'question_body' : question_body,
				   'question_body' : question_title,
			   	   'question_link' : answers_url,
			       'answer_body'   : answer_body,
			       'code_snippets' : code_snippets
		}


if __name__ == '__main__':
	main()
