from info.modules.index import index_blu


@index_blu.route('/index')
def index():
    """路由地址"""
    return "Hello world"
