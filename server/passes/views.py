from genericpath import isdir, isfile
import json
import base64

from django.http import HttpResponse, HttpRequest
from django.conf import settings    
from ninja import NinjaAPI,File
from passes.models import (
    ReqPass,
    IssuedPass,
    ReqLunchTiming,
    ResStudent,
    Result,
    Student,
    Semester,
    PromoteSchema,
    Logging 
)
import re
import os
from datetime import datetime, timedelta,time
from dateutil.relativedelta import relativedelta
import pytz
from typing import List
import requests
from ninja import File
from ninja.files import UploadedFile
from latecomers.models import Latecomers
from passes import utlis
from server.utlis import Auth

from django.db import transaction

from ninja import Schema
from django.http import HttpRequest

class ActivateSchema(Schema):
    startDate: str
    openingTimeLunch: str
    closingTimeLunch: str
    lateCount: int


api = NinjaAPI(urls_namespace="passes",version="2.0.0")

@api.get("/check_first_semester")
def check_first_semester(request: HttpRequest):

    sem = Semester.objects.filter(semester=1).first()

    if not sem:
        return {"active": False}

    return {"active": sem.active}


@api.post("/gen_pass", auth=Auth())
def gen_pass(request: HttpRequest, reqPass: ReqPass):
    today = datetime.now()
    std = Student.objects.filter(kmitrollno=reqPass.roll_no).first()
    if not std:
        return HttpResponse(
            f"No Student Found with that Roll Number"
        )
    valid_passes = IssuedPass.objects.filter(
        roll_no=reqPass.roll_no, valid_till__gte=today.strftime("%Y-%m-%d %H:%M:%S")
    )

    passCount = valid_passes.filter(pass_type=reqPass.pass_type).count()

    if passCount > 0:
        return HttpResponse(
            f"Warning: {reqPass.roll_no} already owns a {reqPass.pass_type} pass"
        )

    valid_till = today
    if reqPass.pass_type == "one_time":
        valid_till = datetime.combine(today.date(), time(16, 30))
    if reqPass.pass_type == "daily":
        valid_till = today + relativedelta(months=6)
    if reqPass.pass_type == "alumni":
        valid_till = today + relativedelta(years=70)
    if reqPass.pass_type == "namaaz":
        valid_till = datetime.combine(today.date(), time(16, 30))

    IssuedPass.objects.create(
        roll_no=reqPass.roll_no,
        pass_type=reqPass.pass_type,
        semester=std.semester,
        issued_date=today.strftime("%Y-%m-%d %H:%M:%S"),
        valid_till=valid_till.strftime("%Y-%m-%d %H:%M:%S"),
    )   
    return "success"

@api.get("/get_active_semesters")
def get_active_semesters(request:HttpRequest):
    sems = Semester.objects.filter(active=True)
    active = []
    for i in sems:
        if(i.active):
            active.append(i.semester)
    return active



@api.get("/get_semester_details")
def get_semester_details(request:HttpRequest,semester:int):
    sem = Semester.objects.filter(semester=semester).first()
    sem = sem.json()
    return HttpResponse(json.dumps(sem),content_type="application/json")

@api.post("/edit_semester",auth=Auth())
def edit_semester(request: HttpRequest,semester:int):
    data = json.loads(request.body)
    sem = Semester.objects.filter(semester=semester).first()
    if not sem:
        return "No sem found!"
        #updating details
    sem.startDate   = data["startDate"]
    sem.openingTimeLunch = data["openingTimeLunch"]
    sem.closingTimeLunch = data["closingTimeLunch"]
    sem.lateCount = data["lateCount"]
    sem.save()
    return "success"

