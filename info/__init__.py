from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from config import *

db = SQLAlchemy()
redis_store = None


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config_name)
    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host=config_name.REDIS_HOST, port=config_name.REDIS_POST)
    CSRFProtect(app)
    Session(app)

    return app
