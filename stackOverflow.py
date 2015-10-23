from BeautifulSoup import BeautifulSoup
import requests
import json
import time
import html2text
import re
import json
import psycopg2
import HTMLParser
import boto
from boto.s3.connection import S3Connection
from flask import Flask, render_template
import os
import urlparse

app = Flask(__name__)

# client_id 		= '5836'
# client_secret 	= 'AN8VH9S*GiY9j2MpgfE8jw(('
# api_key			= ')HzqRSuw*14xiB8Yc8cgZw(('
# questions_url	= "https://api.stackexchange.com/2.2/questions?key=KEY&page=PAGEorder=desc&pagesize=100&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody&page=PAGENUM"
# answer_url 		= "https://api.stackexchange.com/2.2/questions/QUESTIONID/answers?order=desc&page=sort=activity&site=stackoverflow&filter=withbody"
# https://api.stackexchange.com/2.0/questions?key=)HzqRSuw*14xiB8Yc8cgZw((&pagesize=50&site=stackoverflow&tagged=xpages&order=desc&sort=creation&page=1

@app.route('/', methods=['GET', 'POST'])
def index():

	so_client_id 		= '5836'
	so_client_secret 	= 'AN8VH9S*GiY9j2MpgfE8jw(('
	so_api_key			= ')HzqRSuw*14xiB8Yc8cgZw(('
	questions_url		= 'https://api.stackexchange.com/2.2/questions?key={key}&page={page}&order=desc&pagesize=100&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody'
	answer_url 			= 'https://api.stackexchange.com/2.2/questions/{question_id}/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody&key=PLACEHOLDER'
	answer_url 			= answer_url.replace('PLACEHOLDER', so_api_key)

	AWSAccessKeyId		= 'AKIAIY5TKK65FZKGMINQ'
	AWSSecretKey		= 'bi09nM0zDV7thpNUNcEpl/r89g4kidKvvny5071q'
	s3conn 				= S3Connection(AWSAccessKeyId, AWSSecretKey)
	bucket				= s3conn.get_bucket('code-search-corpus')
	print "a"
	urlparse.uses_netloc.append("postgres")
	db_url = urlparse.urlparse(os.environ["DATABASE_URL"])
	db_name=url.path[1:]
	db_password=url.username
	password=url.password
	db_host=url.hostname
	db_port=url.port



	# db_name 			= 'so_code'
	# db_user				= 'crawler'
	# db_host				= 'localhost'
	# db_port				= 5432
	# db_password			= 'socrawler'
	print '0'
	conn 				= psycopg2.connect(dbname=db_name, user=db_user, password=db_password, port=db_port, host=db_host)
	print conn
	print "1"
	page 		   		= 1
	requests_remaining  = 1
	questions_url  		= questions_url.format(key=so_api_key, page=1)
	print "2"

	while requests_remaining > 0:
		print "3"
		questions, requests_remaining = get_questions(url=questions_url, page=page)
		page 		  	   			  += 1

		# print questions
		if questions:
			qas, requests_remaining  = build_qa(questions=questions,url=answer_url, requests_remaining=requests_remaining)
			print "4"
			if len(questions) > 0:
				print "5"
				save_code(qas=qas, conn=conn)
				docs = build_html(qas)
				print docs
				s3upload(docs, bucket)

		print "\nRequests remaining:" + str(requests_remaining)
		time.sleep(30)

	return "Process initiated."

def s3upload(docs, bucket):
	print "Uploading documents to S3."

	for doc in docs:

		try:
			key = bucket.new_key(doc[0])
			key.set_contents_from_string(doc[1])
		except Exception as e:
			print "UPLOAD ERROR:"
			print e
	print "Documents uploaded."

def get_questions(url, page):

	url = url.format(page=page)
	response = requests.get(url)

	print "Fetching questions..."

	if 'error_id' in response:
		print "GET QUESTION ERROR"
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
			requests_remaining -= 1
			response = requests.get(answers_url).json()

			if 'error_id' in response:
				print "GET ANSWER ERROR"
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
						print "ANSWER ERROR:"
						# print answers
						print 'Question id:' + question['id'].encode('utf-8')
						break
					else:
						try:
							if answer['is_accepted']:
								answer_body  = answer['body'].encode('utf-8')


								question_id    = answer['question_id']
								question_title = question['title'].encode('utf-8')
								question_body  = question['body'].encode('utf-8')
								question_link  = question['link'].encode('utf-8')

								soup 		  = BeautifulSoup(answer_body)
								code_extract  = soup.findAll('code')
								code_snippets = {}

								h= HTMLParser.HTMLParser()
								for i in range(len(code_extract)):
									cid 		       = 'so_' + str(i) + '_' + str(question_id) + '.code'
									code 		       = re.search(r'(?<=<code>)(.|\n)*?(?=\<\/code>)', answer_body).group(0)
									answer_body 	   = re.sub(r'<code>(.|\n)*?<\/code>', cid, answer_body, 1)
									code 		       = h.unescape(code)
									code_snippets[cid] = code.replace("'", '"')

								answer_body = html2text.html2text(answer_body.decode('utf-8'))
								answer_body = answer_body.replace('\n', '<br>')

								qa 			= { 'qid'  		     : question_id,
										   		'question_body'  : question_body,
										   		'question_title' : question_title,
									   	   		'question_link'  : question_link,
									      		'answer_body'    : answer_body,
									      		'code_snippets'  : code_snippets
											}
								qas.append(qa)
								break
						except Exception as e:
							print "ANSWER ERROR:"
							print e
			# break
			time.sleep(1)

	print "Building QA complete"
	return qas, requests_remaining

def save_code(qas, conn):
	print "Inserting code snippets into database."

	cursor = conn.cursor()
	for qa in qas:
		qid  = qa['qid']
		link = qa['question_link']

		for cid, code in qa['code_snippets'].iteritems():
			cursor.execute("SELECT EXISTS(SELECT 1 FROM code_snippets where cid=%s)", [cid])
			exists = cursor.fetchall()[0][0]

			if not exists:
				try:
					cursor.execute("INSERT INTO code_snippets(cid, qid, link, code) VALUES (%s, %s, E%s, E%s)", \
									[cid, qid, link, code])
					conn.commit()
				except Exception as e:
					print "DB INSERT ERROR:"
					print e

	print "Insertion complete"

def build_html(qas):
	print "Building HTML documents."

	docs = list()
	template = '''
	<!DOCTYPE html> <html> <body> <h1> {question_title} </h1> <h2> {question_body}  </h2> <h3> {answer_body} </h3> </body> </html>
	'''
	for qa in qas:
		try:
			print qa
			doc_name 	   = 'so_%s.html' % str(qa['qid'])
			question_title = qa['question_title']
			question_body  = qa['question_body']
			answer_body    = qa['answer_body']

			html = template.format(question_title=question_title, question_body=question_body, answer_body=answer_body)
			docs.append((doc_name, html))
		except Exception as e:
			print "HTML BUILD ERROR:"
			print e

	print "HTML documents complete."

	return docs


if __name__ == '__main__':
	app.run()
