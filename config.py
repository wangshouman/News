import logging
import redis


class Config(object):
    SECRET_KEY = "yyZVXT4f9GdyfVyovrHH07D0NI2+lZ+F"
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "127.0.0.1"
    REDIS_POST = 6379
    SESSION_TYPE = "redis"
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_POST)
    PERMANENT_SESSION_LIFETIME = 86400
    LOG_LEVEL = logging.DEBUG

class DevelopmenConfig(Config):
    """开发模式下配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产模式下配置"""
    DEBUG = False
    LOG_LEVEL = logging.ERROR
