import os
from flask import Flask
from flask import render_template, Response, request
from flask import make_response, redirect, session, url_for
from handlers import request_wants_json
from mongoutils.memex_mongo_utils import MemexMongoUtils
from handlers import hosts_handler, urls_handler, \
get_job_state_handler, schedule_spider_handler, \
discovery_handler, mark_interest_handler, get_screenshot_relative_path
import json
import hashlib
from handlers import set_score_handler
from handlers import list_workspace, add_workspace, set_workspace_selected, delete_workspace
from handlers import list_keyword, save_keyword, schedule_spider_searchengine_handler, list_search_term, save_search_term
from handlers import add_known_urls_handler
from handlers import get_score_handler, train_and_score_mongo
from handlers import list_tags, save_tags, search_tags
from handlers import save_display
from handlers import get_page_number_for_host
from auth import requires_auth
from mongoutils.errors import DeletingSelectedWorkspaceError

from searchengine.pharma.spiders.basesearchengine import BaseSearchEngineSpider
from searchengine.pharma.spiders.google_com import GoogleComSpider

server_path = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
app.config.from_object('settings')
from bson.objectid import ObjectId


class StaticSettings:
    def __init__(self):
        self.page_size = 1


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

# ui
@app.route("/discovery")
@requires_auth
def discovery():

    seeds = discovery_handler()
    for seed in seeds:
        seed["url_hash"] = str(hashlib.md5(seed["url"]).hexdigest())
    return render_template('discovery.html', seeds=seeds)

#http://localhost:5000/back?path=data&current-host=www.ine.mx
#http://localhost:5000/back?path=data&current-host=ine.mx
#http://localhost:5000/back?path=data&filter-field=host&filter-regex=www&current-host=ine.mx
@app.route("/back")
@requires_auth
def back(page=1):

    path = request.args.get('path')                     #mandatory
    current_host = request.args.get('current-host')     #mandatory
    filter_field = request.args.get('filter-field')
    filter_regex = request.args.get('filter-regex')

    redirect_to = path

    if filter_regex and filter_field:
        redirect_to = redirect_to + "?filter-field=" + filter_field + "&filter-regex=" + filter_regex

    # if current_host:
    page_number = get_page_number_for_host(path, StaticSettings().page_size, current_host, filter_field, filter_regex)
    if page_number > 0 :
        redirect_to = redirect_to  + "#page-number=" + str(page_number)


    return redirect(redirect_to, code=302)
    # "data#page-number=2"

@app.route("/data")
@requires_auth
def data(page=1):

    filter_field = request.args.get('filter-field')
    filter_regex = request.args.get('filter-regex')
    current_host = request.args.get('current-host')

    hosts = hosts_handler(page=int(page), page_size=StaticSettings().page_size, current_host=current_host)


    return render_template('data.html', hosts=hosts, which_collection="crawl-data",
                           filter_field = filter_field, filter_regex = filter_regex, use_cc_data=False)

@app.route("/cc-data")
@requires_auth
def cc_data(page=1):

    hosts = hosts_handler(page=int(page), page_size=StaticSettings().page_size, which_collection="cc-crawl-data")

    return render_template('data.html', hosts=hosts, use_cc_data=True)

@app.route("/known-data")
@requires_auth
def known_data(page=1):

    hosts = hosts_handler(page=int(page), page_size=StaticSettings().page_size, which_collection="known-data")

    return render_template('data.html', hosts=hosts, use_known_data=True)

# services
@app.route("/hosts/<page>")
@requires_auth
def load_hosts(page=1):

    filter_field = request.args.get('filter-field')
    filter_regex = request.args.get('filter-regex')

    hosts = hosts_handler(page=int(page) + 1, page_size=StaticSettings().page_size, filter_field = filter_field, filter_regex = filter_regex)
    for host_dic in hosts:
        host_dic["host_hash"] = str(hashlib.md5(host_dic["host"]).hexdigest())
        if "tags" in host_dic:
            host_dic["tags_joined"] = ",".join(host_dic["tags"])

    if request_wants_json():
        return Response(json.dumps(hosts), mimetype="application/json")

    return render_template('hosts.html', hosts=hosts, use_cc_data=False, page = page)

