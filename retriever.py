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


pagination = 10
NullChar = 'NaN'


def num_modulo(thread_id_count__):
    global no_of_threads
    return thread_id_count__ % pagination


def return_random_openhub_key():
    global openhub_secrets
    return random.choice(openhub_secrets).strip()

# don't forget to provide api key as first arg of python script
results_done = 0
results_all = 8420  # checked manually, hence its later overwritten
page = 0
timeout = 50

conn = MSQL.connect(host="10.4.4.3", port=3306, user=open('mysqlu.dat', 'r').read(), passwd=open('mysqlp.dat', 'r').read(), db="github")
print 'Testing mySql connection...'
print 'Pinging database: ' + (str(conn.ping()) if conn.ping() is not None else 'NaN')
cursor = conn.cursor()
cursor.execute(r'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = "%s"' % 'github')
rows = cursor.fetchall()
print 'There are: ' + str(rows[0][0]) + ' table objects in the local GHtorrent copy'
cursor.close()

github_clients = list()
github_clients_ids = list()
secrets = []
credential_list = []

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

with open('results.csv', 'wb') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=';', quotechar='\"', quoting=csv.QUOTE_ALL)
    sepinfo = ['sep=;']
    headers = ['ordinal_id', 'github_repo_id', 'repo_full_name', 'repo_html_url', 'repo_forks_count',
               'repo_stargazers_count', 'repo_created_at', 'repo_is_fork', 'repo_has_issues',
               'repo_open_issues_count', 'repo_has_wiki', 'repo_network_count',
               'repo_pushed_at', 'repo_size', 'repo_updated_at', 'wrepo_atchers_count',
               'project_id', 'project_name', 'project_url', 'project_htmlurl', 'project_created_at',
               'project_updated_at', 'project_homepage_url', 'project_average_rating', 'project_rating_count', 'project_review_count',
               'project_activity_level', 'project_user_count', 'twelve_month_contributor_count', 'total_contributor_count',
               'twelve_month_commit_count', 'total_commit_count', 'total_code_lines', 'main_language_name']
    csv_writer.writerow(sepinfo)
    csv_writer.writerow(headers)

    Github(login_or_token=credential['pass'], client_id=credential['client_id'],
           client_secret=credential['client_secret'], user_agent=credential['login'], timeout=timeout)

    while (results_done < results_all):
        # Connect to the Ohloh website and retrieve the account data.
        page += 1
        params_sort_rating = urllib.urlencode({'query': 'tag:framework', 'api_key': return_random_openhub_key(),
                                               'sort': 'rating', 'page': page})
        projects_api_url = "https://www.openhub.net/projects.xml?%s" % (params_sort_rating)

        result_flow = urllib.urlopen(projects_api_url)

        print ''
        print '-------------------------- PAGE ' + str(page) + ' parsed -----------------------------'
        print ''

        # Parse the response into a structured XML object
        tree = ET.parse(result_flow)

        # Did Ohloh return an error?
        elem = tree.getroot()
        error = elem.find("error")
        if error is not None:
            print 'OpenHub returned:', ET.tostring(error),
            sys.exit()

        results_done += int(elem.find("items_returned").text)
        results_all = int(elem.find("items_available").text)

        i = 0
        for node in elem.findall("result/project"):
            i += 1
            print 'Checking element ' + str(i) + '/' + str(pagination)

            project_id = node.find("id").text
            project_name = node.find("name").text
            project_url = node.find("url").text
            project_htmlurl = node.find("html_url").text
            project_created_at = node.find("created_at").text
            project_updated_at = node.find("updated_at").text
            project_homepage_url = node.find("homepage_url").text

            project_average_rating = node.find("average_rating").text
            project_rating_count = node.find("rating_count").text
            project_review_count = node.find("review_count").text

            project_activity_level = node.find("project_activity_index/value").text

            project_user_count = node.find("user_count").text

            # project may have multiple GitHub repositories
            # or even it may be not present on GitHub - check that

            is_github_project = False
            github_repo_id = None

            # in case of multiple github CODE repositories (quite often)
            # treat as a seperate repo - remember, we focus on github repositories, not aggregates

            enlistments_detailed_params = urllib.urlencode({'api_key': return_random_openhub_key()})
            enlistments_detailed_url = "https://www.openhub.net/projects/%s/enlistments.xml?%s" % (project_id, enlistments_detailed_params)

            enlistments_result_flow = urllib.urlopen(enlistments_detailed_url)

            # Parse the response into a structured XML object
            enlistments_tree = ET.parse(enlistments_result_flow)

            # Did Ohloh return an error?
            enlistments_elem = enlistments_tree.getroot()
            enlistments_error = enlistments_elem.find("error")
            if enlistments_error is not None:
                print 'Ohloh returned:', ET.tostring(enlistments_error),
                sys.exit()

            repos_lists = list()

            for enlistment_node in enlistments_elem.findall("result/enlistment"):
                ee_type = enlistment_node.find("repository/type").text
                if (ee_type == "GitRepository"):
                    ee_link = enlistment_node.find("repository/url").text
                    if (ee_link.startswith("git://github.com/")):
                        print 'Is a GitHub project!'
                        is_github_project = True
                        github_repo_id = ee_link.split("git://github.com/")[1].split(".git")[0]
                        print github_repo_id
                        repos_lists.append(github_repo_id)

            if not is_github_project:
                continue

            # now lets get even more sophisticated details
            params_detailed_url = urllib.urlencode({'api_key': return_random_openhub_key()})
            project_detailed_url = "https://www.openhub.net/projects/%s.xml?%s" % (project_id, params_sort_rating)

            detailed_result_flow = urllib.urlopen(project_detailed_url)

            # Parse the response into a structured XML object
            detailed_tree = ET.parse(detailed_result_flow)

            # Did Ohloh return an error?
            detailed_elem = detailed_tree.getroot()
            detailed_error = detailed_elem.find("error")
            if detailed_error is not None:
                print 'Ohloh returned:', ET.tostring(detailed_error),
                sys.exit()

            twelve_month_contributor_count = detailed_elem.find("result/project/analysis/twelve_month_contributor_count").text
            total_contributor_count = detailed_elem.find("result/project/analysis/total_contributor_count").text
            twelve_month_commit_count = detailed_elem.find("result/project/analysis/twelve_month_commit_count")
            twelve_month_commit_count = twelve_month_commit_count.text if twelve_month_commit_count is not None else NullChar
            total_commit_count = detailed_elem.find("result/project/analysis/total_commit_count")
            total_commit_count = total_commit_count.text if total_commit_count is not None else NullChar
            total_code_lines = detailed_elem.find("result/project/analysis/total_code_lines")
            total_code_lines = total_code_lines.text if total_code_lines is not None else NullChar
            main_language_name = detailed_elem.find("result/project/analysis/main_language_name")
            main_language_name = main_language_name.text if main_language_name is not None else NullChar

            current_ghc = github_clients[num_modulo(i-1)]
            current_ghc_desc = github_clients_ids[num_modulo(i-1)]

            print 'Now using github client id: ' + str(current_ghc_desc)

            for gh_entity in repos_lists:

                try:
                    repository = current_ghc.get_repo(gh_entity)
                    repo_name = repository.name
                    repo_full_name = repository.full_name
                    repo_html_url = repository.html_url
                    repo_stargazers_count = repository.stargazers_count
                    repo_forks_count = repository.forks_count
                    repo_created_at = repository.created_at
                    repo_is_fork = repository.fork
                    repo_has_issues = repository.has_issues
                    repo_open_issues_count = repository.open_issues_count
                    repo_has_wiki = repository.has_wiki
                    repo_network_count = repository.network_count
                    repo_pushed_at = repository.pushed_at
                    repo_size = repository.size
                    repo_updated_at = repository.updated_at
                    repo_watchers_count = repository.watchers_count

                    # Now its time to get the list of developers!

                    # yay! rec-09 mysql instance is visible from the yoshimune computer !
                    # ok, but I forgot github blacklisted our comptuing clusters
                    # make sure your local win machine runs it..
                    # just pjatk things.. carry on

                    print 'Retrieving the project id from mysql database.. should take max 1 second.'

                    # Get here project id used in the database !
                    cursor = conn.cursor()
                    cursor.execute(r'select distinct id from (select * from projects where `name`="{0}") as p where url like "%{1}"'.format(repo_name, repo_full_name))
                    rows = cursor.fetchall()

                    repo_db_id = rows[0]

                    print 'project id retrieved from database is: ' + str()

                    # Now get list of GitHub logins which are project_members !
                    cursor.execute(r'SELECT user_id FROM poject_members WHERE repo_id = "%s"' % 'github')
                    project_developers = cursor.fetchall()

                    contributors_count = project_developers.size()

                    for project_developer in project_developers:

                        # create a GitHub user named object for GitHub API
                        current_user = current_ghc.get_user(project_developer)

                        current_user_bio = current_user.bio
                        current_user_blog = current_user.blog
                        current_user_collaborators = current_user.collaborators
                        current_user_company = current_user.company
                        current_user_contributions = current_user.contributions
                        current_user_created_at = current_user.created_at
                        current_user_followers = current_user.followers
                        current_user_following = current_user.following

                        current_user_hireable = current_user.hireable
                        current_user_login = current_user.login
                        current_user_name = current_user.name

                        # Does he commit during business hours?
                        scream.log_debug("Starting to analyze OSRC card for user: " + str(developer_login), True)
                        developer_works_during_bd = None
                        developer_works_period = None
                        tries = 5

                        while True:
                            try:
                                osrc_url = 'http://osrc.dfm.io/' + str(developer_login) + '.json'
                                scream.log_debug('The osrc url is: ' + osrc_url, True)
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
                                proxy = {'http': '184.105.239.95:8080'}
                                session_osrc = requests.Session()
                                requests_osrc = session_osrc.get(osrc_url, proxies=proxy)
                                data = json.loads(requests_osrc.text)
                                time_of_activity_per_hours = [0 for i in xrange(24)]
                                for day_entry_element in data['usage']['events']:
                                    for day___ in day_entry_element['day']:
                                        time_of_activity_per_hours[day_entry_element['day'].index(day___)] += parse_number(day___)
                                scream.log_debug("Histogram for hours for user: " + str(developer_login) + ' created..', True)
                                # count activity during business day
                                count_bd__ = 0
                                count_bd__ += sum(time_of_activity_per_hours[i] for i in range(9, 18))
                                # now count activity during not-busines hours :)
                                count_nwh__ = 0
                                count_nwh__ += sum(time_of_activity_per_hours[i] for i in range(0, 9))
                                count_nwh__ += sum(time_of_activity_per_hours[i] for i in range(18, 24))
                                developer_works_during_bd = True if count_bd__ >= count_nwh__ else False
                                scream.log_debug('Running C program...', True)
                                args___ = ['hist_block.exe' if is_win() else './hist_block'] + [str(x) for x in time_of_activity_per_hours]
                                developer_works_period = subprocess.Popen(args___, stdout=subprocess.PIPE).stdout.read()
                                # -----------------------------------------------------------------------
                                scream.log_debug('Finished analyze OSRC card for user: ' + str(developer_login), True)
                                break
                            except Exception as e:
                                scream.log_error(str(e), True)
                                freeze('OSRC gave error, probably 404')
                                scream.say('try ' + str(tries) + ' more times')
                                tries -= 1
                            finally:
                                if tries < 1:
                                    developer_works_during_bd = 0
                                    developer_works_period = 0
                                    break

                        collection = [str(((page-1)*pagination) + i), gh_entity, repo_full_name, repo_html_url, str(repo_forks_count),
                                      str(repo_stargazers_count), str(contributors_count),
                                      repo_created_at, repo_is_fork, repo_has_issues, repo_open_issues_count,
                                      repo_has_wiki, repo_network_count, repo_pushed_at, repo_size, repo_updated_at, repo_watchers_count,
                                      project_id, project_name, project_url, project_htmlurl, project_created_at,
                                      project_updated_at, project_homepage_url, project_average_rating, project_rating_count, project_review_count,
                                      project_activity_level, project_user_count, twelve_month_contributor_count, total_contributor_count,
                                      twelve_month_commit_count, total_commit_count, total_code_lines, main_language_name]

                        csv_writer.writerow(collection)
                        print '.'
                except UnknownObjectException:
                    print 'Repo ' + gh_entity + ' is not available anymore..'
                except GithubException:
                    # TODO: write here something clever
                    raise

        # Output all the immediate child properties of an Account
        # for node in elem.find("result/project"):
        #     if node.tag == "kudo_score":
        #         print "%s:" % node.tag
        #         for score in elem.find("result/account/kudo_score"):
        #             print "\t%s:\t%s" % (score.tag, score.text)
        #     else:
        #         print "%s:\t%s" % (node.tag, node.text)