from typing import Optional
@api.post("/promote_semester")
def promote_semester(request, semester: int, data: Optional[PromoteSchema] = None):
    year_map = {1:1,2:1,3:2,4:2,5:3,6:3,7:4,8:4}

    try:
        with transaction.atomic():
            #Get current semester
            sem = Semester.objects.get(semester=semester)
            # print(sem.json())
            sem.active = False
            sem.save()
            # print(sem.json())

            # If final semester → deactivate students
            if semester >= 8:
                Student.objects.filter(semester=semester).update(active=False)
                Latecomers.objects.filter(semester=semester).delete()
                return "Success. Students of 8 Semester are Inactive."

            updated_sem = semester + 1

            #  Get next semester safely
            usem = Semester.objects.filter(semester=updated_sem).first()
            if not usem:
                return "Next semester not found"

            # FIX TIME VALIDATION
            start = datetime.strptime(data.openingTimeLunch, "%H:%M")
            end = datetime.strptime(data.closingTimeLunch, "%H:%M")

            if start >= end:
                return "Opening time must be less than closing time"

            # Update next semester
            # print(usem.json())
            usem.active = True
            usem.startDate = data.startDate
            usem.openingTimeLunch = data.openingTimeLunch
            usem.closingTimeLunch = data.closingTimeLunch
            usem.lateCount = data.lateCount
            usem.save()
            # print(usem.json())
            # Promote students
            updated_year = year_map[updated_sem]

            Student.objects.filter(semester=semester).update(
                semester=updated_sem,
                year=updated_year
            )

            # 7. Clean old latecomers
            Latecomers.objects.filter(
                semester=semester,
                date__lt=data.startDate
            ).delete()

            IssuedPass.objects.filter(
                semester=semester
            ).update(active=False)

            Logging.objects.filter(
                semester = semester
            ).delete()
        return f"Success. Students of {semester} are promoted to {updated_sem}"

    except Exception as e:
        print("ERROR:", e)
        return f"Error: {str(e)}"

@api.get("//isvalid", auth=Auth(), response={200: Result, 404: Result})
def is_valid(request: HttpRequest, rollno: str):
    result = Result(success=True, msg="")
    today = datetime.now()
    try:
        # print(1)
        if len(rollno)!=10:
            admn_re = r"[0-9]{2}BD[158]A[0-9]{2}[A-HJ-NP-RT-Z0-9]{2}"
            roll_re = r"\b\d{5}\b"
            admn = re.findall(roll_re,rollno)[0]
            # print(admn)
            std = Student.objects.filter(rollno=admn).first()
        else:
            std = Student.objects.filter(kmitrollno=rollno).first()
            # print(std)
        if not std:
            result.msg="No Student Found with Specific Roll Number or Admission Number."
            result.success=False
            return result
        if not std.active:
            result.msg="The Student has been passed Out. Please verify permission and allow him!"
            return result 
    except Exception as e:
        result.msg = f"Unexpected Error ! {e}"
        result.success=False
        return result
    resPass = IssuedPass.objects.filter(
        roll_no=std.kmitrollno, valid_till__gt= today.strftime("%Y-%m-%d %H:%M:%S"),active=True
    ).order_by("-valid_till").first()
    
    if not resPass:
        result.success = False
        result.msg = "No passes found."
        return 404 ,result
    if resPass.valid_till < today.strftime("%Y-%m-%d %H:%M:%S"):
        result.success = False
        result.msg = "Not valid passes found."
        return result
    
    if resPass.pass_type == "alumni" or resPass.pass_type == "one_time":
        result.msg = f"Roll No. {std.kmitrollno} has valid pass."
        return result
    sem = Semester.objects.filter(semester=std.semester).first()
    
    open_time = datetime.strptime(sem.openingTimeLunch, "%H:%M").time()
    close_time = datetime.strptime(sem.closingTimeLunch, "%H:%M").time()

    timings = {
    "open": datetime.combine(today.date(), open_time),
    "close": datetime.combine(today.date(), close_time),
    }   

    if not (timings["open"] < datetime.now() < timings["close"]):
        result.success = False
        result.msg = "Not the appropriate time"
        return result

    if resPass.pass_type == "namaaz":
        if today.isoweekday() != 5:
            result.success = False
            result.msg = "Invalid Pass"
            return result

    last_logged_time = utlis.log(roll_no=rollno,semester=sem.semester)
    result.msg = f"Last scanned on {last_logged_time}"
    return result

