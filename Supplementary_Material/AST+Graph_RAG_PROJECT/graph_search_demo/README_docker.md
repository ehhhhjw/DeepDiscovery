
## docker base 镜像构建
docker build -f Dockerfile_base -t graph-search-demo-base:2.0.0 .

## docker 项目镜像构建
docker build -f Dockerfile -t graph-search-demo:2.0.0 .

# 导出镜像
docker save -o xxx.tar image:tag
# 导入镜像
docker load -i xxx.tar

## 本地 docker 启动
docker compose -f docker-compose.local.yaml -p graph-search up -d

## 注意
1. 重新修改镜像之后，注意修改 对应的 docker-compose-xxx.yaml 中对应的镜像版本



# 最终操作
## code 线上 - 目录 graph_search_demo_production  port:5002
1. 启动  docker compose -f docker-compose.yaml -p graph-search-production up -d
2. 停止 docker compose -p graph-search-production down
3. 重启 docker compose -f docker-compose.yaml -p graph-search-production restart chat_worker
## code 灰度 - 目录 graph_search_demo_gray  port:5001
1. 启动  docker compose -f docker-compose-gray.yaml -p graph-search-gray up -d
2. 停止 docker compose -p graph-search-gray down
3. 重启  docker compose -f docker-compose-gray.yaml -p graph-search-gray restart chat_worker

## 文档线上 - 目录 graph_search_demo-onlydocs port:5003
1. 启动  docker compose -f docker-compose-docs.yaml -p graph-search-docs-production up -d
2. 停止 docker compose -p graph-search-docs-production down
3. 重启  docker compose -f docker-compose-docs.yaml -p graph-search-docs-production restart chat_worker

## 文档灰度 - 目录 graph_search_demo-onlydocs-gray port:5004
1. 启动  docker compose -f docker-compose-docs-gray.yaml -p graph-search-docs-gray up -d
2. 停止 docker compose -p graph-search-docs-gray down
3. 重启  docker compose -f docker-compose-docs-gray.yaml -p graph-search-docs-gray restart chat_worker
