from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pandas as pd
import re

app = Flask(__name__)
CORS(app)

# Load Excel file
file_path = 'STUDENTS_DATA_AI_DS.xlsx'

try:
    students_df = pd.read_excel(file_path, sheet_name='STUDENTS_INFO')
    parent_info_df = pd.read_excel(file_path, sheet_name='PARENT_INFO')
    attendance_df = pd.read_excel(file_path, sheet_name='ATTENDANCE_INFO')
    result_df = pd.read_excel(file_path, sheet_name='RESULTS_INFO')
    syllabus_df = pd.read_excel(file_path, sheet_name='SYLLABUS_INFO')
    timetable_a_df = pd.read_excel(file_path, sheet_name='TIMETABLE_AI_DS_A')
    timetable_b_df = pd.read_excel(file_path, sheet_name='TIMETABLE_AI_DS_B')
    cgpa_arrear_df = pd.read_excel(file_path, sheet_name='CGPA_AND_ARREAR_INFO')

    # Clean headers
    for df in [students_df, parent_info_df, attendance_df, result_df, syllabus_df, timetable_a_df, timetable_b_df, cgpa_arrear_df]:
        df.columns = df.columns.str.strip().str.upper()

except FileNotFoundError:
    print("❌ Excel file not found. Please check the path.")
    exit()

@app.route('/')
def home():
    return render_template('index.html')

# === Utility extractors ===
def extract_rrn_from_question(question):
    match = re.search(r'\b\d{12}\b', question)
    return match.group(0) if match else None

def extract_semester(question):
    match = re.search(r'semester\s*(\d+)', question, re.IGNORECASE)
    return int(match.group(1)) if match else None

def extract_section(question):
    if "a section" in question or "section a" in question:
        return 'A'
    elif "b section" in question or "section b" in question:
        return 'B'
    return None

