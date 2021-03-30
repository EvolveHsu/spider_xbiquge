#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@author:Evolve Hsu
@file:batch_thread_book.py
@time:2021/03/28
"""
import re
import urllib
import threading
from urllib import request, error  # 制定URL 获取网页数据

from bs4 import BeautifulSoup  # 网页解析 获取数据
import sqlite3  # sqlite3 数据库操作
import time
from book import NewBook
from fake_useragent import UserAgent

headers = {
    'User-Agent': ' Mozilla/5.0 (Windows NT 10.0 Win64 x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 Edg/89.0.774.54'
    # 'User-Agent': UserAgent(verify_ssl=False).random
}
parent_url = 'http://www.xbiquge.me'


# 异步线程对象
class MyThread(threading.Thread):

    def __init__(self, func, book, book_list):
        threading.Thread.__init__(self)
        self.book = book
        self.book_list = book_list
        self.func = func

    def run(self):
        self.func(self.book, self.book_list)


# 获取小说首页html
def get_index_html(url):
    while True:
        request = urllib.request.Request(url=url, headers=headers)
        try:
            resp = urllib.request.urlopen(request)
            html = resp.read().decode("utf-8")
            break
        except urllib.error.URLError as e:
            print(e)
            print("异常链接: " + url)
            time.sleep(5)
    return html


# 获取章节list
def getElementList(url):
    link_list = []
    # 获取首页
    index = parent_url + url
    html = get_index_html(index)
    # 解析首页
    bs = BeautifulSoup(html, "lxml")
    elementList = bs.find('div', id="list").find_all('a')
    for data in elementList:
        # 根据 href名提取内容
        link = data.get('href')
        if link != 'chapter.html':
            link_list.append(link)
    set(link_list)
    return link_list


# 解析数据
def resolve_element(book, book_list):
    text = []
    url = parent_url + book.element
    error_count = 0
    while True:
        print("准备解析 html: " + url)
        request = urllib.request.Request(url=url, headers=headers)
        try:
            resp = urllib.request.urlopen(request)
            if resp.code == 200:
                html = resp.read().decode("utf-8")
                bs = BeautifulSoup(html, "lxml")
                for item in bs.find('div', id="content").find_all('p'):
                    text.append(item.text.replace('xbiquge/最快更新！无广告！', ''))
                # 标题
                book.__setattr__('title', bs.select('body > div.content_read > div > div.bookname > h1 > a')[0].text)
                # 链接
                book.__setattr__('link', url)
                # 序号
                book.__setattr__('number', int(url.split('_')[1].replace('.html', '')))
                # 内容
                book.__setattr__('text', ''.join(text))
                book_list.append(book)
                break
        except Exception as e:
            error_count = error_count + 1
            if error_count == 2:
                print("错误到达2次 链接异常: %s" % url)
                break
            print(e)
            print('发生异常 休息5秒: ' + url)
            time.sleep(5)
    print("本线程任务完成: " + url)


# 批量保存数据到数据库
def save_new_book(book_list):
    print('准备保存数据 数量: %d' % len(book_list))
    db_path = "newbook.db"
    # init_db(db_path)  # 初始化数据库
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    sql = "insert into new_book (book_name,author,number,title ,link, data) values"
    total = 0
    for book in book_list:
        values = "('" + book.book_name + "'" + ',' + "'" + book.author + "'" + ',' + "'" + str(
            book.number) + "'" + ',' + "'" + book.title + "'" + ',' + "'" + book.link + "'" + ',' + "'" + book.text + "')"
        total = total + 1
        if total == len(book_list):
            values = values + ';'
        else:
            values = values + ','
        sql = sql + values
    c.execute(sql)
    conn.commit()
    c.close()
    conn.close()


# 数据库表初始化
def init_db(savePath):
    sql = '''
            create table new_book
            (
                id integer primary key autoincrement,
                book_name varchar ,
                author varchar,
                number integer ,
                title varchar,
                link varchar ,
                data text 
            );
        '''
    conn = sqlite3.connect(savePath)
    c = conn.cursor()
    c.execute(sql)
    conn.commit()
    conn.close()
    print("init_db success")


# 根据书名查找书
def search_book_name(book_name):
    search_url = 'https://www.xbiquge.me/search/result.html?searchkey=' + urllib.parse.quote(book_name)
    while True:
        request = urllib.request.Request(url=search_url, headers=headers)
        try:
            resp = urllib.request.urlopen(request)
            html = resp.read().decode("utf-8")
            break
        except urllib.error.URLError as e:
            print(e)
            time.sleep(1)
    return html


# 根据查询结果页 保存结果集
def resolve_book_base(book_search_html):
    book_name_list = []
    book_link_list = []
    book_author_list = []
    bs = BeautifulSoup(book_search_html, "lxml")
    name_link_list = bs.find_all('span', class_=re.compile('s2'))
    author_list = bs.find_all('span', class_=re.compile('s4'))
    total = 0
    # 2个集合一起循环解析内容并返回
    for name_link, author in zip(name_link_list, author_list):
        if total != 0:
            book_name_list.append(name_link.text)
            book_link_list.append(name_link.a.get('href'))
            book_author_list.append(author.text)
        total = total + 1
    return book_name_list, book_link_list, book_author_list


# 保存小说到文件
def generate_file(book_list, file_name, author, file_path):
    print('准备写入数据: ' + file_name)
    fo = open(file_path + file_name + '-' + author + '.txt', "ab+")  # 打开小说文件
    for book in book_list:
        # 以二进制写入章节题目 需要转换为utf-8编码，否则会出现乱码
        fo.write(('\r' + book.title + '\r\n').encode('UTF-8'))
        # 以二进制写入章节内容
        fo.write((book.text).encode('UTF-8'))
    fo.close()  # 关闭小说文件


if __name__ == '__main__':
    book_name = '烂柯棋缘'
    # book_name = '从精神病院走出的强者'
    # book_name = '斗破苍穹'
    file_path = 'C://Users//24855//Desktop//爬虫小说下载//'
    book_search_html = search_book_name(book_name)
    book_name_list, book_link_list, book_author_list = resolve_book_base(book_search_html)
    book_list = []
    for baseUrl, name, author in zip(book_link_list, book_name_list, book_author_list):
        elementList = getElementList(baseUrl)
        # 单线程测试用
        # resolve_element(NewBook(elementList[0], book_name, author, None, None, None, None))

        # 多线程 resolve_element为执行方法
        threadList = [MyThread(resolve_element, NewBook(element, book_name, author, None, None, None, None), book_list)
                      for element in elementList]
        startTotal = 0
        for t in threadList:
            startTotal = startTotal + 1
            t.setDaemon(True)
            t.start()
            if startTotal == 10:
                sleep_time = 5
                print('启动线程达到 %d 条休息 %d 秒' % (startTotal, sleep_time))
                time.sleep(sleep_time)
                startTotal = 0
        for i in threadList:
            i.join()
        # 根据章节编号排序
        book_list.sort()
        # 生成文件
        generate_file(book_list, book_name, author, file_path)
        book_list = []
    # 保存数据到数据库
    # print("爬取数据完成 准备保存数据")
    # save_new_book(book_list)
