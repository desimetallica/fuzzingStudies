#!/usr/bin/python3
import string
import copy
from hashlib import new
from fuzzingbook.MutationFuzzer import MutationFuzzer
from typing import Set
from itertools import zip_longest
import re
import random

import traitlets

DIGIT_GRAMMAR = {
    "<start>":
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
}

Grammar = dict[str, list[str]]

EXPR_GRAMMAR: Grammar = {
    "<start>":
        ["<expr>"],

    "<expr>":
        ["<term> + <expr>", "<term> - <expr>", "<term>"],

    "<term>":
        ["<factor> * <term>", "<factor> / <term>", "<factor>"],

    "<factor>":
        ["+<factor>",
         "-<factor>",
         "(<expr>)",
         "<integer>.<integer>",
         "<integer>"],

    "<integer>":
        ["<digit><integer>", "<digit>"],

    "<digit>":
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
}


START_SYMBOL = "<start>"
RE_NONTERMINAL = re.compile(r'(<[^<> ]*>)')


def nonterminals(expansion):
    # In later chapters, we allow expansions to be tuples,
    # with the expansion being the first element
    if isinstance(expansion, tuple):
        expansion = expansion[0]

    return RE_NONTERMINAL.findall(expansion)

assert nonterminals("<term> * <factor>") == ["<term>", "<factor>"]
assert nonterminals("<digit><integer>") == ["<digit>", "<integer>"]
assert nonterminals("1 < 3 > 2") == []
assert nonterminals("1 <3> 2") == ["<3>"]
assert nonterminals("1 + 2") == []
assert nonterminals(("<1>", {'option': 'value'})) == ["<1>"]

def is_nonterminal(s):
    return RE_NONTERMINAL.match(s)

assert is_nonterminal("<abc>")
assert is_nonterminal("<symbol-1>")
assert not is_nonterminal("+")

class ExpansionError(Exception):
    pass

def simple_grammar_fuzzer(grammar: Grammar, 
                          start_symbol: str = START_SYMBOL,
                          max_nonterminals: int = 10,
                          max_expansion_trials: int = 100,
                          log: bool = False) -> str:
    """Produce a string from `grammar`.
       `start_symbol`: use a start symbol other than `<start>` (default).
       `max_nonterminals`: the maximum number of nonterminals 
         still left for expansion
       `max_expansion_trials`: maximum # of attempts to produce a string
       `log`: print expansion progress if True"""

    term = start_symbol
    expansion_trials = 0

    while len(nonterminals(term)) > 0:
        symbol_to_expand = random.choice(nonterminals(term))
        expansions = grammar[symbol_to_expand]
        expansion = random.choice(expansions)
        # In later chapters, we allow expansions to be tuples,
        # with the expansion being the first element
        if isinstance(expansion, tuple):
            expansion = expansion[0]

        new_term = term.replace(symbol_to_expand, expansion, 1)

        if len(nonterminals(new_term)) < max_nonterminals:
            term = new_term
            if log:
                print("%-40s" % (symbol_to_expand + " -> " + expansion), term)
            expansion_trials = 0
        else:
            expansion_trials += 1
            if expansion_trials >= max_expansion_trials:
                raise ExpansionError("Cannot expand " + repr(term))

    return term


for i in range(5):
    print(simple_grammar_fuzzer(grammar=EXPR_GRAMMAR, max_nonterminals=3))

CGI_GRAMMAR: Grammar = {
    "<start>":
        ["<string>"],

    "<string>":
        ["<letter>", "<letter><string>"],

    "<letter>":
        ["<plus>", "<percent>", "<other>"],

    "<plus>":
        ["+"],

    "<percent>":
        ["%<hexdigit><hexdigit>"],

    "<hexdigit>":
        ["0", "1", "2", "3", "4", "5", "6", "7",
            "8", "9", "a", "b", "c", "d", "e", "f"],

    "<other>":  # Actually, could be _all_ letters
        ["0", "1", "2", "3", "4", "5", "a", "b", "c", "d", "e", "-", "_"],
}

for i in range(10):
    print(simple_grammar_fuzzer(grammar=CGI_GRAMMAR, max_nonterminals=10))

