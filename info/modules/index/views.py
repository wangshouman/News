from flask import current_app

from info.modules.index import index_blu
from flask import render_template


@index_blu.route('/')
def index():
    """路由地址"""
    return render_template('news/index.html')


@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')
