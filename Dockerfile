
FROM python:3.8.6-buster

# Make a directory for our application
WORKDIR /app

# Install server first, so doesn't need to be rebuilt as often
RUN pip install --no-cache-dir uwsgi

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# download the required nltk data, to user accessible directory
RUN python -c '\
import nltk;\
directory = "/usr/share/nltk_data";\
nltk.download("punkt", directory);\
nltk.download("averaged_perceptron_tagger", directory);\
nltk.download("stopwords", directory)'

# this is a temporary solution
# copy the sample data
COPY people-simple.json allocation.json /

# Copy our source code
COPY bot ./bot

# copy environment variables
COPY .env ./

# Create a group and user for uwsgi
RUN adduser --system --group uwsgi
# change the file owner and group for the app directory
RUN chown -R uwsgi:uwsgi /app

# Switch user
USER uwsgi
