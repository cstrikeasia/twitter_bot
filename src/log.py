import os
import logging
import logging.handlers


class LogFormatter(logging.Formatter):
    
    LEVEL_COLORS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]
    
    def setFORMATS(self, is_exc_info_colored):
        if is_exc_info_colored:
            self.FORMATS = {
                level: logging.Formatter(
                    f'\x1b[30;1m%(asctime)s\x1b[0m {color}%(levelname)-8s\x1b[0m \x1b[35m%(name)s\x1b[0m -> %(message)s',
                    '%Y-%m-%d %H:%M:%S'
                )
                for level, color in self.LEVEL_COLORS
            }
        else:
            self.FORMATS = {
                item[0]: logging.Formatter(
                    '%(asctime)s %(levelname)-8s %(name)s -> %(message)s',
                    '%Y-%m-%d %H:%M:%S'
                )
                for item in self.LEVEL_COLORS
            }
            

    def format(self, record, is_exc_info_colored = False):
        self.setFORMATS(is_exc_info_colored)
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # 覆蓋回溯始終以紅色打印（如果is_exc_info_colored為True）
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            if is_exc_info_colored: record.exc_text = f'\x1b[31m{text}\x1b[0m'
            else: record.exc_text = text

        output = formatter.format(record)

        # 刪除快取層
        record.exc_text = None
        return output


class ConsoleFormatter(LogFormatter):
    
    def format(self, record):
        return super().format(record, is_exc_info_colored = True)


def setup_logger(module_name:str) -> logging.Logger:
    
    # 建立記錄器
    library, _, _ = module_name.partition('.py')
    logger = logging.getLogger(library)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # 建立控制台處理程序
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        
        # 指定Log檔案路徑與`main.py`檔案路徑相同
        grandparent_dir = os.path.abspath(__file__ + "/../../")
        log_name='console.log'
        log_path = os.path.join(grandparent_dir, log_name)
        
        # 建立本機Log處理程序
        log_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            encoding='utf-8',
            maxBytes=32 * 1024 * 1024,  # 32 MiB
            backupCount=2,  # 循環瀏覽5個文件
        )
        log_handler.setFormatter(LogFormatter())
        
        # 將處理程序新增至記錄器
        logger.addHandler(log_handler)
        logger.addHandler(console_handler)

    return logger