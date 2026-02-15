.PHONY: help install verify test test-llm test-quick test-stress clean

help:
	@echo "增强版智能体模拟器 - 可用命令:"
	@echo ""
	@echo "  make install      - 安装依赖"
	@echo "  make verify       - 验证 LLM 配置"
	@echo "  make test         - 运行基础测试（预设回复）"
	@echo "  make test-llm     - 运行 LLM 测试（需要 API 密钥）"
	@echo "  make test-quick   - 快速测试（5轮）"
	@echo "  make test-stress  - 压力测试（50轮）"
	@echo "  make clean        - 清理日志和报告"
	@echo ""

install:
	@echo "安装依赖..."
	pip install -r requirements.txt
	pip install tiktoken pyyaml
	@echo "✓ 依赖安装完成"

verify:
	@echo "验证 LLM 配置..."
	@python verify_llm_config.py

test:
	@echo "运行基础测试..."
	python enhanced_simulator.py --rounds 10

test-llm:
	@echo "运行 LLM 测试..."
	@if [ -z "$$DEEPSEEK_API_KEY" ] && [ -z "$$OPENAI_API_KEY" ]; then \
		echo "错误: 请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量"; \
		echo "推荐: export DEEPSEEK_API_KEY='your-key'"; \
		exit 1; \
	fi
	python enhanced_simulator.py --use-llm --rounds 10

test-quick:
	@echo "快速测试..."
	python enhanced_simulator.py --rounds 5

test-stress:
	@echo "压力测试..."
	python enhanced_simulator.py --rounds 50

test-medical:
	@echo "医疗 AI 场景测试..."
	python enhanced_simulator.py \
		--topic "人工智能在医疗领域的应用前景" \
		--description "讨论AI在医疗诊断、个性化治疗、药物研发等方面的技术进展" \
		--rounds 10

test-climate:
	@echo "气候变化场景测试..."
	python enhanced_simulator.py \
		--topic "应对气候变化的技术创新" \
		--description "探讨可再生能源、碳捕获、智慧城市等技术" \
		--rounds 10

clean:
	@echo "清理日志和报告..."
	rm -rf logs/*.log
	rm -rf reports/*
	@echo "✓ 清理完成"
