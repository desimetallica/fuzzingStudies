#!/usr/bin/python3 
from ntpath import join
from urllib.parse import urljoin, urlsplit
import requests

httpd_url = "http://127.0.0.1:8800"
joined_url = urljoin(httpd_url, "/order?foo=bar")

print(joined_url)
resp = requests.get(urljoin(httpd_url, "/order?item=tshirt&name=Jane+Doe&email=doe%40example.com&city=Seattle&zip=98104"))
print(resp.status_code)
print(resp.content)

