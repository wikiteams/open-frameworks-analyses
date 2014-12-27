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
# import ElementTree based on the python version
try:
    import elementtree.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# don't forget to provide api key as first arg of python script
results_done = 0
results_all = 8420  # checked manually, hence its later overwritten
pagination = 10
page = 0

with open('results.csv', 'wb') as csv_file:
    csv_writer = csv.writer(csv_file, delimiter=';', quotechar='\"', quoting=csv.QUOTE_ALL)
    headers = ['project_id', 'project_name', 'project_url', 'project_htmlurl', 'project_created_at',
               'project_updated_at', 'project_homepage_url', 'project_average_rating', 'project_rating_count', 'project_review_count',
               'project_activity_level']
    csv_writer.writerow(headers)

    while (results_done < results_all):
        # Connect to the Ohloh website and retrieve the account data.
        page += 1
        params_sort_rating = urllib.urlencode({'query': 'tag:framework', 'api_key': sys.argv[1], 'sort': 'rating', 'page': page})
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
            print 'Ohloh returned:', ET.tostring(error),
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

            collection = [project_id, project_name, project_url, project_htmlurl, project_created_at,
                          project_updated_at, project_homepage_url, project_average_rating, project_rating_count, project_review_count,
                          project_activity_level]

            csv_writer.writerow(collection)
            print '.'

        # Output all the immediate child properties of an Account
        # for node in elem.find("result/project"):
        #     if node.tag == "kudo_score":
        #         print "%s:" % node.tag
        #         for score in elem.find("result/account/kudo_score"):
        #             print "\t%s:\t%s" % (score.tag, score.text)
        #     else:
        #         print "%s:\t%s" % (node.tag, node.text)
