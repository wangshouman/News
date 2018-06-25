import functools
# 自定义过滤器
from flask import current_app
from flask import g
from flask import session

from info.models import User


def do_index_class(index):
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    else:
        return ""


def user_login_data(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 执行功能代码
        #  获取当前的登录的用户id
        user_id = session.get("user_id", None)
        # 通讯id获取的用户信息
        user = None
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)

        # 将user对象存在临时变量中,随请求而生,请求完而灭
        g.user = user

        return func(*args, **kwargs)

    return wrapper
