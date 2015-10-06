import requests 
import json


url = "https://api.stackexchange.com/2.2/questions?order=desc&sort=activity&site=stackoverflow"


response = requests.get(url)
data = json.loads(response.content)

with open('output.json', 'w') as outfile:
	json.dump(data, outfile)
