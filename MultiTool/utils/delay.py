import random
import asyncio


MIN_DELAY = 60      # أقل تأخير (ثانية) = دقيقة
MAX_DELAY = 300     # أكثر تأخير (ثانية) = 5 دقايق


def get_random_delay(min_sec=None, max_sec=None):
    """
    يرجع تأخير عشوائي بالثواني
    - توزيع triangular (الأغلب قريب من الوسط)
    - يبدو طبيعي أكثر من uniform
    """
    if min_sec is None:
        min_sec = MIN_DELAY
    if max_sec is None:
        max_sec = MAX_DELAY

    peak = (min_sec + max_sec) / 2

    return random.triangular(min_sec, max_sec, peak)


def format_time(seconds):
    """يحوّل الثواني لنص مقروء"""
    if seconds < 60:
        return f"{seconds:.1f} ثانية"
    elif seconds < 3600:
        return f"{seconds/60:.1f} دقيقة"
    else:
        return f"{seconds/3600:.2f} ساعة"


async def wait_random(min_sec=None, max_sec=None, callback=None):
    """
    ينتظر تأخير عشوائي
    - callback: دالة اختيارية تُستدعى بالثواني
    """
    seconds = get_random_delay(min_sec, max_sec)
    text = format_time(seconds)

    if callback:
        callback(text)
    else:
        print(f"⏳ ينتظر {text}...")

    await asyncio.sleep(seconds)