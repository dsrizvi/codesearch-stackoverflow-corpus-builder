import requests 
import json
import time

request_url = "https://api.stackexchange.com/2.2/questions?order=desc&pagesize=5&sort=votes&min=20&tagged=python&site=stackoverflow"


response = requests.get(request_url)
question_data = response.json()

# print question_data['items']
ids = []

for question in question_data["items"]:
	if question['is_answered'] == True:
		print question["title"]
		answer_url = 'https://api.stackexchange.com/2.2/questions/' + str(question['question_id']) + '/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody'
		time.sleep(31)
		answer_response = requests.get(answer_url).json()
		for answer in answer_response["items"]:
			if 'body' in answer:
				print answer['body']
			
		


# ';'.join(ids)


