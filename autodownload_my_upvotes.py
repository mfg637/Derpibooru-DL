#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib.request, os, sys, json
import tkinter
import math
from tkinter import filedialog
from derpibooru_dl import tagResponse, parser

try:
    import config
except ImportError as e:
    print('error importing config.py')
    raise(e)

error_str1 = 'Error: user API key required.'
error_str1_continue = 'Find you API key in page: "https://derpibooru.org/pages/api"'

try:
    if len(config.key)==0:
        print(error_str1)
        exit()
except AttributeError:
    print(error_str1)
    print('Add string "key = \'you API key here\'" in "config.py" file.')
    print(error_str1_continue)
    exit()

items_per_page=15
pages=1
current_page=1

if len(sys.argv)==1:
    nvalue=3
    period='days'
elif len(sys.argv)==2:
    nvalue=int(sys.argv[1])
    period='days'
elif len(sys.argv)==3:
    nvalue=int(sys.argv[1])
    period=sys.argv[2]

while current_page<=pages:
    print('loading page {} of {}'.format(current_page, pages))
    request={
        'nvalue': nvalue,
        'period': period,
        'page': current_page,
        'key': config.key,
        'perpage': items_per_page
    }
    request_url = ("https://derpibooru.org/search.json?"
                    "q=first_seen_at.gt%3A{nvalue}+{period}+ago+"
                    "%26%26+my%3Aupvotes&key={key}"
                    "&page={page}&perpage={perpage}").format(**request)
    urlstream=urllib.request.urlopen(request_url)
    data = json.loads(str(urlstream.read(), 'utf-8'))
    urlstream.close()
    del urlstream
    if current_page==1:
        pages = int(math.ceil(data['total']/items_per_page))
    for item in data['search']:
        parsed_tags=tagResponse.tagIndex(item['tags'])
        outdir=tagResponse.find_folder(parsed_tags)
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        parser.download(outdir, item)
    current_page += 1