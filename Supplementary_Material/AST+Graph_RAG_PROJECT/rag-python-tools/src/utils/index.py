from datetime import datetime, timedelta


# 判断时间是否在几天之前
def is_before_days(date, days):
    return date < datetime.now() - timedelta(days=days)
