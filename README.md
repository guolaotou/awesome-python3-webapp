这个项目是廖雪峰网站上python教学最后的实战部分。
链接：https://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000/001432170876125c96f6cc10717484baea0c6da9bee2be4000


部署之前需要用pip的方法异步框架aiohttp，前端模板引擎jinja2以及MySQL的Python异步驱动程序aiomysql。然后把config_default里的数据库用户名密码改成自己的。之后在www下打开终端，输入python app.py，如果成功运行起来，就去浏览器输入localhost:9000，看一下首页吧！然后发帖的话，需要管理权限，注册的用户默认admin属性都是0，需要手动去数据库里把你某位用户的admin改成1，这样就可以用这个用户发帖了，登录后在上面导航页也能看到管理端。
