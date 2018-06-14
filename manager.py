from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from config import *
from info import create_app, db

app = create_app(DevelopmenConfig)
manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)

# @app.route('/')
# def index():
#     """路由地址"""
#     return "Hello world"

if __name__ == '__main__':
    manager.run()
