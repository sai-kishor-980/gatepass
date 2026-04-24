import json
from urllib import response

from django.http import HttpResponse, HttpRequest
from ninja import NinjaAPI
from datetime import datetime
from typing import Union
from latecomers.models import *
from server.utlis import Auth
# from passes.utlis import get_local_date, get_roll_no, get_normalized_timestamp
from passes.models import Student,Semester
import re


api = NinjaAPI(urls_namespace="latecomers",version="3.0.0")

    

@api.post("", auth=Auth(), response=Result)
def rem_latecomers(request: HttpRequest):
    body = json.loads(request.body)
    roll= body["roll_no"]
    #"[0-9]{2}BD[158]A[0-9]{2}[A-HJ-NP-RT-Z0-9]{2}",
    # scannedAt = body["date"]
    # print(scannedAt)
    # date = str(datetime.fromtimestamp(float(scannedAt)))
    # date = date.split(" ")[0]
    ####### IGNORED THE DATE FROM THE FRONT END AS IT IS HAVING AN ERROR AND THE DATA BASE ALWAYS TAKES THE SAME DATE!
    # now , here mapping all the things admn -> roll and all other things ! 
    result = Result(success=True, msg="")
    today = datetime.today()
    today = str(datetime.today())
    today = today.split(" ")[0] # today's date is returned for checking in the server ! 
    # now comes the student data getting :
    # print(body)
    if type(body) != list:
        try:
            if len(roll)!=10:
                admn_re = r"[0-9]{2}BD[158]A[0-9]{2}[A-HJ-NP-RT-Z0-9]{2}"
                roll_re = r"\b\d{5}\b"
                admn = re.findall(roll_re,roll)[0]
                # print(admn)
                std = Student.objects.filter(rollno=admn).first()
            else:
                std = Student.objects.filter(kmitrollno=roll).first()
                # print(std)
            if not std:
                result.msg="No Student Found with Specific Roll Number or Admission Number."
                result.success=False
                return result
            if not std.active:
                result.msg="The Student has been passed Out. Please verify permission and allow him!"
                return result 
            limit = Semester.objects.filter(semester=std.semester).first().lateCount
            todayCount = Latecomers.objects.filter(roll_no=std.kmitrollno, date__startswith=today).count()
            # print(todayCount)
            lateCount = Latecomers.objects.filter(roll_no=std.kmitrollno).count()
            # print(lateCount)
            if todayCount == 0:
                if lateCount >=limit:
                    result.msg = f"Student reached the limit of {limit} Late Entries.\nPrevious Late Entries are {lateCount}"
                    Latecomers.objects.create(roll_no=std.kmitrollno, date=today,semester=std.semester)
                    result.success = False
                    return result
                Latecomers.objects.create(roll_no=std.kmitrollno, date=today,semester=std.semester)
                if lateCount<limit-1 :
                    result.msg = f"Scanned successfully.\nStudent has been late for {lateCount} times earlier."
                elif lateCount==limit-1:
                    result.msg=f"Scanned successfully.\nWarn the Student this is the Last Chance for the Student. Reached {limit}."
            else:
                result.msg = f"Roll no has been scanned Earlier Today.\nStudent has been late for {lateCount} times earlier."
        except Exception as e:
            # print(e)
            result.success = False
            result.msg = "Not able to scan. Please try again."
    else:
        for i in body:

            Latecomers.objects.create(roll_no=i["roll_no"], date=i["date"])

    return result


@api.get("")
def latecomers(request, ret_type="json", frm=None, to=None, roll_no=None,semester=None):
    latecomers_qs = Latecomers.objects.all()

    if frm and to:
        latecomers_qs = latecomers_qs.filter(date__gte=frm,date__lte=to)

    if roll_no:
        latecomers_qs = latecomers_qs.filter(roll_no=roll_no)

    if semester:
        latecomers_qs = latecomers_qs.filter(semester=semester)
    if latecomers_qs.count() == 0:
        return HttpResponse("No latecomers found.")
    
    if ret_type == "json":
        res = [i.json() for i in latecomers_qs]
        return HttpResponse(json.dumps(res), content_type="application/json")
    if ret_type == "csv":
        res = ""
        for i in latecomers_qs:
            if res == "":
                res += str(list(i.json().keys())).strip("[]").replace("'", "") + "\n"
#            print(i.roll_no, get_roll_no(i.roll_no), str(i.json().values()), get_local_date(i.date))
            res += (
                str(list(i.json().values()))
                .strip("[]")
                .replace("'", "")
                + "\n"
            )
        return HttpResponse(
            res,
            content_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=latecomers_{int(datetime.now().timestamp())}.csv"
            },
        )

    