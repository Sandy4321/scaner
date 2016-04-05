from scaner.utils import add_metadata
import json
from flask import current_app

# thetopics = {}

# with open('examples/topics.json') as f:
#     temp = json.load(f)
#     thetopics = temp

@add_metadata('topics')
def search(*args, **kwargs):
    search_task = current_app.tasks.topic_search.delay()
    return {'topics': search_task.get(timeout = 10)}, 200 

@add_metadata()
def get(topicId, *args, **kwargs):
    get_task = current_app.tasks.topicdelay(topicId)
    return {'topics': get_task.get(timeout = 10)}, 200 

@add_metadata()
def get_network(*args, **kwargs):
    pass
