FROM python:3.11-slim
WORKDIR /workspace
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY . .
ENTRYPOINT ["stackwise"]
CMD ["--help"]
