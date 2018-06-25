from flask import abort
from flask import current_app, jsonify
from flask import g
from flask import request
from flask import session

from info import constants
from info.models import *
from info.modules.index import index_blu
from flask import render_template

from info.utils.common import user_login_data
from info.utils.response_code import RET


@index_blu.route("/news_list")
def get_news_list():
    # 获取数据
    args_data = request.args
    cid = args_data.get("cid", 1)
    per_page = args_data.get("per_page", constants.HOME_PAGE_MAX_NEWS)
    page = args_data.get("page", 1)

    # 校验参数
    cid = int(cid)
    per_page = int(per_page)
    page = int(page)

    # 获取数据库中数据
    filters = [News.status == 0]
    if cid != 1:
        filters.append(News.category_id == cid)

    paginates = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)

    # 创建列表保存对象
    news_list = []
    news_model = paginates.items
    # 获取到总页数
    total_page = paginates.pages
    current_page = paginates.page
    for news in news_model:
        news_list.append(news.to_basic_dict())

    # 字典保存
    data = {
        "news_list": news_list,
        "total_page": total_page,
        "current_page": current_page
    }

    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@index_blu.route('/')
@user_login_data
def index():
    """路由地址"""
    user = g.user

    # 点击排行榜的设置
    news_list = None

    # 数据库查询数据
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []

    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())

    # 首页分类的设置
    categories = None
    # 数据库查询
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)

    category_list = []

    for category in categories:
        category_list.append(category.to_dict())

    data = {
        # 为了方便返回所需要的数据, 我们开发中一般会自定义to_dict函数
        # user有值, 就返回前面的数据, 没有值, 就返回None --> 模板就解析不出来数据
        # 模型转字典
        'user': user.to_index_dict() if user else None,
        "click_news_list": click_news_list,
        "category_list": category_list
    }

    return render_template('news/index.html', data=data)


@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')
