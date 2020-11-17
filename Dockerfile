
FROM python:3.8.6-buster

# Make a directory for our application
WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uwsgi

# download the required nltk data
RUN python -c '\
import nltk;\
nltk.download("punkt");\
nltk.download("averaged_perceptron_tagger");\
nltk.download("stopwords")'

# this is a temporary solution
# copy the sample data
COPY people-simple.json allocation.json /

# Copy our source code
COPY bot ./bot

# copy environment variables
COPY .env ./
