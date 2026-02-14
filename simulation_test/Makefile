.PHONY: help install check test-basic test-high-freq test-closing test-cancel test-all clean

help:
	@echo "双智能体对话模拟测试 - 可用命令:"
	@echo ""
	@echo "  make install        - 安装依赖"
	@echo "  make check          - 检查环境配置"
	@echo "  make test-basic     - 运行基本对话测试"
	@echo "  make test-high-freq - 运行高频消息测试（触发摘要）"
	@echo "  make test-closing   - 运行话题关闭测试"
	@echo "  make test-cancel    - 运行取消关闭测试"
	@echo "  make test-all       - 运行所有测试"
	@echo "  make clean          - 清理临时文件"
	@echo ""

install:
	@echo "安装依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

check:
	@echo "检查环境配置..."
	python check_environment.py

test-basic:
	@echo "运行基本对话测试..."
	python run_simulation.py --scenario basic

test-high-freq:
	@echo "运行高频消息测试..."
	python run_simulation.py --scenario high-freq

test-closing:
	@echo "运行话题关闭测试..."
	python run_simulation.py --scenario closing

test-cancel:
	@echo "运行取消关闭测试..."
	python run_simulation.py --scenario cancel

test-all:
	@echo "运行所有测试..."
	python run_simulation.py --scenario all

clean:
	@echo "清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ 清理完成"
