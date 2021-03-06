"""AUCR main driver init database model creation and import plugins."""
# coding=utf-8
import logging
import os
from config import Config
from elasticsearch import Elasticsearch
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from logging.handlers import SMTPHandler, RotatingFileHandler
from yaml_info.yamlinfo import YamlInfo
from aucr_app.plugins import init_task_plugins

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l("Please log in to access this page.")
mail = Mail()
moment = Moment()
babel = Babel()


def create_app(config_class=Config):
    """Return AUCR app flask object."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='AUCR Failure',
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if app.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/aucr.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s '
                                                    '[in %(pathname)s:%(lineno)d]'))
    app.logger.setLevel(logging.INFO)
    app.logger.info('AUCR startup')

    return app


def init_app(app):
    """AUCR app flask function init."""
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    init_task_plugins(app)
    return app


def aucr_app():
    """AUCR app flask function framework create and get things started."""
    YamlInfo("projectinfo.yml", "projectinfo", "LICENSE")
    app = create_app()
    app = init_app(app)
    app.secret_key = app.config['SECRET_KEY']
    app.app_context().push()
    db.create_all()
    return app


@babel.localeselector
def get_locale():
    """Get default language function returns systems default in config."""
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])