URL_GRAMMAR: Grammar = {
    "<start>":
        ["<url>"],
    "<url>":
        ["<scheme>://<authority><path><query>"],
    "<scheme>":
        ["http", "https", "ftp", "ftps"],
    "<authority>":
        ["<host>", "<host>:<port>", "<userinfo>@<host>", "<userinfo>@<host>:<port>"],
    "<host>":  # Just a few
        ["cispa.saarland", "www.google.com", "fuzzingbook.com"],
    "<port>":
        ["80", "8080", "<nat>"],
    "<nat>":
        ["<digit>", "<digit><digit>"],
    "<digit>":
        ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "<userinfo>":  # Just one
        ["user:password"],
    "<path>":  # Just a few
        ["", "/", "/<id>"],
    "<id>":  # Just a few
        ["abc", "def", "x<digit><digit>"],
    "<query>":
        ["", "?<params>"],
    "<params>":
        ["<param>", "<param>&<params>"],
    "<param>":  # Just a few
        ["<id>=<id>", "<id>=<nat>"],
}

for i in range(10):
    print(simple_grammar_fuzzer(grammar=URL_GRAMMAR, max_nonterminals=10))

TITLE_GRAMMAR: Grammar = {
    "<start>": ["<title>"],
    "<title>": ["<topic>: <subtopic>"],
    "<topic>": ["Generating Software Tests", "<fuzzing-prefix>Fuzzing", "The Fuzzing Book"],
    "<fuzzing-prefix>": ["", "The Art of ", "The Joy of "],
    "<subtopic>": ["<subtopic-main>",
                   "<subtopic-prefix><subtopic-main>",
                   "<subtopic-main><subtopic-suffix>"],
    "<subtopic-main>": ["Breaking Software",
                        "Generating Software Tests",
                        "Principles, Techniques and Tools"],
    "<subtopic-prefix>": ["", "Tools and Techniques for "],
    "<subtopic-suffix>": [" for <reader-property> and <reader-property>",
                          " for <software-property> and <software-property>"],
    "<reader-property>": ["Fun", "Profit"],
    "<software-property>": ["Robustness", "Reliability", "Security"],
}

titles: Set[str] = set()
while len(titles) < 10:
    titles.add(simple_grammar_fuzzer(
        grammar=TITLE_GRAMMAR, max_nonterminals=10))

#print(titles)

number_of_seeds = 10
seeds = [
    simple_grammar_fuzzer(grammar=URL_GRAMMAR,
    max_nonterminals=10) for i in range(number_of_seeds)]

print(seeds)

m = MutationFuzzer(seeds)

print([m.fuzz() for i in range(20)])

#simple nonterminal grammar definition
simple_nonterminal_grammar: Grammar = {
    "<start>": ["<nonterminal>"],
    "<nonterminal>": ["<left-angle><identifier><right-angle>"],
    "<left-angle>": ["<"],
    "<right-angle>": [">"],
    "<identifier>": ["id"]  # for now
}

nonterminal_grammar = copy.deepcopy(simple_nonterminal_grammar)
nonterminal_grammar["<identifier>"] = ["<idchar>", "<identifier><idchar>"]
nonterminal_grammar["<idchar>"] = ['a', 'b', 'c', 'd']  # for now

print(nonterminal_grammar)

def extend_grammar(grammar: Grammar, extension: Grammar = {}) -> Grammar:
    new_grammar = copy.deepcopy(grammar)
    new_grammar.update(extension)
    return new_grammar

def srange(characters: str) -> list[str]:
    """Construct a list with all characters in the string"""
    return [c for c in characters]

print(string.ascii_letters)
print(srange(string.ascii_letters)[:10])

nonterminal_grammar = extend_grammar(nonterminal_grammar, {
    "<idchar>": (
        srange(string.ascii_letters) + 
        srange(string.digits) + 
        srange("-_"))
})

print([simple_grammar_fuzzer(nonterminal_grammar, "<identifier>") for i in range(10)])
print("")

def crange(character_start: str, character_end: str) -> list[str]:
    return [chr(i)
            for i in range(ord(character_start), ord(character_end) + 1)]

#print(crange('0', '9'))
print(crange('a', 'z'))
print(string.ascii_letters)
print(srange(string.ascii_lowercase))
assert crange('a', 'z') == srange(string.ascii_lowercase)

