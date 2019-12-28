import logging
import colorlog


def init_config():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    format_ = '%(asctime)s_out  %(module)s_out  %(funcName)s_out  [%(levelname)s_out]  %(message)s_out'
    date_format = '%Y-%m-%d %H:%M:%S'

    cformat = '%(log_color)s_out' + format_
    f = colorlog.ColoredFormatter(cformat, date_format,
                                  log_colors={'DEBUG': 'cyan', 'INFO': 'green',
                                              'WARNING': 'bold_yellow', 'ERROR': 'red',
                                              'CRITICAL': 'bold_red'})

    ch = logging.StreamHandler()
    ch.setFormatter(f)
    root.addHandler(ch)

    file_f = logging.Formatter(format_)
    fh = logging.FileHandler("ULog.log")
    fh.setFormatter(file_f)
    root.addHandler(fh)
