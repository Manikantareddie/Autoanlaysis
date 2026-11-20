FROM python:3.11-slim
RUN useradd --create-home --uid 10001 analyst
WORKDIR /workspace
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY runner.py /workspace/runner.py
USER analyst
ENTRYPOINT ["python", "/workspace/runner.py"]
