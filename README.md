# Smart Attendance Monitoring and Visualization System

A GUI-based Flask project to maintain attendance records, calculate attendance percentages with Pandas, and generate graphical reports.

## Features
- Forms to add students and record Present/Absent attendance.
- SQLite database for persistent storage.
- Duplicate attendance prevention per student and date.
- Pandas-based attendance percentage calculation.
- Dashboard summary and low-attendance flag (example threshold: 75%).
- Matplotlib bar chart and CSV report export.
- Optional demo data to test the app quickly.

## Run on Windows
1. Install Python 3.10+.
2. Extract this ZIP and open a terminal in the `smart_attendance_project` folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
5. Start the app:
   ```powershell
   python app.py
   ```
6. Open http://127.0.0.1:5000 in your browser.

Use **Students** to add students, **Attendance** to record attendance, and **Reports** to view the chart and export a CSV. To quickly test, open `/load-demo` in the browser after starting the app.

Attendance percentage = (Present records / Total recorded sessions) × 100.

This is a local academic mini-project, not a production-hardened deployment. Change the Flask secret key and remove/protect the demo-data route before public deployment.
