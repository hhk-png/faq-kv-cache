.PHONY: help api celery worker redis test install

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:        ## 安装后端依赖
	cd backend && python -m pip install -r requirements.txt

test:           ## 运行后端测试
	cd backend && python -m pytest tests/ -v

api:            ## 启动 FastAPI 后端 (http://localhost:8000)
	cd backend && python -m uvicorn app.main:app --reload --port 8000

redis:          ## 启动 Redis
	redis-server

worker:         ## 启动 Celery Worker
	cd backend && python -m celery -A app.tasks.celery_app worker --loglevel=info

celery: worker  ## 同 worker

frontend-install: ## 安装前端依赖
	cd frontend && pnpm install

frontend:       ## 启动前端开发服务器 (http://localhost:5173)
	cd frontend && pnpm dev

frontend-build: ## 构建前端
	cd frontend && pnpm build

all:            ## 先运行测试，验证全部通过
	python -m pytest backend/tests/ -v && echo "✅ 全部通过"
