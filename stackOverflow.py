from BeautifulSoup import BeautifulSoup
import requests
import time
import html2text
import re
import json
import psycopg2
import HTMLParser
import boto
from boto.s3.connection import S3Connection
from flask import Flask, render_template, request
import os
import urlparse
from celery import Celery
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler('stackoverflow.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = Flask(__name__)
# app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
# app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

app.config.update(BROKER_URL=os.environ['REDIS_URL'],
                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])


celery = Celery(app.name, broker=app.config['BROKER_URL'])
celery.conf.update(app.config)

COUNT = 1


@app.route('/start', methods=['GET', 'POST'])
def index():
	start_page = request.args.get('start_page')
	end_page   = request.args.get('end_page')
	run.delay(start_page,end_page)
	logger.info("Building Corpus...")
	return "Process iniatied"


def s3upload(name, html, bucket):
	logger.info( "  Uploading document to S3.")

	try:
		key = bucket.new_key(name)
		key.set_contents_from_string(html)
	except Exception as e:
		logger.info( "  UPLOAD ERROR:")
		logger.info(e)
	logger.info( "  Documents uploaded.")

def get_questions(url, page):

	# url = url.format(page=page)
	url = url.replace('PAGE', str(page))

	try:
		response = requests.get(url)
	except:
		logger.info( "  Connection refused; sleeping for 600s....")
		time.sleep(600)
		response = requests.get(url)

	logger.info( "Fetching questions...")

	if 'error_id' in response:
		logger.info( "  GET QUESTION ERROR")
		if response['error_id'] == 502:
			logger.info( response)
			wait_time = re.findall(r'\d+', response['error_message'])[0]
			logger.info( "  API limit reached. Sleeping for " + str(wait_time) + 'seconds')
			time.sleep(float(wait_time))
			logger.info( "  Resuming...")
	else:
		logger.info( "Questions fetched.")
		questions = response.json()
		return questions['items'], questions['quota_remaining']


def build_qa(url, questions, requests_remaining, conn, bucket):

	global COUNT

	for question in questions:
		if question['is_answered']:
			answers_url			= url.format(question_id=str(question['question_id']))
			requests_remaining -= 1
			try:
				response = requests.get(answers_url).json()
			except:
				logger.info( "Connection refused; sleeping for 600s")
				time.sleep(600)
				response = requests.get(answers_url).json()

			if 'error_id' in response:
				logger.info( "GET ANSWER ERROR")
				logger.info( response)
				if response['error_id'] == 502:
					wait_time = re.findall(r'\d+', response['error_message'])[0]
					logger.info( "API limit reached. Sleeping for " + str(wait_time) + 'seconds')
					time.sleep(float(wait_time))
					answers = requests.get(answer_url).json()

			if 'error_id' not in response:
				for answer in response['items']:
					if 'error_id' in answer:
						answer = None
						logger.info( "ANSWER ERROR:")
						# logger.info( answers
						logger.info( 'Question id:' + question['id'].encode('utf-8'))
						break
					else:
						try:
							if answer['is_accepted']:
								answer_body  = answer['body'].encode('utf-8')


								question_id    = answer['question_id']
								question_title = question['title'].encode('utf-8')
								question_body  = question['body'].encode('utf-8')
								question_link  = question['link'].encode('utf-8')

								logger.info( '================================================================')
								logger.info( 'Document #' + str(COUNT))
								logger.info( 'Building question ' + str(question_id))


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
								save_code(qa=qa, conn=conn)
								doc_name, html = build_html(qa=qa)
								s3upload(name=doc_name, html=html, bucket=bucket)

								COUNT += 1

								break
						except Exception as e:
							logger.info("ANSWER ERROR:")
							logger.info(e)

			time.sleep(10)

	logger.info( "Building QA complete")
	return requests_remaining

def save_code(qa, conn):
	logger.info( "  Inserting code snippets into database.")

	cursor = conn.cursor()
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
				logger.info( "  DB INSERT ERROR:")
				logger.info( e)
				conn.rollback()

	logger.info( "  Insertion complete")

	return True

def build_html(qa):
	logger.info( "  Building HTML document.")

	template = '''
	<!DOCTYPE html> <html> <body> <h1> {question_title} </h1> <h2> {question_body}  </h2> <h3> {answer_body} </h3> </body> </html>
	'''

	try:
		doc_name 	   = 'so_%s.html' % str(qa['qid'])
		question_title = qa['question_title']
		question_body  = qa['question_body']
		answer_body    = qa['answer_body']
		html = template.format(question_title=question_title, question_body=question_body, answer_body=answer_body)
	except Exception as e:
		logger.info( "HTML BUILD ERROR:")
		logger.info(e)

	logger.info( "  HTML document complete.")

	return doc_name, html

@celery.task
def run(start_page, end_page):

	print "========================================================================="

	so_api_key			=  os.environ['SO_API_KEY']
	questions_url		= 'https://api.stackexchange.com/2.2/questions?key={key}&page=PAGE&order=desc&pagesize=100&sort=votes&min=20&tagged=python&site=stackoverflow&filter=withbody'
	answer_url 			= 'https://api.stackexchange.com/2.2/questions/{question_id}/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody&key=PLACEHOLDER'
	answer_url 			= answer_url.replace('PLACEHOLDER', so_api_key)

	AWSAccessKeyId		= os.environ['AWSAccessKeyId']
	AWSSecretKey		= os.environ['AWSSecretKey']
	s3conn 				= S3Connection(AWSAccessKeyId, AWSSecretKey)
	bucket				= s3conn.get_bucket('code-search-corpus')

	urlparse.uses_netloc.append("postgres")
	url 			= urlparse.urlparse(os.environ["DATABASE_URL"])
	db_name			= url.path[1:]
	db_user			= url.username
	db_password		= url.password
	db_host			= url.hostname
	db_port			= url.port


	# db_name 			= 'so_code'
	# db_user				= 'crawler'
	# db_host				= 'localhost'
	# db_port				=  5432
	# db_password			= 'socrawler'


	conn 				= psycopg2.connect(database=db_name, user=db_user, password=db_password,
										   port=db_port, host=db_host)
	page 		   		= start_page
	questions_url  		= questions_url.format(key=so_api_key, page=1)
	page = start_page


	while start_page >= page and page <= end_page:
		logger.info( "\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n Moving to page " + str(page))
		questions, requests_remaining = get_questions(url=questions_url, page=page)
		page 		  	   			  = page + 1

		if questions:
			requests_remaining  = build_qa(questions=questions,url=answer_url,
										   requests_remaining=requests_remaining,
										   conn=conn, bucket=bucket)

		logger.info( "\nRequests remaining:" + str(requests_remaining))
		time.sleep(10)

	return "Process initiated."




if __name__ == '__main__':
	app.run()