@api.get("/truncate")
def rmv_passes(
    request: HttpRequest,
    no: str,
):
    allpass = IssuedPass.objects.filter(roll_no = no)
    pass_ = IssuedPass.objects.filter(roll_no = no, pass_type = "one_time")
    if pass_.count() > 0:   
        lst = pass_[pass_.count() - 1]
        if lst.pass_type == 'one_time':
            lst.delete()
        
    res = [i.json() for i in allpass]
    return HttpResponse(json.dumps(res), content_type="application/json")
    

@api.get("/get_issued_passes", description="Lets you download all passes")
def get_issues_passes(
    request: HttpRequest,
    ret_type="json",
    frm=None,
    to=None,
    rollno=None,
    semester = None
):
    # pass_lst = None
    pass_qs = IssuedPass.objects.all()
    if frm and to:
        frmt = datetime.strptime(frm, "%Y-%m-%d").date()
        tot = datetime.strptime(to, "%Y-%m-%d").date()
        open_time = datetime.strptime("00:00","%H:%M").time()
        close_time = datetime.strptime("23:59", "%H:%M").time()
        frmtt = datetime.combine(frmt, open_time)
        tott = datetime.combine(tot, close_time)
        pass_qs = pass_qs.filter(
            issued_date__gt=frmtt.strftime("%Y-%m-%d %H:%M:%S"),
            issued_date__lt=tott.strftime("%Y-%m-%d %H:%M:%S")
        )

    if rollno:
        pass_qs = pass_qs.filter(roll_no=rollno)
    if semester:
        pass_qs = pass_qs.filter(semester=semester)
    if len(pass_qs) == 0:
        return HttpResponse("No passes found.")

    if ret_type == "json":
        res = [i.json() for i in pass_qs]
        return HttpResponse(json.dumps(res), content_type="application/json")
    if ret_type == "csv":
        res = ""
        for i in pass_qs:
            if res == "":
                res += str(list(i.json().keys())).strip("[]").replace("'", "") + "\n"
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
                "Content-Disposition": f"attachment; filename=passes_{int(datetime.now().timestamp())}.csv"
            },
        )


@api.get("/get_valid_passes")
def get_valid_passes(request: HttpRequest):
    today = datetime.now()
    pass_qs = IssuedPass.objects.filter(valid_till__gt=today.strftime("%Y-%m-%d %H:%M:%S"))
    pass_json = [i.json() for i in pass_qs]
    print(pass_json)

    return HttpResponse(json.dumps(pass_json), content_type="application/json")


@api.get("/get_student_data", auth=Auth(), response={200: ResStudent, 404: str})
def get_student_data(request: HttpRequest, rollno: str):
    res = Student.objects.filter(kmitrollno=rollno).first()
    if res == None:
        return 404, "No rollno found"
    picture_bytes = None
    try:
        if os.path.isdir("./studentImages"):
            for ext in ["jpg", "jpeg", "png"]: 
                if os.path.isfile(f"./studentImages/{rollno}.{ext}"):
                    with open(f"./studentImages/{rollno}.{ext}", "rb") as img:
                        picture_bytes = img.read()
                    break
            if not picture_bytes:
                res.picture = None
                return 200, res
        else:
            image_res = requests.get(str(res.picture), timeout=3)
            picture_bytes = image_res.content
            if image_res.status_code == 403:
                res.picture = None
                return 200, res
        picture_b64 = base64.b64encode(picture_bytes)
        res.picture = picture_b64.decode()
        # print(res)
    except:  # noqa: E722
        res.picture = None
        # print(res)

    return 200, res

@api.get("/get_scan_history")
def get_scan_history(
    request: HttpRequest,
    ret_type="json",
    frm=None,
    to=None,
    rollno=None,
    semester = None
):
    # pass_lst = None
    pass_qs = Logging.objects.all()
    if frm and to:
        frmt = datetime.strptime(frm, "%Y-%m-%d").date()
        tot = datetime.strptime(to, "%Y-%m-%d").date()
        open_time = datetime.strptime("00:00","%H:%M").time()
        close_time = datetime.strptime("23:59", "%H:%M").time()
        frmtt = datetime.combine(frmt, open_time)
        tott = datetime.combine(tot, close_time)
        pass_qs = pass_qs.filter(
            time__gt=frmtt.strftime("%Y-%m-%d %H:%M:%S"),
            time__lt=tott.strftime("%Y-%m-%d %H:%M:%S")
        )

    if rollno:
        pass_qs = pass_qs.filter(roll_no=rollno)
    if semester:
        pass_qs = pass_qs.filter(semester=semester)
    if len(pass_qs) == 0:
        return HttpResponse("No passes found.")

    if ret_type == "json":
        res = [i.json() for i in pass_qs]
        return HttpResponse(json.dumps(res), content_type="application/json")
    if ret_type == "csv":
        res = ""
        for i in pass_qs:
            if res == "":
                res += str(list(i.json().keys())).strip("[]").replace("'", "") + "\n"
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
                "Content-Disposition": f"attachment; filename=scan_{int(datetime.now().timestamp())}.csv"
            },
        )

