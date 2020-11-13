
FROM python:3.8.6-buster

# Make a directory for our application
WORKDIR /app
# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy our source code
COPY /bot .

# Run the application
CMD ["python", "app.py"]