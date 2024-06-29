import os

SECRET_KEY = os.urandom(24)

MONGO_URI = os.environ.get('MONGODB_URI')

UNAME = os.environ.get('UNAME')
PWORD = os.environ.get('PWORD')
