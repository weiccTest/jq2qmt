-- 分钟数据收集请求配置表
-- 用于配置需要从聚宽收集分钟K线数据的股票列表

CREATE TABLE IF NOT EXISTS `minute_data_request` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `symbol` varchar(20) NOT NULL COMMENT '股票代码，如 000001.XSHE',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用: 1-启用, 0-禁用',
  `collect_days` int NOT NULL DEFAULT '1' COMMENT '收集天数，1=只收集当天',
  `last_collect_time` datetime DEFAULT NULL COMMENT '最后收集时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_symbol` (`symbol`),
  KEY `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分钟数据收集请求配置';

-- 插入示例数据
-- INSERT INTO minute_data_request (symbol) VALUES
-- ('000001.XSHE'),
-- ('600000.XSHG');
