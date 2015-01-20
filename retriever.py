#!/usr/bin/python

"""
The MIT License (MIT)

Copyright (c) 2014 WikiTeams.pl

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import urllib
import csv
import random
import scream
import json
import requests
import cStringIO
import subprocess
import threading
import codecs
import time
import os
import argparse
from github import Github, UnknownObjectException, GithubException
# import ElementTree based on the python version
try:
    import elementtree.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
try:
    import MySQLdb as MSQL
except ImportError:
    import _mysql as MSQL


version_name = 'Version 1.01 codename: Ducky duck'
openhub_query_tags = None
force_csv_append = None
pagination = 10
NullChar = 'NaN'
sleepy_head_time = 25

# don't forget to provide api key as first arg of python script
results_done = 0
results_all = 8420  # checked manually, hence its later overwritten
# page = 0
timeout = 50


def is_win():
    return sys.platform.startswith('win')


def parse_number(s):
    return int(float(s))


def num_modulo(thread_id_count__):
    global no_of_threads
    return thread_id_count__ % pagination


def return_random_openhub_key():
    global openhub_secrets
    return random.choice(openhub_secrets).strip()


def freeze(message):
    global sleepy_head_time
    scream.log_warning('Sleeping for ' + str(sleepy_head_time) + ' seconds. Reason: ' + str(message), True)
    time.sleep(sleepy_head_time)


class WriterDialect(csv.Dialect):
    strict = True
    skipinitialspace = True
    quoting = csv.QUOTE_MINIMAL
    delimiter = ','
    escapechar = '\\'
    quotechar = '"'
    lineterminator = os.linesep


class WriterDialectQuoteAll(csv.Dialect):
    strict = True
    skipinitialspace = True
    quoting = csv.QUOTE_ALL
    delimiter = ';'
    escapechar = '\\'
    quotechar = '"'
    lineterminator = os.linesep


class Stack:
    def __init__(self):
        self.__storage = []

    def isEmpty(self):
        return len(self.__storage) == 0

    def push(self, p):
        self.__storage.append(p)

    def pop(self):
        return self.__storage.pop()


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and re-encodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=WriterDialect, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class GeneralGetter(threading.Thread):

    finished = False
    page = None
    conn = None

    def __init__(self, threadId, page):
        scream.say('Initiating GeneralGetter, running __init__ procedure.')
        self.threadId = threadId
        threading.Thread.__init__(self)
        self.daemon = True
        self.finished = False
        self.page = page
        self.conn = MSQL.connect(host="10.4.4.3", port=3306, user=open('mysqlu.dat', 'r').read(),
                                 passwd=open('mysqlp.dat', 'r').read(), db="github", connect_timeout=50000000)

    def run(self):
        scream.cout('GeneralGetter thread(' + str(self.threadId) + ')' + 'starts working on OpenHub page ' + str(self.page))
        self.finished = False
        self.get_data(self.page, self.conn)

    def is_finished(self):
        return self.finished if self.finished is not None else False

    def set_finished(self, finished):
        scream.say('Marking the thread ' + str(self.threadId) + ' as finished..')
        self.finished = finished

    def cleanup(self):
        scream.say('Marking thread on ' + str(self.threadId) + "/" + str(self.page) + ' as definitly finished..')
        self.finished = True
        try:
            self.conn.close()
        except:
            scream.log('MySQL connection instance already closed. Ok.')
        scream.say('Terminating/join() thread on ' + str(self.threadId) + ' ...')
        #self.join()

    def get_data(self, page, conn):
        global results_done
        global results_all
        global pagination
        global openhub_query_tags

        self.params_sort_rating = urllib.urlencode({'query': 'tag:' + openhub_query_tags[0], 'api_key': return_random_openhub_key(),
                                                    'sort': 'rating', 'page': page})
        self.projects_api_url = "https://www.openhub.net/projects.xml?%s" % (self.params_sort_rating)

        self.result_flow = urllib.urlopen(self.projects_api_url)

        scream.say('')
        scream.say('-------------------------- PAGE ' + str(page) + ' parsed -----------------------------')
        scream.say('')

        # Parse the response into a structured XML object
        self.tree = ET.parse(self.result_flow)

        # Did Ohloh return an error?
        self.elem = self.tree.getroot()
        self.error = self.elem.find("error")
        if self.error is not None:
            print 'OpenHub returned ERROR:', ET.tostring(self.error),
            sys.exit()

        results_done += int(self.elem.find("items_returned").text)
        results_all = int(self.elem.find("items_available").text)

        self.i = 0
        for self.node in self.elem.findall("result/project"):
            self.i += 1
            scream.say('Checking element ' + str(self.i) + '/' + str(pagination))

            self.project_id = self.node.find("id").text
            self.project_name = self.node.find("name").text
            self.project_url = self.node.find("url").text
            self.project_htmlurl = self.node.find("html_url").text
            self.project_created_at = self.node.find("created_at").text
            self.project_updated_at = self.node.find("updated_at").text
            self.project_homepage_url = self.node.find("homepage_url").text

            self.project_average_rating = self.node.find("average_rating").text
            self.project_rating_count = self.node.find("rating_count").text
            self.project_review_count = self.node.find("review_count").text

            self.project_activity_level = self.node.find("project_activity_index/value").text

            self.project_user_count = self.node.find("user_count").text

            # project may have multiple GitHub repositories
            # or even it may be not present on GitHub - check that

            self.is_github_project = False
            self.github_repo_id = None

            # in case of multiple github CODE repositories (quite often)
            # treat as a seperate repo - remember, we focus on github repositories, not aggregates

            self.enlistments_detailed_params = urllib.urlencode({'api_key': return_random_openhub_key()})
            self.enlistments_detailed_url = "https://www.openhub.net/projects/%s/enlistments.xml?%s" % (self.project_id, self.enlistments_detailed_params)

            self.enlistments_result_flow = urllib.urlopen(self.enlistments_detailed_url)

            # Parse the response into a structured XML object
            self.enlistments_tree = ET.parse(self.enlistments_result_flow)

            # Did Ohloh return an error?
            self.enlistments_elem = self.enlistments_tree.getroot()
            self.enlistments_error = self.enlistments_elem.find("error")
            if self.enlistments_error is not None:
                print 'Ohloh returned:', ET.tostring(self.enlistments_error),
                sys.exit()

            self.repos_lists = list()

            for self.enlistment_node in self.enlistments_elem.findall("result/enlistment"):
                self.ee_type = self.enlistment_node.find("repository/type").text
                if (self.ee_type == "GitRepository"):
                    self.ee_link = self.enlistment_node.find("repository/url").text
                    if (self.ee_link.startswith("git://github.com/")):
                        scream.say('Is a GitHub project!')
                        self.is_github_project = True
                        self.github_repo_id = self.ee_link.split("git://github.com/")[1].split(".git")[0]
                        scream.say(self.github_repo_id)
                        self.repos_lists.append(self.github_repo_id)

            if not self.is_github_project:
                continue

            # now lets get even more sophisticated details
            self.params_detailed_url = urllib.urlencode({'api_key': return_random_openhub_key()})
            self.project_detailed_url = "https://www.openhub.net/projects/%s.xml?%s" % (self.project_id, self.params_detailed_url)  # how come here was a typo ?

            self.detailed_result_flow = urllib.urlopen(self.project_detailed_url)

            # Parse the response into a structured XML object
            self.detailed_tree = ET.parse(self.detailed_result_flow)

            # Did Ohloh return an error?
            self.detailed_elem = self.detailed_tree.getroot()
            self.detailed_error = self.detailed_elem.find("error")
            if self.detailed_error is not None:
                print 'Ohloh returned:', ET.tostring(self.detailed_error),
                sys.exit()

            self.twelve_month_contributor_count = self.detailed_elem.find("result/project/analysis/twelve_month_contributor_count").text
            self.total_contributor_count = self.detailed_elem.find("result/project/analysis/total_contributor_count").text
            self.twelve_month_commit_count = self.detailed_elem.find("result/project/analysis/twelve_month_commit_count")
            self.twelve_month_commit_count = self.twelve_month_commit_count.text if self.twelve_month_commit_count is not None else NullChar
            self.total_commit_count = self.detailed_elem.find("result/project/analysis/total_commit_count")
            self.total_commit_count = self.total_commit_count.text if self.total_commit_count is not None else NullChar
            self.total_code_lines = self.detailed_elem.find("result/project/analysis/total_code_lines")
            self.total_code_lines = self.total_code_lines.text if self.total_code_lines is not None else NullChar
            self.main_language_name = self.detailed_elem.find("result/project/analysis/main_language_name")
            self.main_language_name = self.main_language_name.text if self.main_language_name is not None else NullChar

            self.current_ghc = github_clients[num_modulo(self.i-1)]
            self.current_ghc_desc = github_clients_ids[num_modulo(self.i-1)]

            print 'Now using github client id: ' + str(self.current_ghc_desc)

            for self.gh_entity in self.repos_lists:

                try:
                    self.repository = self.current_ghc.get_repo(self.gh_entity)
                    self.repo_name = self.repository.name
                    self.repo_full_name = self.repository.full_name
                    self.repo_html_url = self.repository.html_url
                    self.repo_stargazers_count = self.repository.stargazers_count
                    self.repo_forks_count = self.repository.forks_count
                    self.repo_created_at = self.repository.created_at
                    self.repo_is_fork = self.repository.fork
                    self.repo_has_issues = self.repository.has_issues
                    self.repo_open_issues_count = self.repository.open_issues_count
                    self.repo_has_wiki = self.repository.has_wiki
                    self.repo_network_count = self.repository.network_count
                    self.repo_pushed_at = self.repository.pushed_at
                    self.repo_size = self.repository.size
                    self.repo_updated_at = self.repository.updated_at
                    self.repo_watchers_count = self.repository.watchers_count

                    # Now its time to get the list of developers!

                    # yay! rec-09 mysql instance is visible from the yoshimune computer !
                    # ok, but I forgot github blacklisted our comptuing clusters
                    # make sure your local win machine runs it..
                    # just pjatk things.. carry on

                    scream.say('Retrieving the project id from mysql database.. should take max 1 second.')

                    # Get here project id used in the database !
                    #conn.ping(True)
                    self.cursor = conn.cursor()
                    self.cursor.execute(r'select distinct id from (select * from projects where `name`="{0}") as p where url like "%{1}"'.format(self.repo_name, self.repo_full_name))
                    self.rows = self.cursor.fetchall()

                    try:
                        self.repo_db_id = self.rows[0]
                    except:
                        #print str(cursor.info())
                        # this is too new repo , because it is not found on mysql db, skip it !
                        continue
                        #print 'Faulty query was: -------- '
                        #print r'select distinct id from (select * from projects where `name`="{0}") as p where url like "%{1}"'.format(self.repo_name, self.repo_full_name)

                    scream.say('project id retrieved from database is: ' + str(self.repo_db_id))

                    self.cursor.close()

                    #conn.ping(True)
                    self.cursor = conn.cursor()
                    # Now get list of GitHub logins which are project_members !
                    self.cursor.execute(r'SELECT login FROM project_members INNER JOIN users ON users.id = project_members.user_id WHERE repo_id = %s' % self.repo_db_id)
                    self.project_developers = self.cursor.fetchall()

                    self.project_developers = [i[0] for i in self.project_developers]  # unzipping tuples in tuples
                    self.contributors_count = len(self.project_developers)

                    self.cursor.close()
                    #conn.close()

                    for self.project_developer in self.project_developers:

                        # create a GitHub user named object for GitHub API
                        self.current_user = self.current_ghc.get_user(self.project_developer)

                        self.current_user_bio = self.current_user.bio
                        self.current_user_blog = self.current_user.blog
                        self.current_user_collaborators = self.current_user.collaborators
                        self.current_user_company = self.current_user.company
                        self.current_user_contributions = self.current_user.contributions
                        self.current_user_created_at = self.current_user.created_at
                        self.current_user_followers = self.current_user.followers
                        self.current_user_following = self.current_user.following

                        self.current_user_hireable = self.current_user.hireable
                        self.current_user_login = self.current_user.login
                        self.current_user_name = self.current_user.name

                        self.developer_login = self.project_developer

                        # Does he commit during business hours?
                        scream.log_debug("Starting to analyze OSRC card for user: " + str(self.developer_login), True)
                        self.developer_works_during_bd = None
                        self.developer_works_period = 0
                        self.developer_all_pushes = 0
                        self.developer_all_stars_given = 0
                        self.developer_all_creations = 0
                        self.developer_all_issues_created = 0
                        self.developer_all_pull_requests = 0

                        self.tries = 5

                        while True:
                            try:
                                self.osrc_url = 'https://osrc.dfm.io/' + str(self.developer_login) + '.json'
                                scream.log_debug('The osrc url is: ' + self.osrc_url, True)
                                # OSRC was grumpy about the urllib2 even with headers attached
                                # hdr = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7',
                                #        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                #        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                                #        'Accept-Encoding': 'none',
                                #        'Accept-Language': 'en-US,en;q=0.8',
                                #        'Connection': 'keep-alive'}
                                # req = urllib2.Request(osrc_url, headers=hdr)
                                # response = urllib2.urlopen(req)
                                # thus i moved to requests library
                                self.proxy = {'http': '94.154.26.132:8090'}
                                self.session_osrc = requests.Session()
                                self.requests_osrc = self.session_osrc.get(self.osrc_url, proxies=self.proxy)
                                self.data = json.loads(self.requests_osrc.text)
                                self.not_enough_information = True if ('message' in self.data) and (self.data['message'].startswith('Not enough information for')) else False
                                if (self.not_enough_information):
                                    # could be user deleted, or non-contributing but told to be member.. break and assign 0 values
                                    break
                                self.time_of_activity_per_hours = [0 for z in xrange(24)]
                                for self.day_entry_element in self.data['usage']['events']:
                                    for self.day___ in self.day_entry_element['day']:
                                        self.time_of_activity_per_hours[self.day_entry_element['day'].index(self.day___)] += parse_number(self.day___)
                                scream.log_debug("Histogram for hours for user: " + str(self.developer_login) + ' created..', True)
                                # count activity during business day
                                self.count_bd__ = 0
                                self.count_bd__ += sum(self.time_of_activity_per_hours[z] for z in range(9, 18))
                                # now count activity during not-busines hours :)
                                self.count_nwh__ = 0
                                self.count_nwh__ += sum(self.time_of_activity_per_hours[z] for z in range(0, 9))
                                self.count_nwh__ += sum(self.time_of_activity_per_hours[z] for z in range(18, 24))
                                self.developer_works_during_bd = True if self.count_bd__ >= self.count_nwh__ else False
                                scream.log_debug('Running C program...', True)
                                self.args___ = ['hist_block.exe' if is_win() else './hist_block'] + [str(x) for x in self.time_of_activity_per_hours]
                                self.developer_works_period = subprocess.Popen(self.args___, stdout=subprocess.PIPE).stdout.read()

                                # now get count of events for this user....

                                for self.usage_element in self.data['usage']['events']:
                                    if (self.usage_element['type'] == "PushEvent"):
                                        self.developer_all_pushes += self.usage_element['total']
                                    elif (self.usage_element['type'] == "WatchEvent"):
                                        self.developer_all_stars_given += self.usage_element['total']
                                    elif (self.usage_element['type'] == "CreateEvent"):
                                        self.developer_all_creations += self.usage_element['total']
                                    elif (self.usage_element['type'] == "IssuesEvent"):
                                        self.developer_all_issues_created += self.usage_element['total']
                                    elif (self.usage_element['type'] == "PullRequestEvent"):
                                        self.developer_all_pull_requests += self.usage_element['total']

                                # -----------------------------------------------------------------------
                                scream.log_debug('Finished analyze OSRC card for user: ' + str(self.developer_login), True)
                                break
                            except Exception as e:
                                scream.log_error(str(e), True)
                                freeze('OSRC gave error, probably 404')
                                scream.say('try ' + str(self.tries) + ' more times')
                                self.tries -= 1
                            finally:
                                if self.tries < 1:
                                    self.developer_works_during_bd = None
                                    self.developer_works_period = 0
                                    break

                        self.collection = [str(((page-1)*pagination) + self.i), self.gh_entity, self.repo_full_name, self.repo_html_url,
                                           str(self.repo_forks_count), str(self.repo_stargazers_count), str(self.contributors_count),
                                           str(self.repo_created_at), str(self.repo_is_fork), str(self.repo_has_issues), str(self.repo_open_issues_count),
                                           str(self.repo_has_wiki), str(self.repo_network_count), str(self.repo_pushed_at), str(self.repo_size),
                                           str(self.repo_updated_at), str(self.repo_watchers_count), self.project_id,
                                           self.project_name, self.project_url, self.project_htmlurl, str(self.project_created_at),
                                           str(self.project_updated_at), self.project_homepage_url, str(self.project_average_rating),
                                           str(self.project_rating_count), str(self.project_review_count), self.project_activity_level,
                                           str(self.project_user_count), str(self.twelve_month_contributor_count), str(self.total_contributor_count),
                                           str(self.twelve_month_commit_count), str(self.total_commit_count), str(self.total_code_lines),
                                           self.main_language_name, str(self.developer_works_during_bd), str(self.developer_works_period),
                                           str(self.developer_all_pushes), str(self.developer_all_stars_given), str(self.developer_all_creations),
                                           str(self.developer_all_issues_created), str(self.developer_all_pull_requests)]

                        csv_writer.writerow(self.collection)
                        #self.set_finished(True)
                        print '.'
                except UnknownObjectException:
                    print 'Repo ' + self.gh_entity + ' is not available anymore..'
                except GithubException:
                    # TODO: write here something clever
                    raise
        self.set_finished(True)


def all_finished(threads):
    are_finished = True
    for thread in threads:
        if not thread.is_finished():
            return False
    return are_finished


def num_working(threads):
    are_working = 0
    for thread in threads:
        if not thread.is_finished():
            are_working += 1
        else:
            thread.cleanup()
    return are_working


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-tags", help="type of software [tags] you wish to parse from openhub", type=str)
    parser.add_argument("-r", "--resume", help="resume parse ? [True/False]", action="store_true")
    parser.add_argument("-resume_point", help="resume point (ordinal_id)", type=int)
    parser.add_argument("-fa", "--force_append", help="force appending results to CSV instead of overwrite", action="store_true")
    parser.add_argument("-v", "--verbose", help="verbose messaging ? [True/False]", action="store_true")
    parser.add_argument("-s", "--excel", help="add excel sepinfo at the beginning ? [True/False]", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        scream.intelliTag_verbose = True
        scream.say("verbosity turned on")
    if args.tags:
        openhub_query_tags = args.tags.split(',')
        print 'Tags used to query open hub will be: ' + str(openhub_query_tags)
    if args.force_append:
        force_csv_append = True
    if args.resume_point:
        print 'Resume repo id is: ' + str(args.resume_point)

    assert len(openhub_query_tags) < 2 # I couldn't find a way to query openhub for multiple tags..

    first_conn = MSQL.connect(host="10.4.4.3", port=3306, user=open('mysqlu.dat', 'r').read(),
                              passwd=open('mysqlp.dat', 'r').read(), db="github", connect_timeout=50000000)
    print 'Testing mySql connection...'
    print 'Pinging database: ' + (str(first_conn.ping(True)) if first_conn.ping(True) is not None else 'NaN')
    cursor = first_conn.cursor()
    cursor.execute(r'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = "%s"' % 'github')
    rows = cursor.fetchall()
    print 'There are: ' + str(rows[0][0]) + ' table objects in the local GHtorrent copy'
    cursor.close()
    first_conn.close()
    #conn.ping(True)

    github_clients = list()
    github_clients_ids = list()
    secrets = []
    credential_list = []

    page = 0

    # reading the secrets, the Github factory objects will be created in next paragraph
    with open('pass.txt', 'r') as passfile:
        line__id = 0
        for line in passfile:
            line__id += 1
            secrets.append(line)
            if line__id % 4 == 0:
                login_or_token__ = str(secrets[0]).strip()
                pass_string = str(secrets[1]).strip()
                client_id__ = str(secrets[2]).strip()
                client_secret__ = str(secrets[3]).strip()
                credential_list.append({'login': login_or_token__, 'pass': pass_string, 'client_id': client_id__, 'client_secret': client_secret__})
                del secrets[:]

    print str(len(credential_list)) + ' full credentials successfully loaded'

    openhub_secrets = []

    with open('openhub-credentials.txt', 'r') as passfile:
        for line in passfile:
            openhub_secrets.append(line)

    print str(len(openhub_secrets)) + ' openhub credentials successfully loaded'

    # with the credential_list list we create a list of Github objects, github_clients holds ready Github objects
    for credential in credential_list:
        local_gh = Github(login_or_token=credential['pass'], client_id=credential['client_id'],
                          client_secret=credential['client_secret'], user_agent=credential['login'],
                          timeout=timeout)
        github_clients.append(local_gh)
        github_clients_ids.append(credential['login'])
        print local_gh.rate_limiting

    print 'How many Github objects in github_clients: ' + str(len(github_clients))
    print 'Assigning current github client to the first object in a list'

    github_client = github_clients[0]
    lapis = local_gh.get_api_status()
    print 'Current status of GitHub API...: ' + lapis.status + ' (last update: ' + str(lapis.last_updated) + ')'

    result_csv_filename = 'results_' + openhub_query_tags[0] + '.csv'
    with open(result_csv_filename, 'ab' if force_csv_append else 'wb') as csv_file:
        threads = []
        thread_id_count = 0

        csv_writer = UnicodeWriter(csv_file, dialect=WriterDialectQuoteAll)

        sepinfo = ['sep=;']
        headers = ['ordinal_id', 'github_repo_id', 'repo_full_name', 'repo_html_url', 'repo_forks_count',
                   'stargazers_count', 'contributors_count', 'repo_created_at', 'repo_is_fork', 'repo_has_issues',
                   'repo_open_issues_count', 'repo_has_wiki', 'repo_network_count',
                   'repo_pushed_at', 'repo_size', 'repo_updated_at', 'repo_watchers_count',
                   'project_id', 'project_name', 'project_url', 'project_htmlurl', 'project_created_at',
                   'project_updated_at', 'project_homepage_url', 'project_average_rating', 'project_rating_count', 'project_review_count',
                   'project_activity_level', 'project_user_count', 'twelve_month_contributor_count', 'total_contributor_count',
                   'twelve_month_commit_count', 'total_commit_count', 'total_code_lines', 'main_language_name',
                   'developer_works_during_bd', 'developer_works_period',
                   'developer_all_pushes', 'developer_all_stars_given', 'developer_all_creations',
                   'developer_all_issues_created', 'developer_all_pull_requests']
        csv_writer.writerow(sepinfo)
        csv_writer.writerow(headers)

        Github(login_or_token=credential['pass'], client_id=credential['client_id'],
               client_secret=credential['client_secret'], user_agent=credential['login'], timeout=timeout)

        while (results_done < results_all):
            # Connect to the Ohloh website and retrieve the account data.
            page += 1
            gg = GeneralGetter(thread_id_count, page)
            scream.say('Creating instance of GeneralGetter complete')
            scream.say('Appending thread to collection of threads')
            threads.append(gg)
            scream.say('Append complete, threads[] now have size: ' + str(len(threads)))
            thread_id_count += 1
            scream.log_debug('Starting thread ' + str(thread_id_count-1) + '....', True)
            gg.start()
            while (num_working(threads) > 7):
                time.sleep(0.2)  # sleeping for 200 ms - there are already 8 active threads..
