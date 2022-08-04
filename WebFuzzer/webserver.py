#!/usr/bin/python3
from multiprocess import Process
import requests
import time
from multiprocess import Queue
import sys
import traceback
import urllib.parse
import sqlite3
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.server import HTTPStatus
import fuzzingbook.bookutils
from typing import NoReturn, Tuple, Dict, List, Optional, Union
from IPython.display import display
from fuzzingbook.bookutils import HTML
from fuzzingbook.bookutils import rich_output, terminal_escape

ORDERS_DB = "orders.db"

HTTPD_MESSAGE_QUEUE = Queue()

HTTPD_MESSAGE_QUEUE.put("I am another message")
HTTPD_MESSAGE_QUEUE.put("I am one more message")

FUZZINGBOOK_SWAG = {
    "tshirt": "One FuzzingBook T-Shirt",
    "drill": "One FuzzingBook Rotary Hammer",
    "lockset": "One FuzzingBook Lock Set"
}

HTML_ORDER_FORM = """
<html><body>
<form action="/order" style="border:3px; border-style:solid; border-color:#FF0000; padding: 1em;">
  <strong id="title" style="font-size: x-large">Fuzzingbook Swag Order Form</strong>
  <p>
  Yes! Please send me at your earliest convenience
  <select name="item">
  """
# (We don't use h2, h3, etc. here
# as they interfere with the notebook table of contents)

for item in FUZZINGBOOK_SWAG:
    HTML_ORDER_FORM += \
        '<option value="{item}">{name}</option>\n'.format(item=item,
            name=FUZZINGBOOK_SWAG[item])

HTML_ORDER_FORM += """
  </select>
  <br>
  <table>
  <tr><td>
  <label for="name">Name: </label><input type="text" name="name">
  </td><td>
  <label for="email">Email: </label><input type="email" name="email"><br>
  </td></tr>
  <tr><td>
  <label for="city">City: </label><input type="text" name="city">
  </td><td>
  <label for="zip">ZIP Code: </label><input type="number" name="zip">
  </tr></tr>
  </table>
  <input type="checkbox" name="terms"><label for="terms">I have read
  the <a href="/terms">terms and conditions</a></label>.<br>
  <input type="submit" name="submit" value="Place order">
</p>
</form>
</body></html>
"""

HTML_ORDER_RECEIVED = """
<html><body>
<div style="border:3px; border-style:solid; border-color:#FF0000; padding: 1em;">
  <strong id="title" style="font-size: x-large">Thank you for your Fuzzingbook Order!</strong>
  <p id="confirmation">
  We will send <strong>{item_name}</strong> to {name} in {city}, {zip}<br>
  A confirmation mail will be sent to {email}.
  </p>
  <p>
  Want more swag?  Use our <a href="/">order form</a>!
  </p>
</div>
</body></html>
"""

HTML_TERMS_AND_CONDITIONS = """
<html><body>
<div style="border:3px; border-style:solid; border-color:#FF0000; padding: 1em;">
  <strong id="title" style="font-size: x-large">Fuzzingbook Terms and Conditions</strong>
  <p>
  The content of this project is licensed under the
  <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons
  Attribution-NonCommercial-ShareAlike 4.0 International License.</a>
  </p>
  <p>
  To place an order, use our <a href="/">order form</a>.
  </p>
</div>
</body></html>
"""

HTML_NOT_FOUND = """
<html><body>
<div style="border:3px; border-style:solid; border-color:#FF0000; padding: 1em;">
  <strong id="title" style="font-size: x-large">Sorry.</strong>
  <p>
  This page does not exist.  Try our <a href="/">order form</a> instead.
  </p>
</div>
</body></html>
  """

HTML_INTERNAL_SERVER_ERROR = """
<html><body>
<div style="border:3px; border-style:solid; border-color:#FF0000; padding: 1em;">
  <strong id="title" style="font-size: x-large">Internal Server Error</strong>
  <p>
  The server has encountered an internal error.  Go to our <a href="/">order form</a>.
  <pre>{error_message}</pre>
  </p>
</div>
</body></html>
  """

def init_db():
    if os.path.exists(ORDERS_DB):
        os.remove(ORDERS_DB)

    db_connection = sqlite3.connect(ORDERS_DB)
    db_connection.execute("DROP TABLE IF EXISTS orders")
    db_connection.execute("CREATE TABLE orders "
                          "(item text, name text, email text, "
                          "city text, zip text)")
    db_connection.commit()

    return db_connection

db = init_db()

#print(db.execute("SELECT * FROM orders").fetchall())

#db.execute("INSERT INTO orders " + "VALUES ('lockset', 'Walter White', ""'white@jpwynne.edu', 'Albuquerque', '87101')")
#db.commit()

