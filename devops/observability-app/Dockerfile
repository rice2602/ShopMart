# Build Flask App on Python Alpine to ensure a thin, lightweight container image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies needed for python package compilation (like pandas, pyarrow)
RUN apk add --no-cache libstdc++ g++ make

# Copy requirements
COPY devops/observability-app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and directories (preserving structure)
COPY devops/observability-app/app.py .
COPY devops/observability-app/templates/ templates/

# Also copy src pipeline so that simulation endpoint functions correctly
COPY src/ /src/
# Set PYTHONPATH so app can resolve local pipeline packages
ENV PYTHONPATH="/:${PYTHONPATH}"

# Expose default Flask port
EXPOSE 5000

# Define execution entrypoint
CMD ["python", "app.py"]
