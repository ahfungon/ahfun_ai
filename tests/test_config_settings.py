"""Tests for configuration settings module.

This module tests the configuration management using Pydantic settings.
Validates: Requirements 6.3, 8.7
"""
import os
import pytest
from config.settings import Settings


class TestSettingsDefaults:
    """Test default configuration values."""
    
    def test_summary_threshold_default(self):
        """Test SUMMARY_THRESHOLD has correct default value of 8000."""
        settings = Settings()
        assert settings.summary_threshold == 8000
    
    def test_closing_timeout_default(self):
        """Test CLOSING_TIMEOUT has correct default value of 5 minutes (300 seconds)."""
        settings = Settings()
        assert settings.closing_timeout == 300
    
    def test_max_retries_default(self):
        """Test MAX_RETRIES has correct default value of 3."""
        settings = Settings()
        assert settings.max_retries == 3
    
    def test_retry_delays_default(self):
        """Test RETRY_DELAYS has correct default value of [1, 2, 4]."""
        settings = Settings()
        assert settings.retry_delays == "1,2,4"
        assert settings.retry_delays_list == [1, 2, 4]
    
    def test_database_url_default(self):
        """Test database URL has a default value."""
        settings = Settings()
        # PostgreSQL is the only supported database
        assert "postgresql://" in settings.database_url
    
    def test_redis_url_default(self):
        """Test Redis URL has a default value."""
        settings = Settings()
        assert settings.redis_url == "redis://localhost:6379/0"
    
    def test_openclaw_api_url_default(self):
        """Test OpenClaw API URL has a default value."""
        settings = Settings()
        assert settings.openclaw_api_url == "https://api.openclaw.example.com/v1"
    
    def test_deepseek_api_url_default(self):
        """Test DeepSeek API URL has a default value."""
        settings = Settings()
        assert settings.deepseek_api_url == "https://api.deepseek.com/v1"
    
    def test_celery_broker_url_default(self):
        """Test Celery broker URL has a default value."""
        settings = Settings()
        assert settings.celery_broker_url == "redis://localhost:6379/0"
    
    def test_celery_result_backend_default(self):
        """Test Celery result backend has a default value."""
        settings = Settings()
        assert settings.celery_result_backend == "redis://localhost:6379/0"
    
    def test_celery_max_concurrent_tasks_default(self):
        """Test Celery max concurrent tasks has correct default value of 5."""
        settings = Settings()
        assert settings.celery_max_concurrent_tasks == 5
    
    def test_api_host_default(self):
        """Test API host has a default value."""
        settings = Settings()
        assert settings.api_host == "0.0.0.0"
    
    def test_api_port_default(self):
        """Test API port has a default value."""
        settings = Settings()
        assert settings.api_port == 8000


class TestSettingsEnvironmentVariables:
    """Test configuration loading from environment variables."""
    
    def test_summary_threshold_from_env(self, monkeypatch):
        """Test SUMMARY_THRESHOLD can be overridden by environment variable."""
        monkeypatch.setenv("SUMMARY_THRESHOLD", "10000")
        settings = Settings()
        assert settings.summary_threshold == 10000
    
    def test_closing_timeout_from_env(self, monkeypatch):
        """Test CLOSING_TIMEOUT can be overridden by environment variable."""
        monkeypatch.setenv("CLOSING_TIMEOUT", "600")
        settings = Settings()
        assert settings.closing_timeout == 600
    
    def test_max_retries_from_env(self, monkeypatch):
        """Test MAX_RETRIES can be overridden by environment variable."""
        monkeypatch.setenv("MAX_RETRIES", "5")
        settings = Settings()
        assert settings.max_retries == 5
    
    def test_retry_delays_from_env(self, monkeypatch):
        """Test RETRY_DELAYS can be overridden by environment variable."""
        monkeypatch.setenv("RETRY_DELAYS", "2,4,8,16")
        settings = Settings()
        assert settings.retry_delays == "2,4,8,16"
        assert settings.retry_delays_list == [2, 4, 8, 16]
    
    def test_database_url_from_env(self, monkeypatch):
        """Test database URL can be overridden by environment variable."""
        test_url = "postgresql://user:pass@localhost/testdb"
        monkeypatch.setenv("DATABASE_URL", test_url)
        settings = Settings()
        assert settings.database_url == test_url
    
    def test_redis_url_from_env(self, monkeypatch):
        """Test Redis URL can be overridden by environment variable."""
        test_url = "redis://redis-server:6379/1"
        monkeypatch.setenv("REDIS_URL", test_url)
        settings = Settings()
        assert settings.redis_url == test_url
    
    def test_openclaw_api_key_from_env(self, monkeypatch):
        """Test OpenClaw API key can be set from environment variable."""
        test_key = "test-openclaw-key-123"
        monkeypatch.setenv("OPENCLAW_API_KEY", test_key)
        settings = Settings()
        assert settings.openclaw_api_key == test_key
    
    def test_openclaw_api_url_from_env(self, monkeypatch):
        """Test OpenClaw API URL can be overridden by environment variable."""
        test_url = "https://custom-openclaw.example.com/api"
        monkeypatch.setenv("OPENCLAW_API_URL", test_url)
        settings = Settings()
        assert settings.openclaw_api_url == test_url
    
    def test_deepseek_api_key_from_env(self, monkeypatch):
        """Test DeepSeek API key can be set from environment variable."""
        test_key = "test-deepseek-key-456"
        monkeypatch.setenv("DEEPSEEK_API_KEY", test_key)
        settings = Settings()
        assert settings.deepseek_api_key == test_key
    
    def test_deepseek_api_url_from_env(self, monkeypatch):
        """Test DeepSeek API URL can be overridden by environment variable."""
        test_url = "https://custom-deepseek.example.com/api"
        monkeypatch.setenv("DEEPSEEK_API_URL", test_url)
        settings = Settings()
        assert settings.deepseek_api_url == test_url
    
    def test_celery_broker_url_from_env(self, monkeypatch):
        """Test Celery broker URL can be overridden by environment variable."""
        test_url = "redis://celery-broker:6379/2"
        monkeypatch.setenv("CELERY_BROKER_URL", test_url)
        settings = Settings()
        assert settings.celery_broker_url == test_url
    
    def test_celery_result_backend_from_env(self, monkeypatch):
        """Test Celery result backend can be overridden by environment variable."""
        test_url = "redis://celery-backend:6379/3"
        monkeypatch.setenv("CELERY_RESULT_BACKEND", test_url)
        settings = Settings()
        assert settings.celery_result_backend == test_url
    
    def test_celery_max_concurrent_tasks_from_env(self, monkeypatch):
        """Test Celery max concurrent tasks can be overridden by environment variable."""
        monkeypatch.setenv("CELERY_MAX_CONCURRENT_TASKS", "10")
        settings = Settings()
        assert settings.celery_max_concurrent_tasks == 10


