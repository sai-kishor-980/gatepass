import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
// import 'package:flutter/services.dart';

import 'secrets.dart';

import './db_handling.dart';
// import 'ffi.dart';

// var hosturl = "http://localhost:3000";

int rollToYear(String rollno) {
  var today = DateTime.now();
  int year = 0;
  year = (today.year - int.parse("20${rollno.substring(0, 2)}"));
  if (today.month > DateTime.september) {
    year += 1;
  }
  return year;
}

dynamic getDecryptedData(String endata) {
  Map res;
  try {
    res = jsonDecode(endata);
    //   if (res.keys.toList() != ["rno", "valid_till"]) {
    //     return null;
  } catch (e) {
    return null;
  }
  return res;
}

Future<Map<String, dynamic>> getValidity(rollno) async {
  try {
    var res = await http.get(Uri.parse("$hostUrl/isvalid?rollno=$rollno"),
        headers: Map.from({"authorization": "bearer $auth_token"}));
    return jsonDecode(res.body);
  } catch (e) {
    debugPrint(e.toString());
    debugPrint("e.toString()");
    return Map.from(
        {"success": false, "msg": "Please connect to internet. $e"});
  }
}

Future<bool> isValidPassOld(rollno) async {
  var passFuture = ValidPass.by(rollno: rollno);
  // var res = await _isValidPass(passFuture);
  var pass = (await passFuture)[0];

  int validTill = (pass['valid_till'] as int);
  var now = DateTime.now();
  if (now.millisecondsSinceEpoch > validTill * 1000) {
    return false;
  }

  int year = rollToYear(pass['rollno'] as String);
  if (pass['pass_type'] == 'alumni' || pass['pass_type'] == 'single_use') {
    // ignore: avoid_print
    print("Is True");
    return true;
  }
  var timing = await getTimings()[year - 1];

  var stArr = (timing['opening_time'].split(":") as List<String>)
      .map((e) => int.parse(e))
      .toList();
  var enArr = (timing['closing_time'].split(":") as List<String>)
      .map((e) => int.parse(e))
      .toList();

  int startStamp = DateTime(now.year, now.month, now.day, stArr[0], stArr[1], 0)
      .millisecondsSinceEpoch;
  int endStamp = DateTime(now.year, now.month, now.day, enArr[0], enArr[1], 0)
      .millisecondsSinceEpoch;
  int nowStamp = now.millisecondsSinceEpoch;
  if (!(nowStamp > startStamp && nowStamp < endStamp)) {
    return false;
  }

  return true;
}

Future<Map<String, dynamic>> remLatecomers(String rollno) async {
  try { 
    var res = await http.post(Uri.parse("$hostUrl/latecomers/"),
        headers: Map.from({"authorization": "bearer $auth_token"}),
        body: jsonEncode(<String, String>{
          "roll_no": rollno,
          "date": (DateTime.now().microsecondsSinceEpoch~/10e6).toString()
        }));
    // var x = (res.body);
    return jsonDecode(res.body);
  } catch (e) {
    debugPrint(e.toString());
    return Map.from(
        {"success": false, "msg": "Please connect to internet.\n$e"});
  }
}

Future<bool> refresh({bool startup = false}) async {
  return true;
  // if (startup) {
  //   if (await isDbPresent()) {
  //     return true;
  //   }
  // }
  // try {
  //   await refreshTimings();
  //   await ValidPass.loadAll();
  //   print(await getValidity("22BD1A0505"));
  //   return true;
  // } catch (e) {
  //   return false;
  // }    
}

// Future<bool> refreshStartup() async {
//   if (await isDbPresent()) {
//     return refresh();
//   } else {
//     return
//   }
// }

void main() async {
  // print(await getValidity("22BD1A0505"));
  // String now = (DateTime.now().millisecondsSinceEpoch.toString());
  // var res = await http.post(
  //   Uri.parse("$hostUrl/latecomers"),
  //   headers: Map<String, String>.from(
  //     {
  //       "authorization": "bearer $auth_token",
  //     },
  //   ),
  //   body: jsonEncode(
  //     [
  //       {
  //         "roll_no": "22BD1A0505",
  //         "date": DateTime.now().millisecondsSinceEpoch.toString(),
  //       }
  //     ],
  //   ),
  // );
}
