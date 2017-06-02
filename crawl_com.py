#!/usr/bin/env python3

# coding=utf-8
# -*- coding: utf8 -*-

from googleapiclient.discovery import build
import requests
import json
import sys
import csv
import os
import re
import pprint
from bs4 import BeautifulSoup

api_key = "my_api_key"
cse_id = "my_cse_id"

domain_filter = ["104.com", "1111.com", "indeed.com", "518.com", "facebook.com",
                 "ithome.com", "mcujobs.tw", "gov.tw"]
company_list = []

email_re = r"[\w\.-]+@[\w\.-]+"
phone_re = r"[+(]?\d+\)?[-\d+]+"


def google_search(query, index):
    # Build a service object for interacting with the API. Visit
    # the Google APIs Console <http://code.google.com/apis/console>
    # to get an API key for your own application.
    service = build("customsearch", "v1",
                    developerKey=api_key)

    res = service.cse().list(
        q=query,
        cx=cse_id,
        num=10,
        start=index
    ).execute()

    # pprint.pprint(res)
    with open('gsr/' + str(index) + '.json', 'w') as f:
        json.dump(res['items'], f)


class Company(object):
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.email = []
        self.phone = []

    def add_email(self, mail):
        self.email += mail

    def add_phone(self, fone):
        self.phone += fone

    def to_row(self):
        return [self.name, self.url, ', '.join(self.email), ', '.join(self.phone)]


def output_to_csv(file_name):
    with open(file_name, 'w', encoding='utf-8-sig') as output:
        wr = csv.writer(output, dialect='excel')
        wr.writerow(['Name', 'Url', 'EMail', 'Phone'])
        for com in company_list:
            try:
                wr.writerow(com.to_row())
            except:
                print("output error: " + com.name)


def get_phone_number(s):
    phone = []
    phone += re.findall(r"0\d{1,2}-\d{6,8}", s)
    phone += re.findall(r"\(?0\d{1,2}\)-\d{6,8}", s)
    phone += re.findall(r"0\d{1,2}-?\d{4}-?\d{4}", s)
    phone += re.findall(r"\(?0\d{1,2}\)?\d{4}-?\d{4}", s)
    phone += re.findall(r"09\d{2}-?\d{3}-?\d{3}", s)
    phone += re.findall(r"0800-?\d{3}-?\d{3}", s)
    phone += re.findall(r"\+886[-\d+]+", s)
    return [x for x in phone if 9 < len(x) < 17 and ('-' in x or ')' in x)]
    # return [x for x in re.findall(phone_re, s) if 9 < len(x) < 17]


def get_email_addr(s):
    return [x for x in re.findall(email_re, s) if len(x.split('@')) is 2]


def get_next_page(s, url):
    soup = BeautifulSoup(s, "html.parser")
    href = []
    for a in soup.find_all('a', href=True):
        link = a['href']
        if 'mailto' in link or 'javascript' in link:
            continue
        if 'http' not in link:
            link = url + '/' + link
        if url.split('/')[2] not in link:
            continue
        href.append(link)
    return href


def get_page(url):
    try:
        res = requests.get(url)
        return res.text
    except:
        print("get url error: " + url)
        return "error"


def get_contact(com):
    s = get_page(com.url)
    com.add_email(get_email_addr(s))
    com.add_phone(get_phone_number(s))
    pprint.pprint(com.to_row())
    if len(com.email) is 0 or len(com.phone) is 0:
        links = get_next_page(s, com.url)
        for link in links:
            ss = get_page(link)
            com.add_email(get_email_addr(ss))
            com.add_phone(get_phone_number(ss))

    com.phone = list(set(com.phone))
    com.email = list(set(com.email))
    return com


def is_homepage(url):
    tok = url.split('/')
    if len(tok) > 5:
        return False
    if len(tok[-1]) > 15:
        return False
    for domain in domain_filter:
        if domain in url:
            return False
    return True


def parse_gsr(search_result):
    for result in search_result:
        if is_homepage(result['link']):
            company = Company(result['title'], result['link'])
            company = get_contact(company)
            company_list.append(company)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python crawl_com.py [keyword]")
        sys.exit(1)

    query = sys.argv[1]
    for i in range(10):
        google_search(query, 1 + i * 10)

    for file in os.listdir("gsr"):
        with open('gsr/' + file) as f:
            results = json.load(f)

        parse_gsr(results)

    output_to_csv('result.csv')
