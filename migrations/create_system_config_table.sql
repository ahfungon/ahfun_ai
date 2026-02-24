-- Create system_configs table for storing runtime configuration
CREATE TABLE IF NOT EXISTS system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    config_type VARCHAR(20) NOT NULL DEFAULT 'text',
    category VARCHAR(50) NOT NULL DEFAULT 'general',
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    default_value TEXT,
    validation TEXT,
    options TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on category for faster filtering
CREATE INDEX IF NOT EXISTS idx_system_configs_category ON system_configs(category);

-- Create index on display_order for faster sorting
CREATE INDEX IF NOT EXISTS idx_system_configs_display_order ON system_configs(display_order);

COMMENT ON TABLE system_configs IS 'System configuration for runtime settings';
COMMENT ON COLUMN system_configs.key IS 'Unique configuration key';
COMMENT ON COLUMN system_configs.value IS 'Configuration value (stored as string)';
COMMENT ON COLUMN system_configs.config_type IS 'Configuration type: text, number, textarea, select, password, boolean';
COMMENT ON COLUMN system_configs.category IS 'Configuration category for grouping';
COMMENT ON COLUMN system_configs.display_name IS 'Display name for UI';
COMMENT ON COLUMN system_configs.description IS 'Description for UI tooltip';
COMMENT ON COLUMN system_configs.default_value IS 'Default value for reset functionality';
COMMENT ON COLUMN system_configs.validation IS 'Validation rules (JSON string)';
COMMENT ON COLUMN system_configs.options IS 'Options for select type (JSON array)';
COMMENT ON COLUMN system_configs.display_order IS 'Display order for UI sorting';