from ninja import Form




from passes.models import init_students


@api.get("")
def home(request: HttpRequest, initdb: bool = False):
    print(request.method)
    if initdb:
        init_students()
        return HttpResponse("Database updated.")
    return HttpResponse("Welcome to the Hosting Server of GARUDA (Late Pass)")



# BACKEND : replace your existing /upload_data API with this

from ninja import Form, File
from ninja.files import UploadedFile
from typing import List
from django.conf import settings
from django.db import transaction
import json
import os


@api.post("/upload_data")
def upload_students(
    request,

    # json string from frontend
    students: str = Form(...),

    # Upload / Update
    mode: str = Form(...),

    # only for Upload mode
    admission_type: str = Form(""),

    # only for Update mode
    semester: str = Form(""),

    # optional images
    images: List[UploadedFile] = File(None)
):

    # ========================================================
    # STEP 1 : READ STUDENT JSON
    # ========================================================
    try:
        students_data = json.loads(students)

    except Exception:
        return {
            "success": False,
            "message": "Invalid JSON Data"
        }

    # ========================================================
    # STEP 2 : CREATE ROLL -> DATA MAP
    # ========================================================
    student_map = {
        str(i["Roll No."]).strip(): i
        for i in students_data
    }

    # ========================================================
    # STEP 3 : CREATE IMAGE MAP
    # rollno -> uploaded image
    # ========================================================
    image_map = {}

    if images:
        for img in images:
            roll = img.name.split(".")[0].strip()
            image_map[roll] = img

    # ========================================================
    # STEP 4 : SAVE DIRECTORY
    # ========================================================
    save_dir = settings.MEDIA_ROOT
    os.makedirs(save_dir, exist_ok=True)

    # ========================================================
    # STEP 5 : RESULT LISTS
    # ========================================================
    created = []
    updated = []
    failed = []

    # ========================================================
    # STEP 6 : UPLOAD MODE MAPPING
    # ========================================================
    # only for new intake
    upload_map = {
        "1st Year Regular": {
            "year": "1",
            "semester": "1"
        },

        "2nd Year LE": {
            "year": "2",
            "semester": "3"
        }
    }

    # ========================================================
    # STEP 7 : MAIN LOOP
    # ========================================================
    for roll, data in student_map.items():

        try:
            with transaction.atomic():

                # ------------------------------------------------
                # CHECK EXISTING STUDENT
                # ------------------------------------------------
                student = Student.objects.filter(
                    kmitrollno=roll
                ).first()

                # =================================================
                # MODE = UPLOAD
                # =================================================
                if mode == "Upload":

                    # --------------------------------------------
                    # duplicate student not allowed
                    # --------------------------------------------
                    if student:
                        failed.append(
                            f"{roll} -> Already Exists"
                        )
                        continue

                    # --------------------------------------------
                    # image compulsory in upload mode
                    # --------------------------------------------
                    if roll not in image_map:
                        failed.append(
                            f"{roll} -> No Image Uploaded"
                        )
                        continue

                    # --------------------------------------------
                    # get mapping
                    # --------------------------------------------
                    if admission_type not in upload_map:
                        failed.append(
                            f"{roll} -> Invalid Admission Type"
                        )
                        continue

                    year = upload_map[
                        admission_type
                    ]["year"]

                    sem = upload_map[
                        admission_type
                    ]["semester"]

                    # --------------------------------------------
                    # save image
                    # --------------------------------------------
                    img = image_map[roll]

                    file_path = os.path.join(
                        save_dir,
                        img.name
                    )

                    with open(file_path, "wb+") as f:
                        for chunk in img.chunks():
                            f.write(chunk)

                    # --------------------------------------------
                    # create student
                    # --------------------------------------------
                    Student.objects.create(

                        # hallticket
                        kmitrollno=roll,

                        # admission no
                        rollno=str(
                            data.get("Adm. No.", "")
                        ).strip(),

                        name=str(
                            data.get(
                                "Name of the Student",
                                ""
                            )
                        ).strip(),

                        section=str(
                            data.get("Sec", "")
                        ).strip(),

                        dept=str(
                            data.get(
                                "Department",
                                ""
                            )
                        ).strip(),

                        year=year,
                        semester=sem,

                        picture=img.name,

                        active=True
                    )

                    created.append(roll)

                # =================================================
                # MODE = UPDATE
                # =================================================
                elif mode == "Update":

                    # --------------------------------------------
                    # student must exist
                    # --------------------------------------------
                    if not student:
                        failed.append(
                            f"{roll} -> Not Found"
                        )
                        continue

                    # --------------------------------------------
                    # only selected semester students
                    # --------------------------------------------
                    if str(student.semester) != str(semester):
                        failed.append(
                            f"{roll} -> Not in Semester {semester}"
                        )
                        continue

                    # --------------------------------------------
                    # update fields
                    # --------------------------------------------
                    student.rollno = str(
                        data.get("Adm. No.", "")
                    ).strip()

                    student.name = str(
                        data.get(
                            "Name of the Student",
                            ""
                        )
                    ).strip()

                    student.section = str(
                        data.get("Sec", "")
                    ).strip()

                    student.dept = str(
                        data.get(
                            "Department",
                            ""
                        )
                    ).strip()

                    # --------------------------------------------
                    # image optional in update mode
                    # if uploaded -> replace
                    # else keep old image
                    # --------------------------------------------
                    if roll in image_map:

                        img = image_map[roll]

                        file_path = os.path.join(
                            save_dir,
                            img.name
                        )

                        with open(file_path, "wb+") as f:
                            for chunk in img.chunks():
                                f.write(chunk)

                        student.picture = img.name

                    student.save()

                    updated.append(roll)

                # =================================================
                # INVALID MODE
                # =================================================
                else:
                    failed.append(
                        f"{roll} -> Invalid Mode"
                    )

        except Exception as e:

            failed.append(
                f"{roll} -> {str(e)}"
            )

    # ========================================================
    # STEP 8 : SUMMARY
    # ========================================================
    summary = {
        "total": len(student_map),
        "created": len(created),
        "updated": len(updated),
        "failed": len(failed)
    }

    # ========================================================
    # STEP 9 : FINAL RESPONSE
    # ========================================================
    return {
        "success": True,
        "created": created,
        "updated": updated,
        "failed": failed,
        "summary": summary
    }




# ==========================================
# ADD THIS IN passes/views.py
# ==========================================

from django.http import HttpRequest


# ------------------------------------------
# CHECK WHETHER 1ST SEMESTER ACTIVE OR NOT
# ------------------------------------------
@api.get("/check_first_semester")
def check_first_semester(request: HttpRequest):

    sem = Semester.objects.filter(semester=1).first()

    # If no record found
    if not sem:
        return {
            "active": False,
            "message": "Semester 1 not found"
        }

    return {
        "active": sem.active
    }


# ------------------------------------------
# ACTIVATE 1ST SEMESTER
# ------------------------------------------
@api.post("/activate_first_semester", auth=Auth())
def activate_first_semester(
    request: HttpRequest,
    data: ActivateSchema
):

    sem = Semester.objects.filter(semester=1).first()

    if not sem:
        return "Semester 1 not found."

    if sem.active:
        return "1st Semester already active."

    sem.active = True
    sem.startDate = data.startDate
    sem.openingTimeLunch = data.openingTimeLunch
    sem.closingTimeLunch = data.closingTimeLunch
    sem.lateCount = data.lateCount

    sem.save()

    return "1st Semester Activated Successfully."

