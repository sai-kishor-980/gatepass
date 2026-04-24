// ignore_for_file: prefer_const_constructors

// import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:skeletonizer/skeletonizer.dart';
import 'color_schemes.g.dart';

import './scanner.dart';

import './utlis.dart' as utlis;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    String title = "Garuda Scanner";
    Future<bool> loaded = utlis.refresh(startup: true);

    return MaterialApp(
      title: title,
      theme: ThemeData(
        colorScheme: lightColorScheme,
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: darkColorScheme,
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false,
      home: FutureBuilder<bool>(
          initialData: null,
          future: loaded,
          builder: (context, snapshot) {
            return Skeletonizer(
              enabled: snapshot.data == null,
              child: HomePage(title: title),
            );
          }),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.title});
  final String title;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  void handleScan(
    context,
    title,
    Future<Map<String, dynamic>> Function(String) affirmFun,
  ) async {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) {
          return ScanPage(
            title: title,
            onScan: (scanRes, context) {
              // var deviceSize = MediaQuery.of(context).size;
              showGeneralDialog(
                context: context,
                pageBuilder: (context, a1, a2) {
                  var rollNoPattern = RegExp(r'\d{2}BD[18]A\d{2}[A-HJ-NP-RT-Z0-9]{2}');
                  var rnos = rollNoPattern.firstMatch(scanRes);
                  if(rnos != null){
                    print(scanRes + "hello");
                    scanRes = rnos[0].toString();
                    print(scanRes);
                  }
                  var affirm = affirmFun(scanRes);
                  return FutureBuilder(
                    future: affirm,
                    builder: (context, snap) {
                      if (snap.data != null) {
                        return Align(
                          alignment: Alignment.topCenter,
                          child: Dialog(
                            backgroundColor: Colors.transparent,
                            child: AffirmBox(
                              isValid: snap.data?["success"],
                              msg: snap.data?["msg"],
                            ),
                          ),
                        );
                      } else {
                        return SpinKitCircle(
                          size: 20,
                          color: Colors.black,
                        );
                      }
                      // return Skeletonizer(
                      //   enabled: snap.data != null,
                      //   child: AffirmBox(
                      //     isValid: snap.data?["success"],
                      //     msg: snap.data?["msg"],
                      //   ),
                      // );
                    },
                  );
                },
              );
            },
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Icon(Icons.arrow_back),
        title: Text(widget.title),
      ),
      body: Align(
        alignment: Alignment(0, -0.4),
        child: ScrollConfiguration(
          behavior: ScrollBehavior(),
          child: SingleChildScrollView(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                MyButton(
                  label: "Scan Passes",
                  todo: () {
                    handleScan(
                      context,
                      "Scan Passes",
                      utlis.getValidity,
                    );
                  },
                ),
                MyButton(
                  label: "Scan Latecomers",
                  todo: () {
                    handleScan(
                      context,
                      "Scan Latecomers",
                      utlis.remLatecomers,
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await utlis.refresh(startup: true);
        },
        child: Icon(Icons.refresh),
        // shape: ,
      ),
    );
  }
}

class AffirmBox extends StatelessWidget {
  const AffirmBox({super.key, required this.isValid, required this.msg});
  final bool isValid;
  final String msg;

  @override
  Widget build(BuildContext context) {
    var deviceSize = MediaQuery.of(context).size;
    return Container(
      height: 3.5 * deviceSize.height / 8,
      width: 6 * deviceSize.width / 8,
      decoration: BoxDecoration(
        borderRadius: const BorderRadius.all(Radius.circular(8)),
        color: Theme.of(context).colorScheme.surface,
      ),
      child: Stack(children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisAlignment: MainAxisAlignment.start,
          children: [
            AffirmIcon(isValid: isValid),
            Divider(
              color: Theme.of(context).colorScheme.surfaceVariant,
              indent: 33,
              endIndent: 33,
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 30),
              child: Text(
                msg,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 20,
                  color: Theme.of(context).colorScheme.onSurface,
                  decoration: TextDecoration.none,
                ),
              ),
            ),
          ],
        ),
        Align(
            alignment: Alignment.bottomCenter,
            child: TextButton(
              onPressed: () {
                Navigator.pop(context);
              },
              child: const Padding(
                padding: EdgeInsets.only(bottom: 8.0),
                child: Text(
                  "Next",
                  style: TextStyle(fontSize: 20),
                ),
              ),
            ))
      ]),
    );
  }
}

class AffirmIcon extends StatelessWidget {
  const AffirmIcon({required this.isValid, super.key});
  final bool isValid;

  final Color green = const Color.fromARGB(255, 7, 141, 63);
  final Color red = const Color.fromARGB(255, 186, 49, 49);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsetsDirectional.symmetric(vertical: 25),
      decoration: BoxDecoration(
        color: ((isValid) ? green : red),
        shape: BoxShape.circle,
      ),
      child: Icon(
        (isValid) ? Icons.done_rounded : Icons.close_rounded,
        color: Colors.white,
        size: 80,
      ),
    );
  }
}

class MyButton extends StatelessWidget {
  const MyButton({super.key, required this.label, required this.todo});
  final String label;
  final void Function() todo;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(15),
      child: ElevatedButton(
        onPressed: todo,
        child: Padding(
          padding: const EdgeInsets.all(5),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 25,
              // fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }
}
