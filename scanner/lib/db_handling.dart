import 'dart:async';

import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';
// import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'package:http/http.dart' as http;
import 'secrets.dart';

const String dbname = "scanner_data.db";

Future<bool> isDbPresent() async {
  // databaseFactory = databaseFactoryFfi;
  var dbPath = join(await getDatabasesPath(), dbname);
  var res = await File(dbPath).exists();
  return res;
}

void createTables(Database db) {
  // db.execute('CREATE TABLE latecomers (rollno varchar(11), date integer)');
  db.execute('''CREATE TABLE valid_pass (
    roll_no varchar(11),
    pass_type varchar(10),
    issue_date BIGINT,
    valid_till BIGINT
  )''');
  db.execute('''CREATE TABLE Lunch_Timings (
        year varchar(2) UNIQUE,
        opening_time varchar(7),
        closing_time varchar(7)
    );''');
  db.execute(
      "INSERT INTO Lunch_Timings (year,opening_time,closing_time) VALUES ('1', '12:15', '13:00')");
  db.execute(
      "INSERT INTO Lunch_Timings (year,opening_time,closing_time) VALUES ('2', '12:15', '13:00')");
  db.execute(
      "INSERT INTO Lunch_Timings (year,opening_time,closing_time) VALUES ('3', '12:15', '13:00')");
}

Future<Database> openDB() async {
  // await databaseFactory.deleteDatabase(join(await getDatabasesPath(), dbname));
  final database = openDatabase(
    join(await getDatabasesPath(), dbname),
    onCreate: (db, version) {
      createTables(db);
    },
    version: 1,
  );
  return database;
}

class ValidPass {
  String rollno;
  String passType;
  BigInt issueDate;
  BigInt validTill;

  ValidPass(
    this.rollno,
    this.passType,
    this.issueDate,
    this.validTill,
  );

  static const tablename = "valid_pass";

  Map<String, dynamic> toMap() {
    return {
      "roll_no": rollno,
      "pass_type": passType,
      "issue_date": issueDate,
      "valid_till": validTill,
    };
  }

  static Future<List<Map<String, Object?>>> by({required String rollno}) async {
    final db = await openDB();
    // var x = await db.query(tablename, columns: null, where: null);
    var res = await db.query(
      tablename,
      columns: null,
      where: "roll_no = ?",
      whereArgs: [rollno],
    );

    return res;
  }

  Future<bool> insertToDB() async {
    try {
      var db = await openDB();
      await db.insert(tablename, toMap());
      // var res = await db.query("Lunch_Timings");
      // print(res);
      return true;
    } catch (e) {
      return false;
    }
  }

  static Future<bool> loadAll() async {
    try {
      var db = await openDB();
      var res = (await http.get(Uri.parse("$hostUrl/get_valid_passes")));
      // var res =
      // var resJson = jsonDecode("[{roll_no: 22BD1A0511, issue_date: 1699107871, valid_till: 3908183071, pass_type: alumni}, {roll_no: 22BD1A0505, issue_date: 1699541920, valid_till: 3908617120, pass_type: alumni}]");
      var resJson = jsonDecode(res.body);
      db.rawDelete("DELETE FROM $tablename");
      for (var i in resJson) {
        await db.insert(
            tablename,
            Map.from({
              "roll_no": i["roll_no"],
              "issue_date": i["issue_date"],
              "valid_till": i["valid_till"],
              "pass_type": i["pass_type"]
            }));
      }
      // print()
      return true;
    } catch (e) {
      return false;
    }
  }

  static Future<List<dynamic>> getAll() async {
    var db = await openDB();
    var res = await db.rawQuery('SELECT * from $tablename');
    // print(res);
    // print("get all ran");
    return res;
  }
}

dynamic getTimings() async {
  final db = await openDB();
  var res = await db.query("Lunch_Timings");
  return res;
}

Future<void> refreshTimings() async {
  var res = await http.get(Uri.parse('$hostUrl/get_timings'));
  var timings = jsonDecode(res.body);
  var db = await openDB();
  for (var i in timings) {
    // i["rollno"] = i["roll_no"];
    // i.remove("roll_no");
    db.update("Lunch_Timings", i, where: 'year = ?', whereArgs: [i['year']]);
  }
}
