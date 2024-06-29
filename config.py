import os

SECRET_KEY = os.urandom(24)

MONGO_URI = os.environ.get('MONGODB_URI')

