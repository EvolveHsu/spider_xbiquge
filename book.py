#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@author:Evolve Hsu
@file:book.py
@time:2021/03/25
"""
from typing import Any


class NewBook:
    def __init__(self, element, book_name, author, title, link, number, text):
        self.element = element
        self.book_name = book_name
        self.author = author
        self.title = title
        self.link = link
        self.number = number
        self.text = text

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)

    def __lt__(self, other):  # override <操作符
        if self.number < other.number:
            return True
        return False
