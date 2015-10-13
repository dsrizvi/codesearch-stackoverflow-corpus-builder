import requests 
import json


request_url = "https://api.stackexchange.com/2.2/questions?order=desc&pagesize=100&sort=activity&tagged=python&site=stackoverflow"


response = requests.get(request_url)
question_data = response.json()

# print question_data['items']
ids = []

for question in question_data['items']:
	# _ids.append(str(question['question_id'])
	# ids.append(str(question['question_id']))
	# if question['is_answered'] == True:
	answer_url = 'https://api.stackexchange.com/2.2/questions/' + str(question['question_id']) + '/answers?order=desc&sort=activity&site=stackoverflow&filter=withbody'
	answer_response = requests.get(answer_url).json()
	with open('output.json', 'w') as outfile:
		json.dump(answer_response, outfile)
	


# ';'.join(ids)


