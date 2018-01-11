#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Laotou Guo'

'url handlers '

import markdown2
import asyncio, re, time, json, logging, hashlib, base64
from coroweb import Handler_decorator
from aiohttp import web
from coroweb import get, post
from models import User, Comment, Blog, next_id
from APIError import APIError, APIValueError, APIResourceNotfoundError, APIPermissionError
from config import configs


#day 7
# @get('/')
# async def index(request):
#     users = await User.findAll()
#     return {
#         '__template__': 'test.html',
#         'users': users
#     }

# Day 8(构建前端)
# 首页
@get('/')
async def index(request, *, page='1'):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    # blogs = [
    #     Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
    #     Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
    #     Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200)
    # ]
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'blogs': blogs,
        'page': page,
        '__user__': request.__user__
    }

# Day 9 编写api （主要是test）
# @get('/api/users')
# async def api_get_users():
#     users = await User.findAll(orderBy='created_at desc')
#     for u in users:
#         u.passwd = '******'
#     return dict(users = users)

# Day 10 编写用户注册和登录API


COOKIE_NAME = 'awesession'#用来在set_cookie中命名
_COOKIE_KEY = configs['session']['secret']#导入默认设置


#------------------------------------------------FUNCTION-------------------------------------------------------


# 检测是否登录且是否是管理员
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

# 制作cookie的数值，即set_cookie的value
def user2cookie(user, max_age):
    # build cookie string by: id-expires-sha1（id-到期时间-摘要算法）
    expires = str(time.time()+max_age)
    s = '%s-%s-%s-%s'%(user.id, user.passwd, expires, _COOKIE_KEY)#s的组成：id, passwd, expires, _COOKIE_KEY
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]#再把s进行摘要算法
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

_RE_EMAIL = re.compile(r'^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+){0,4}@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+){0,4}$') # Python正则表达式验证邮箱 http://blog.csdn.net/catkint/article/details/55260281
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

# 解密cookie
async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if float(expires) < time.time():
            return None
        user = await User.find(uid)
        if not user:
            return None

        # 利用用户id,加密后的密码,失效时间,加上cookie密钥,组合成待加密的原始字符串
        # 再对其进行加密,与从cookie分解得到的sha1进行比较.若相等,则该cookie合法
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('Invalid sha1')
            return None
        user.passwd = "******"
        return user
    except Exception as e:
        logging.exception(e)
        return None

# 选择页面
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

# 定义选取数量
class Page(object):
    def __init__(self, item_count, page_index = 1, page_size = 10): #参数依次是：数据库博客总数，初始页，一页显示博客数
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count //page_size + (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index # 初始页
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count # 是否有下一页
        self.has_previous = self.page_index > 1 # 是否有上一页
    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__


#------------------------------------------------映射页面--------------------------------------------------------

# 首页在上面 #@get('/')

# 显示注册页面
@get('/register')
async def register():
    return {
        '__template__': 'register.html'
    }

# 显示登录页面
@get('/signin')
async def signin():
    return {
        '__template__': 'signin.html'
    }

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

# 显示创建博客页面
@get('/manage/blogs/create')
async def manage_create_blog(request):
    return{
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs',
        '__user__': request.__user__
    }

# 博客列表页面
@get('/manage/blogs')
async def manage_blogs(request, *, page='1'):
    return{
        '__template__':'manage_blogs.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }

# 修改博客页面
@get('/manage/blogs/edit')
def manage_edit_blog(request, *, id):
    return{
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s' % id,
        '__user__': request.__user__
    }
# @get('/manage/blogs/edit')
# def manage_edit_blog(*, id):
#     return{
#         '__template__': 'manage_blog_edit.html',
#         'id': id,
#         'action': '/api/blogs/%s' % id
#     }

# 显示博客详情页面
@get('/blog/{id}')
async def get_blog(request,*,id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments,
        '__user__': request.__user__
    }

#评论列表页面
@get('/manage/comments')
def manage_comments(request, *, page='1'):
    return{
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }

# 用户列表页面
@get('/manage/users')
def manage_users(request, *, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page),
        '__user__': request.__user__
    }

#--------------------------------------------------API----------------------------------------------------------

# 注册接口
@post('/api/users')
async def api_register_user(*,name,email,passwd):
    if not name or not name.strip():#如果名字是空格或没有返错
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd and not _RE_SHA1.match(passwd):
        raise APIValueError('password')
    users = await User.findAll(where='email=?', args=[email])# 查询邮箱是否已注册，查看ORM框架源码
    if len(users) > 0:
        raise APIError('register:failed','email','Email is already in use.')

    # 接下来就是注册到数据库上,具体看会ORM框架中的models源码
    # 这里用来注册数据库表id不是使用Use类中的默认id生成，而是调到外部来，原因是后面的密码存储摘要算法时，会把id使用上。
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())#
    await user.save()

    #制作cookie返回返回浏览器客户端
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'  # 掩盖passwd
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 验证登录信息接口
@post('/api/authenticate')
async def authenticate(*,email,passwd):
    if not email:
        raise APIValueError('email')
    if not passwd:
        raise APIValueError('passwd')
    users = await User.findAll(where='email=?',args=[email]) # 在数据库中查找email,将以list形式返回
    if len(users) == 0:
        raise APIValueError('email','Email not exist.')
    user = users[0]# 取得用户记录.事实上,就只有一条用户记录,只不过返回的是list

    #把登录密码转化格式并进行摘要算法
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode("utf-8"))
    sha1.update(b":")
    sha1.update(passwd.encode("utf-8"))
    if user.passwd != sha1.hexdigest():
        raise APIValueError("passwd", "Invalid password")

    # 用户登录之后,同样的设置一个cookie,与注册用户部分的代码完全一样
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = "*****"
    r.content_type = "application/json"
    r.body = json.dumps(user, ensure_ascii=False).encode("utf-8")
    return r

# API: 获取用户
@get('/api/users')
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

# API：用户登出
@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/') #回到首页
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True) #重置cookie
    logging.info('user signed out.')
    return r

# API: 查看博客 by id,详情见manage_blog_edit.html
@get('/api/blog/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog

#API: 创建博客
@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'Name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'Summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'Content cannot be empty.')
    blog = Blog(user_id = request.__user__.id, user_name = request.__user__.name, user_image = request.__user__.image, name = name.strip(), summary = summary.strip(), content = content.strip())
    await blog.save()
    return blog

#API: 获取博客（批量）,见manage_blogs.html
@get('/api/blogs')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')#查询日志总数
    p = Page(num, page_index)
    if num == 0: #数据库没日志
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit)) #选取对应的日志
    return dict(page=p, blogs=blogs)#返回管理页面信息，及显示日志数

#API: 获取博客详情，详情见manage_blog_edit.html
@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog

#API：修改博客，详情见manage_blog_edit.html
@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content):
    check_admin(request)
    blog = await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    await blog.update()
    return blog

#API: 删除博客
@post('/api/blogs/{id}/delete')
async def api_delete_blog(request,*,id):
    check_admin(request)
    blog = await Blog.find(id)
    await blog.remove()
    return dict(id=id)

#API: 获取评论列表，见manage_comments.html
@get('/api/comments')
async def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments = comments)
#API: 创建评论
@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
    user = request.__user__  # 登录再说
    if not user:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotfoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    await comment.save()
    return comment

@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotfoundError('Comment')
    await c.remove()
    return dict(id=id)























