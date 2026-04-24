from django.db import models
from typing import Union
from bulk_update_or_create import BulkUpdateOrCreateQuerySet
import json
from datetime import datetime

class Semester(models.Model):
    semester = models.IntegerField(primary_key=True)
    startDate = models.CharField(max_length=25)
    lateCount = models.IntegerField()
    openingTimeLunch = models.CharField(max_length=10)
    closingTimeLunch = models.CharField(max_length=10)
    active = models.BooleanField()

    def json(self):
        return{
            "semester" : self.semester,
            "Start Date" : self.startDate,
            "Late Limit" : self.lateCount,
            "Lunch Opening Time" : self.openingTimeLunch,
            "Lunch Closing Time" : self.closingTimeLunch,
            "Status" : "Active"if self.active else "Inactive"
        }
    class Meta:
        db_table = "semester"

class IssuedPass(models.Model):
    PASS_TYPES = [("one_time", "one_time"), ("daily", "daily"), ("alumni", "alumni")]
    roll_no = models.CharField(max_length=11)
    semester = models.IntegerField(default=1)
    today = datetime.now()
    issued_date = models.CharField(max_length=25,default=today.strftime("%Y-%m-%d %H:%M:%S"))
    valid_till = models.CharField(max_length=25,default=today.strftime("%Y-%m-%d %H:%M:%S"))
    pass_type = models.CharField(max_length=10)
    active = models.BooleanField(default=True)

    def json(self):
        return {
            "roll_no": self.roll_no,
            "issue_date": self.issued_date,
            "valid_till": self.valid_till,
            "pass_type": self.pass_type,
            "semester":self.semester,
            "active" : "Active"if self.active else "Inactive" 
        }

    class Meta:
        db_table = "issued_pass"



# class Student(models.Model):


class Student(models.Model):
    rollno = models.CharField(max_length=11)    # admn no 
    kmitrollno = models.CharField(max_length=11,primary_key=True) # hall ticket number
    name = models.CharField(max_length=100)
    year = models.CharField(max_length=2, default="-1")
    semester = models.CharField(max_length=2,default="1")
    dept = models.CharField(max_length=5)
    section = models.CharField(max_length=5)
    picture = models.CharField(max_length=60, null=True)
    active = models.BooleanField(default=True)
    # def json(self):
    #     return

    class Meta:
        db_table = "student"


class Logging(models.Model):
    time = models.CharField(max_length=25)
    roll_no = models.CharField(max_length=11)
    semester = models.IntegerField(default=1)

    def json(self):
        return {
            "Roll No":self.roll_no,
            "Time":self.time,
            "Semester":self.semester
        }


from ninja import Schema  # noqa: E402


class ReqPass(Schema):
    roll_no: str
    pass_type: str


class ReqLunchTiming(Schema):
    opening_time: str
    closing_time: str

class PromoteSchema(Schema):
    startDate: str
    openingTimeLunch: str
    closingTimeLunch: str
    lateCount: int

class ResStudent(Schema):
    rollno: str
    kmitrollno: str
    name: str
    year: str
    semester:str
    active:bool
    dept: str
    section: str
    picture: Union[str, None]


class Result(Schema):
    success: bool
    msg: str


# initialize students table


def init_students():
    data = []
    with open("./students.json") as file:
        data = list(
            map(
                lambda i: Student(
                    **{
                        "rollno": i["rollno"],
                        "kmitrollno":i["kmitrollno"],
                        "name": i["name"],
                        "year": i["year"],
                        "dept": i["dept"],
                        "semester":i["semester"],
                        "section": i["section"],
                        "active":i["Active"]
                        # "picture": i["picture"],
                    }
                ),
                json.load(file),
            )
        )
    print(())
    Student.objects.bulk_create(data)
    # Student.objects.bulk_create()
