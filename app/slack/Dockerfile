# Use an official Python runtime as a base image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=3000

# set working directory
WORKDIR /usr/src/app

# copy requirements and install
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app sources (bot.py and optional src/)
COPY bot.py ./ 
COPY src/ ./src/

# expose port (matching Flask default)
EXPOSE 3000

# run the bot
CMD ["python", "bot.py"]
