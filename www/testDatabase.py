#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import orm
from models import User, Blog, Comment
import asyncio

loop = asyncio.get_event_loop()
async def test():
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='admin', db='awesome')

    u = User(name='Test8', email='test8@example.com', passwd='1234567890', image='about:blank', id='1238')

    await u.save()
    await orm.destory_pool()

# 把协程放到事件循环中执行
loop.run_until_complete(test())



# #以下为测试
# loop = asyncio.get_event_loop()
# loop.run_until_complete(create_pool(host='127.0.0.1', port=3306, user='root', password='admin',db='awesome', loop=loop))
# rs = loop.run_until_complete(select('select * from users',None))
# #获取到了数据库返回的数据
# print("heh:%s" % rs)