@app.route("/cc-hosts/<page>")
@requires_auth
def cc_load_hosts(page=1):

    hosts = hosts_handler(page=int(page) + 1, page_size=StaticSettings().page_size, which_collection="cc-crawl-data")

    if request_wants_json():
        return Response(json.dumps(hosts), mimetype="application/json")

    return render_template('hosts.html', hosts=hosts, which_collection="cc-crawl-data", use_cc_data=True)

@app.route("/known-hosts/<page>")
@requires_auth
def known_load_hosts(page=1):

    hosts = hosts_handler(page=int(page) + 1, page_size=StaticSettings().page_size, which_collection="known-data")

    if request_wants_json():
        return Response(json.dumps(hosts), mimetype="application/json")

    return render_template('hosts.html', hosts=hosts, which_collection="known-data", use_known_data=True)

@app.route("/urls")
@app.route("/urls/<host>")
@requires_auth
def urls(host=None):

    urls = urls_handler(host)
    if request_wants_json():
        return Response(json.dumps(urls), mimetype="application/json")

    # !super hacky
    for url_dic in urls:
        screenshot_path = url_dic.get("screenshot_path")
        if screenshot_path:
            url_dic["screenshot_path"] = get_screenshot_relative_path(screenshot_path)
        url_dic["url_hash"] = str(hashlib.md5(url_dic["url"]).hexdigest())

    return render_template("urls.html", urls=urls)

@app.route("/cc-urls")
@app.route("/cc-urls/<host>")
@requires_auth
def cc_urls(host=None):

    urls = list(urls_handler(host, which_collection="cc-crawl-data"))
    if request_wants_json():
        return Response(json.dumps(urls), mimetype="application/json")

    # change this
    return render_template("urls.html", urls=urls, use_cc_data=True)

@app.route("/known-urls")
@app.route("/known-urls/<host>")
@requires_auth
def known_urls(host=None):

    urls = list(urls_handler(host, which_collection="known-data"))
    if request_wants_json():
        return Response(json.dumps(urls), mimetype="application/json")

    # change this
    return render_template("urls.html", urls=urls, use_known_data=True)

@app.route("/add-known", methods = ['GET', 'POST'])
@requires_auth
def add_known_urls():

    if request.method == 'POST':
        urls_raw = json.loads(request.data)[0]
        add_known_urls_handler(urls_raw)
        return Response(json.dumps({}), mimetype="application/json")

    else:
        return render_template("known.html")

@app.route("/schedule-spider/")
@requires_auth
def schedule_spider():

    url = request.args.get('url')
    schedule_spider_handler(url)
    return Response("OK")

@app.route("/url-job-state/")
@requires_auth
def get_spider_update():

    url = request.args.get('url')
    state = get_job_state_handler(url)

    return str(state)

@app.route("/mark-interest/<interest>/")
@requires_auth
def mark_interest(interest):

    url = request.args.get('url')
    print url

    if interest.strip().lower() == "false":
        interest = False

    elif interest.strip().lower() == "true":
        interest = True

    else:
        raise Exception("Interest must be either true or false")

    ret = mark_interest_handler(interest, url)
    return Response("OK")

@app.route("/set-score/<score>/")
@requires_auth
def set_score(score):

    url = request.args.get('url')
    ret = set_score_handler(url, score)

    return Response("OK")

############# TAGS #############

@app.route("/api/tags/<term>" , methods=['GET'])
@requires_auth
def api_search_term(term):
    in_doc = search_tags(term)
    if in_doc == None:
        return Response("{}", mimetype="application/json")
    else:
        out_doc = JSONEncoder().encode(in_doc)
        return Response(json.dumps(out_doc), mimetype="application/json")

#upsert_tags_to_hosts
@app.route("/api/tags/<host>", methods=['PUT'])
@requires_auth
def api_save_tags(host):
    tags = request.json
    save_tags(host, tags)

    in_doc = list_tags(host)
    if in_doc == None:
        return Response("{}", mimetype="application/json")
    else:
        out_doc = JSONEncoder().encode(in_doc)
        return Response(json.dumps(out_doc), mimetype="application/json")

############# /host Hosts #############
@app.route("/api/host/display/<host>", methods=['PUT'])
@requires_auth
def api_save_display(host):
    data = request.json
    displayable = data['display']
    save_display(host, displayable)
    return Response("{}", mimetype="application/json")

