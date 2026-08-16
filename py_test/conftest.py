"""pytest 全局夹具: 测试日志写入临时目录,不污染 logs/"""

import os
import tempfile

os.environ["SELLING_LOG_DIR"] = tempfile.mkdtemp(prefix="selling_test_logs_")
