FROM python:3.8.6-buster

# Make a directory for our application
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the sample data
COPY people-simple.json allocation.json data/

# Copy our source code
COPY *.py ./