############# Workspaces #############
@app.route("/")
@app.route("/workspace/" , methods=['GET'])
@requires_auth
def get_workspace_view():
    return render_template("workspace.html")


@app.route("/api/workspace/", methods=['GET'])
@requires_auth
def get_workspace_api():
    in_doc = list_workspace()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")


@app.route("/api/workspace/<name>/", methods=['PUT'])
@requires_auth
def add_workspace_api(name):
    add_workspace(name)

    in_doc = list_workspace()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")

@app.route("/api/workspace/selected/<id>/", methods=['PUT'])
@requires_auth
def selected_workspace_api(id):
    set_workspace_selected(id)

    in_doc = list_workspace()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")

@app.route("/api/workspace/<id>/", methods=['DELETE'])
@requires_auth
def delete_workspace_api(id):
    try:
        delete_workspace(id)
    except DeletingSelectedWorkspaceError:
        ui_response = '{"error":"Is not allowed to delete the workspace while it is selected."}'
        return Response(json.dumps(ui_response), mimetype="application/json")

    in_doc = list_workspace()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")

############# Keywords #############

@app.route("/keyword/" , methods=['GET'])
@requires_auth
def get_keyword_view():
    return render_template("keyword.html")

@app.route("/api/keyword/", methods=['GET'])
@requires_auth
def get_keyword_api():
    in_doc = list_keyword()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")


@app.route("/api/keyword/", methods=['PUT'])
@requires_auth
def save_keyword_api():
   # print(request)
   # keywords = request.data
   # print("keywords:" + keywords)
    keywords = request.json
   # print(_json)

    save_keyword(keywords)

    in_doc = list_keyword()
    if in_doc == None:
        out_doc = JSONEncoder().encode(in_doc)
        return Response("{}", mimetype="application/json")
    else:
        out_doc = JSONEncoder().encode(in_doc)

        return Response(json.dumps(out_doc), mimetype="application/json")

@app.route("/api/fetch-keyword/", methods=['POST'])
@requires_auth
def fetch_keyword_api():
    #url = request.args.get('keywords')
    keywords = request.json
    #schedule_spider_handler(url)
    schedule_spider_searchengine_handler(keywords)
    return Response("OK")

########## Search Terms ################
@app.route("/searchterm/" , methods=['GET'])
@requires_auth
def get_search_term_view():
    return render_template("searchterm.html")

@app.route("/api/searchterm/", methods=['GET'])
@requires_auth
def get_search_term_api():
    in_doc = list_search_term()
    out_doc = JSONEncoder().encode(in_doc)
    return Response(json.dumps(out_doc), mimetype="application/json")

@app.route("/api/searchterm/", methods=['PUT'])
@requires_auth
def save_search_term_api():
    search_terms = request.json
    save_search_term(search_terms)

    in_doc = list_search_term()
    if in_doc == None:
        out_doc = JSONEncoder().encode(in_doc)
        return Response("{}", mimetype="application/json")
    else:
        out_doc = JSONEncoder().encode(in_doc)

        return Response(json.dumps(out_doc), mimetype="application/json")

@app.route("/api/fetch-searchterm/", methods=['POST'])
@requires_auth
def fetch_search_terms_api():
    search_terms = request.json
    #schedule_spider_handler(url)
    search_terms = ",".join(search_terms)
    schedule_spider_searchengine_handler(search_terms)
    return Response(json.dumps({}), mimetype="application/json")

################ SCORING #########################
@app.route("/score", methods = ["GET"])
@requires_auth
def get_scoring_page():

    if request.method == "GET":
        yes_interest_docs, no_interest_docs = get_score_handler()

        return render_template('score.html', num_yes_interest = len(yes_interest_docs), num_no_interest = len(no_interest_docs))

@app.route("/api/rescore", methods = ["POST"])
@requires_auth
def start_ranker():

    if request.method == "POST":
        train_and_score_mongo()
        return Response("{}", mimetype="application/json")

if __name__ == "__main__":

    if app.config["INIT_DB_ON_START"]:
        MemexMongoUtils(init_db=True)

    if app.config['DEBUG']:
        app.debug = True

    app.run('0.0.0.0', threaded=True)