#print(db.execute("SELECT * FROM orders").fetchall())
#db.execute("DELETE FROM orders WHERE name = 'Walter White'")
#db.commit()
#print(db.execute("SELECT * FROM orders").fetchall())

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """A simple HTTP Server"""
    pass

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        try:
            # print("GET " + self.path)
            if self.path == "/":
                self.send_order_form()
            elif self.path.startswith("/order"):
                self.handle_order()
            elif self.path.startswith("/terms"):
                self.send_terms_and_conditions()
            else:
                self.not_found()
        except Exception:
            self.internal_server_error()

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_order_form(self):
        self.send_response(HTTPStatus.OK, "Place your order")
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_ORDER_FORM.encode("utf8"))

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_terms_and_conditions(self):
        self.send_response(HTTPStatus.OK, "Terms and Conditions")
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_TERMS_AND_CONDITIONS.encode("utf8"))

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def get_field_values(self):
        # Note: this fails to decode non-ASCII characters properly
        query_string = urllib.parse.urlparse(self.path).query

        # fields is { 'item': ['tshirt'], 'name': ['Jane Doe'], ...}
        fields = urllib.parse.parse_qs(query_string, keep_blank_values=True)

        values = {}
        for key in fields:
            values[key] = fields[key][0]

        return values

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def handle_order(self):
        values = self.get_field_values()
        self.store_order(values)
        self.send_order_received(values)

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def store_order(self, values):
        db = sqlite3.connect(ORDERS_DB)
        # The following should be one line
        sql_command = "INSERT INTO orders VALUES ('{item}', '{name}', '{email}', '{city}', '{zip}')".format(**values)
        self.log_message("%s", sql_command)
        db.executescript(sql_command)
        db.commit()

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_order_received(self, values):
        # Should use html.escape()
        values["item_name"] = FUZZINGBOOK_SWAG[values["item"]]
        confirmation = HTML_ORDER_RECEIVED.format(**values).encode("utf8")

        self.send_response(HTTPStatus.OK, "Order received")
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(confirmation)

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_HEAD(self):
        # print("HEAD " + self.path)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html")
        self.end_headers()

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def not_found(self):
        self.send_response(HTTPStatus.NOT_FOUND, "Not found")

        self.send_header("Content-type", "text/html")
        self.end_headers()

        message = HTML_NOT_FOUND
        self.wfile.write(message.encode("utf8"))

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def internal_server_error(self):
        self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal Error")

        self.send_header("Content-type", "text/html")
        self.end_headers()

        exc = traceback.format_exc()
        self.log_message("%s", exc.strip())

        message = HTML_INTERNAL_SERVER_ERROR.format(error_message=exc)
        self.wfile.write(message.encode("utf8"))

def display_httpd_message(message: str) -> None:
    if rich_output():
        display(
            HTML(
                '<pre style="background: NavajoWhite;">' +
                message +
                "</pre>"))
    else:
        print(terminal_escape(message))

def print_httpd_messages():
    while not HTTPD_MESSAGE_QUEUE.empty():
        message = HTTPD_MESSAGE_QUEUE.get()
        display_httpd_message(message)

def clear_httpd_messages() -> None:
    while not HTTPD_MESSAGE_QUEUE.empty():
        HTTPD_MESSAGE_QUEUE.get()

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        message = ("%s - - [%s] %s\n" %
                   (self.address_string(),
                    self.log_date_time_string(),
                    format % args))
        HTTPD_MESSAGE_QUEUE.put(message)

class SimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        message = ("%s - - [%s] %s\n" %
                   (self.address_string(),
                    self.log_date_time_string(),
                    format % args))
        HTTPD_MESSAGE_QUEUE.put(message)

def run_httpd_forever(handler_class: type) -> NoReturn:
    host = "127.0.0.1"  # localhost IP
    for port in range(8800, 9000):
        httpd_address = (host, port)

        try:
            httpd = HTTPServer(httpd_address, handler_class)
            break
        except OSError:
            continue

    httpd_url = "http://" + host + ":" + repr(port)
    HTTPD_MESSAGE_QUEUE.put(httpd_url)
    httpd.serve_forever()

def start_httpd(handler_class: type = SimpleHTTPRequestHandler) \
        -> Tuple[Process, str]:
    clear_httpd_messages()

    httpd_process = Process(target=run_httpd_forever, args=(handler_class,))
    httpd_process.start()

    httpd_url = HTTPD_MESSAGE_QUEUE.get()
    return httpd_process, httpd_url

httpd_process, httpd_url = start_httpd()
print(httpd_url)
