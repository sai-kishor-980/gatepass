from django.db import models
from bulk_update_or_create import BulkUpdateOrCreateQuerySet

class Latecomers(models.Model):
    roll_no = models.CharField(max_length=11)
    date = models.CharField(max_length=20)
    semester = models.IntegerField(default=1)
    def json(self):
        return {"roll_no": self.roll_no, "semester":self.semester,"date": self.date}

    class Meta:
        unique_together = ('roll_no', 'date')
        db_table = "latecomers"
        


from ninja import Schema
from typing import List


class Result(Schema):
    success: bool
    msg: str


class ReqLatecomers(Schema):
    roll_no: str
    date: str


class ReqLatecomersList(Schema):
    data: List[ReqLatecomers]

class ReqLateLimit(Schema):
    count : int