# === Info fetchers ===
def get_student_info(rrn):
    student = students_df[students_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        return {
            "Student Name": row['NAME OF STUDENT'],
            "RRN": rrn,
            "Student Info": row.drop(labels=['RRN']).to_dict()
        }
    return {"response": "Student not found for the provided RRN."}

def get_parent_info(rrn):
    parent = parent_info_df[parent_info_df['RRN'].astype(str) == str(rrn)]
    if not parent.empty:
        row = parent.iloc[0]
        return {
            "Student Name": row['NAME OF STUDENT'],
            "RRN": rrn,
            "Parent Info": row.drop(labels=['RRN']).to_dict()
        }
    return {"response": "Parent info not found for the provided RRN."}

def get_attendance(rrn):
    student = attendance_df[attendance_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        return {
            "Student Name": row['NAME_OF_STUDENT'],
            "RRN": rrn,
            "Attendance": row.drop(labels=['RRN', 'NAME_OF_STUDENT']).to_dict()
        }
    return {"response": "Attendance not found for the provided RRN."}

def get_result(rrn, semester=None):
    student = result_df[result_df['RRN'].astype(str) == str(rrn)]
    if student.empty:
        return {"response": "Result not found for the provided RRN."}
    
    if semester:
        sem_data = student[student['SEMESTER'] == semester]
        if sem_data.empty:
            return {"response": f"Result not found for Semester {semester}."}
        row = sem_data.iloc[0]
        return {
            "Student Name": row.get('NAME_OF_STUDENT', 'N/A'),
            "RRN": rrn,
            f"Semester {semester} Result": row.drop(labels=['RRN', 'NAME_OF_STUDENT', 'SEMESTER']).to_dict()
        }
    else:
        all_sem_results = {}
        grouped = student.groupby('SEMESTER')
        for sem, group in grouped:
            row = group.iloc[0]
            all_sem_results[f"Semester {sem}"] = row.drop(labels=['RRN', 'NAME_OF_STUDENT', 'SEMESTER']).to_dict()
        return {
            "Student Name": student.iloc[0].get('NAME_OF_STUDENT', 'N/A'),
            "RRN": rrn,
            "All Semester Results": all_sem_results
        }

def get_syllabus_for_semester(sem):
    data = syllabus_df[syllabus_df['SEMESTER'] == sem]
    return data.to_html(index=False, border=1, classes="syllabus-table") if not data.empty else f"No syllabus data found for semester {sem}."

def get_timetable_for_section(section):
    df = timetable_a_df if section == 'A' else timetable_b_df if section == 'B' else None
    if df is None:
        return "No timetable data found."

    df = df.fillna('')
    subject_colors = {
        "CSD3251": "#f0e68c", "CSDX631": "#add8e6",
        "SSDX11": "#98fb98", "SSDX12": "#98fb98", "SSDX13": "#98fb98", "SSDX14": "#98fb98",
        "CSDX626": "#87ceeb", "CSDX627": "#87ceeb",
        "CSD631": "#afeeee", "CSD3252": "#dda0dd", "OPEN ELECTIVE": "#f5deb3"
    }

    venue_codes = {"LS002", "LS003", "LS004", "ES303"}

    styled_df = df.copy()
    last_subject_colors = ["" for _ in df.columns]

    for i, row in df.iterrows():
        for j, cell in enumerate(row):
            if not cell:
                styled_df.iat[i, j] = ''
                continue

            parts = [p.strip() for p in str(cell).split('/')]
            styled_parts = []

            for part in parts:
                # Inherit color if it's a venue
                if part in venue_codes:
                    color = last_subject_colors[j] or "#ffffff"
                else:
                    color = subject_colors.get(part, "#ffffff")
                    last_subject_colors[j] = color  # update last subject

                styled_parts.append(f'<div style="background-color: {color}; padding: 4px;">{part}</div>')

            styled_df.iat[i, j] = ''.join(styled_parts)

    html_table = styled_df.to_html(index=False, border=1, classes="timetable-table", escape=False)
    return f"<b>Timetable for Section {section}:</b><br><br>{html_table}"

def get_cgpa_arrears(rrn):
    student = cgpa_arrear_df[cgpa_arrear_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        return {
            "Student Name": row.get('NAME OF STUDENT', 'N/A'),
            "RRN": rrn,
            "CGPA": row.get('CGPA', 'N/A'),
            "Number of Arrears": int(row.get('NUMBER_OF_ARREARS', 0)),
            "Status": row.get('STATUS', '')
        }
    return {"response": "CGPA or arrear info not found for the provided RRN."}

def get_sgpa(rrn, semester):
    column = f'SEMESTER_{semester}_SGPA'
    student = cgpa_arrear_df[cgpa_arrear_df['RRN'].astype(str) == str(rrn)]
    if not student.empty and column in cgpa_arrear_df.columns:
        row = student.iloc[0]
        sgpa = row.get(column, 'N/A')
        return {
            "Student Name": row.get('NAME OF STUDENT', 'N/A'),
            "RRN": rrn,
            "Semester": semester,
            "SGPA": sgpa
        }
    return {"response": f"SGPA for semester {semester} not found for RRN {rrn}."}

# === Main Chat Route ===
@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').lower()
    rrn = extract_rrn_from_question(question)

    if rrn:
        if "sgpa" in question:
            semester = extract_semester(question)
            response = get_sgpa(rrn, semester) if semester else {"response": "Please specify semester number for SGPA."}
        elif "attendance" in question:
            response = get_attendance(rrn)
        elif "result" in question or "marks" in question:
            semester = extract_semester(question)
            response = get_result(rrn, semester)
        elif "student" in question:
            response = get_student_info(rrn)
        elif "parent" in question:
            response = get_parent_info(rrn)
        elif "cgpa" in question or "arrear" in question:
            response = get_cgpa_arrears(rrn)
        else:
            response = {"response": "Please ask about SGPA, CGPA, attendance, result, or parent info."}
    elif "syllabus" in question:
        semester = extract_semester(question)
        response = get_syllabus_for_semester(semester) if semester else {"response": "Please specify a semester number."}
    elif "timetable" in question:
        section = extract_section(question)
        response = get_timetable_for_section(section) if section else {"response": "Please specify section A or B."}
    else:
        response = {"response": "Sorry, I couldn't understand your question."}

    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)