class TestRetryDelaysParsing:
    """Test retry delays parsing functionality."""
    
    def test_retry_delays_list_parsing(self):
        """Test retry_delays_list property correctly parses comma-separated string."""
        settings = Settings()
        settings.retry_delays = "1,2,4"
        assert settings.retry_delays_list == [1, 2, 4]
    
    def test_retry_delays_list_with_spaces(self):
        """Test retry_delays_list handles spaces in the string."""
        settings = Settings()
        settings.retry_delays = "1, 2, 4, 8"
        assert settings.retry_delays_list == [1, 2, 4, 8]
    
    def test_retry_delays_list_single_value(self):
        """Test retry_delays_list handles single value."""
        settings = Settings()
        settings.retry_delays = "5"
        assert settings.retry_delays_list == [5]
    
    def test_retry_delays_list_custom_values(self):
        """Test retry_delays_list with custom exponential backoff values."""
        settings = Settings()
        settings.retry_delays = "2,4,8,16,32"
        assert settings.retry_delays_list == [2, 4, 8, 16, 32]


class TestSettingsValidation:
    """Test configuration validation."""
    
    def test_summary_threshold_positive(self):
        """Test SUMMARY_THRESHOLD must be positive."""
        settings = Settings()
        assert settings.summary_threshold > 0
    
    def test_closing_timeout_positive(self):
        """Test CLOSING_TIMEOUT must be positive."""
        settings = Settings()
        assert settings.closing_timeout > 0
    
    def test_max_retries_non_negative(self):
        """Test MAX_RETRIES must be non-negative."""
        settings = Settings()
        assert settings.max_retries >= 0
    
    def test_celery_max_concurrent_tasks_positive(self):
        """Test Celery max concurrent tasks must be positive."""
        settings = Settings()
        assert settings.celery_max_concurrent_tasks > 0
    
    def test_api_port_valid_range(self):
        """Test API port is in valid range."""
        settings = Settings()
        assert 1 <= settings.api_port <= 65535


class TestSettingsCaseInsensitive:
    """Test case-insensitive environment variable loading."""
    
    def test_lowercase_env_var(self, monkeypatch):
        """Test lowercase environment variable is recognized."""
        monkeypatch.setenv("summary_threshold", "12000")
        settings = Settings()
        assert settings.summary_threshold == 12000
    
    def test_uppercase_env_var(self, monkeypatch):
        """Test uppercase environment variable is recognized."""
        monkeypatch.setenv("SUMMARY_THRESHOLD", "15000")
        settings = Settings()
        assert settings.summary_threshold == 15000
    
    def test_mixed_case_env_var(self, monkeypatch):
        """Test mixed case environment variable is recognized."""
        monkeypatch.setenv("Summary_Threshold", "18000")
        settings = Settings()
        assert settings.summary_threshold == 18000


# Feature: dual-agent-chat, Property 30: Threshold可配置
class TestProperty30ThresholdConfigurable:
    """Property 30: Threshold可配置
    
    验证需求 6.3: Summary触发阈值应可通过配置文件动态调整，默认值为8000 tokens
    """
    
    def test_threshold_default_value(self):
        """对于任何系统配置，Summary触发阈值默认值应为8000 tokens。"""
        settings = Settings()
        assert settings.summary_threshold == 8000
    
    def test_threshold_configurable_via_env(self, monkeypatch):
        """对于任何系统配置，Summary触发阈值应可通过环境变量动态调整。"""
        # Test with different threshold values
        test_values = [5000, 8000, 10000, 15000, 20000]
        
        for threshold in test_values:
            monkeypatch.setenv("SUMMARY_THRESHOLD", str(threshold))
            settings = Settings()
            assert settings.summary_threshold == threshold
    
    def test_threshold_type_is_integer(self):
        """对于任何系统配置，Summary触发阈值应为整数类型。"""
        settings = Settings()
        assert isinstance(settings.summary_threshold, int)
    
    def test_threshold_positive_value(self):
        """对于任何系统配置，Summary触发阈值应为正整数。"""
        settings = Settings()
        assert settings.summary_threshold > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
