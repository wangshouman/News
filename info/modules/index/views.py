from flask import current_app
from flask import session

from info.models import User
from info.modules.index import index_blu
from flask import render_template


@index_blu.route('/')
def index():
    """路由地址"""
    #  获取当前的登录的用户id
    user_id = session.get("user_id")
    # 通讯id获取的用户信息
    user = None
    if user_id:
        try:
            user = User.query.get(user_id)
        except Exception as e:
            current_app.logger.error(e)

    data = {
        # 为了方便返回所需要的数据, 我们开发中一般会自定义to_dict函数
        # user有值, 就返回前面的数据, 没有值, 就返回None --> 模板就解析不出来数据
        # 模型转字典
        'user': user.to_index_dict() if user else None
    }

    return render_template('news/index.html', data=data)


@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')
