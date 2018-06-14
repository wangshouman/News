from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import redis
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand




class Config(object):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "127.0.0.1"
    REDIS_POST = 6379
    SESSION_TYPE = "redis"
    SESSION_USE_SIGNER = True
    redis_store = redis.StrictRedis(host=REDIS_HOST, port=REDIS_POST)
    PERMANENT_SESSION_LIFETIME = 86400






app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
redis_store = redis.StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_POST)
CSRFProtect(app)
Session(app)
manager = Manager(app)
Migrate(app,db)
manager.add_command("db",MigrateCommand)


@app.route('/')
def index():
    """路由地址"""
    return "Hello world"

if __name__ == '__main__':
    manager.run()
