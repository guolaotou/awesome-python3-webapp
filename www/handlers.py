#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Laotou Guo'

'url handlers '

import asyncio, re, time, json, logging, hashlib, base64
from coroweb import Handler_decorator
from coroweb import get
from models import User, Comment, Blog, next_id


@get('/')
async def index(request):
    users = await User.findAll()
    return {
        '__template__': 'test.html',
        'users': users
    }