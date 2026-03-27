from datetime import date, datetime
from passes.models import  Logging
from typing import Dict, Union
import pytz
import re

# def roll_to_year(rno):
#     today = datetime.today()
#     year = today.year - int(f"20{rno[0:2]}")
#     if today.month >= 9:
#         year += 1
#     return year + (1 if rno[4:6] == "5A" else 0)
def log(roll_no: str,semester:int) -> Union[str,int, None]:
    """Logs the given roll no and gives the last time the pass was scanned for the given user.

    Args:
        roll_no (str): roll no to log the pass scanning

    Returns:
        int | None: unix time stamp of last time scanned
    """
    # print(datetime.fromtimestamp(datetime.today().timestamp()))
    last_logged = Logging.objects.filter(roll_no=roll_no).order_by("-time").first()
    try:
        today = datetime.now()
        Logging.objects.create(time=today.strftime("%Y-%m-%d %H:%M:%S"), roll_no=roll_no,semester=semester)
        if not last_logged:
            return None
        else:
            return last_logged.time
    except:
        return -1
