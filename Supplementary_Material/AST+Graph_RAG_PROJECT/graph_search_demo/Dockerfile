# 先通过 base 构建基础镜像，将服务器下载不下来的包，打包进去
FROM graph-search-demo-base:2.0.0 AS base

WORKDIR /app/api

COPY pyproject.toml poetry.lock ./

RUN poetry install --sync --no-cache --no-root

# Copy source code 通过 volums 进行映射
# COPY ./src /app/api/src
# COPY ./scripts /app/api/scripts
# COPY ./examples /app/api/examples

# 通过 volums 进行地址映射，不再把全部文件 copy 到镜像里
# COPY . /app/api/
# COPY ./examples/ajx_doc /app/api/data
# COPY ./examples/code /app/api/data

ENV PYTHONPATH=src

ENTRYPOINT ["poetry", "run", "/bin/bash", "./scripts/server.sh"]
