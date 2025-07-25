# logutils/logutils.py
import logging
import os
from datetime import datetime

# 创建 logs 目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 日志格式
fmt_str = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
datefmt_str = '%Y-%m-%d %H:%M:%S'

# 配置根日志器
logging.basicConfig(
    level=logging.INFO,
    format=fmt_str,
    datefmt=datefmt_str,
    handlers=[
        logging.FileHandler(f"logs/alpha_selector_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(name)
