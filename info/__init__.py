from logging.handlers import RotatingFileHandler
from flask_wtf.csrf import generate_csrf
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from config import *

db = SQLAlchemy()
redis_store = None  # type:redis.StrictRedis


def create_app(config_name):
    setup_log(config_name)
    app = Flask(__name__)
    app.config.from_object(config_name)
    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host=config_name.REDIS_HOST, port=config_name.REDIS_POST, decode_responses=True)
    CSRFProtect(app)
    Session(app)

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    from info.modules.index import index_blu
    app.register_blueprint(index_blu)

    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)

    from info.modules.news import news_blue
    app.register_blueprint(news_blue)

    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu)

    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu)

    # 导入自定义文件名
    from info.utils.common import do_index_class
    # 注册自定义函数
    app.add_template_filter(do_index_class, "index_class")


    return app

def setup_log(config_name):
    """配置日志"""

    # 设置日志的记录等级
    logging.basicConfig(level=config_name.LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)