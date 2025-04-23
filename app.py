from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import pandas as pd
import re

app = Flask(__name__)
CORS(app)

# Load Excel file
file_path = 'STUDENTS_DATA_AI_DS.xlsx'

try:
    # Load all required sheets
    students_df = pd.read_excel(file_path, sheet_name='STUDENTS_INFO')
    parent_info_df = pd.read_excel(file_path, sheet_name='PARENT_INFO')
    attendance_df = pd.read_excel(file_path, sheet_name='ATTENDANCE_INFO')
    result_sem1_df = pd.read_excel(file_path, sheet_name='RESULTS_SEM1_INFO')
    result_sem2_df = pd.read_excel(file_path, sheet_name='RESULTS_SEM2_INFO')
    result_sem3_df = pd.read_excel(file_path, sheet_name='RESULTS_SEM3_INFO')
    result_sem4_df = pd.read_excel(file_path, sheet_name='RESULTS_SEM4_INFO')
    result_sem5_df = pd.read_excel(file_path, sheet_name='RESULTS_SEM5_INFO')
    syllabus_df = pd.read_excel(file_path, sheet_name='SYLLABUS_INFO')
    timetable_a_df = pd.read_excel(file_path, sheet_name='TIMETABLE_AI_DS_A')
    timetable_b_df = pd.read_excel(file_path, sheet_name='TIMETABLE_AI_DS_B')
    cgpa_arrear_df = pd.read_excel(file_path, sheet_name='CGPA_AND_ARREAR_INFO')

    # Standardize column names across all sheets
    all_dfs = [
        students_df, parent_info_df, attendance_df,
        result_sem1_df, result_sem2_df, result_sem3_df,
        result_sem4_df, result_sem5_df, syllabus_df,
        timetable_a_df, timetable_b_df, cgpa_arrear_df
    ]
    for df in all_dfs:
        df.columns = df.columns.str.strip().str.upper().str.replace(' ', '_')

    # Normalize SUBJECT_CODE in syllabus_df for safe matching
    syllabus_df['SUBJECT_CODE'] = syllabus_df['SUBJECT_CODE'].astype(str).str.strip().str.upper()

except FileNotFoundError:
    print("❌ Excel file not found. Please check the path.")
    exit()

@app.route('/')
def home():
    return render_template('index.html')

# Utility extractors
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

def extract_subject_code(question):
    match = re.search(r'[A-Z]{3,}\d{3,}', question.upper())
    return match.group(0) if match else None

# Info fetchers
def get_student_info(rrn):
    student = students_df[students_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        return {
            "Student Name": row['NAME_OF_STUDENT'],
            "RRN": rrn,
            "Student Info": row.drop(labels=['RRN']).to_dict()
        }
    return {"response": "Student not found for the provided RRN."}

def get_parent_info(rrn):
    parent = parent_info_df[parent_info_df['RRN'].astype(str) == str(rrn)]
    if not parent.empty:
        row = parent.iloc[0]
        return {
            "Student Name": row['NAME_OF_STUDENT'],
            "RRN": rrn,
            "Parent Info": row.drop(labels=['RRN']).to_dict()
        }
    return {"response": "Parent info not found for the provided RRN."}

def get_attendance(rrn, subject_code=None):
    student = attendance_df[attendance_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        full_attendance = row.drop(labels=['RRN', 'NAME_OF_STUDENT']).to_dict()

        if subject_code:
            filtered = {k: v for k, v in full_attendance.items() if subject_code in k}
            if filtered:
                return {
                    "Student Name": row['NAME_OF_STUDENT'],
                    "RRN": rrn,
                    f"Attendance for {subject_code}": filtered
                }
            else:
                return {
                    "Student Name": row['NAME_OF_STUDENT'],
                    "RRN": rrn,
                    "response": f"No attendance data found for subject code {subject_code}."
                }

        return {
            "Student Name": row['NAME_OF_STUDENT'],
            "RRN": rrn,
            "Attendance": full_attendance
        }

    return {"response": "Attendance not found for the provided RRN."}

def get_result(rrn, semester=None):
    sem_df_map = {
        1: result_sem1_df,
        2: result_sem2_df,
        3: result_sem3_df,
        4: result_sem4_df,
        5: result_sem5_df
    }
    if semester not in sem_df_map:
        return {"response": "Invalid semester. Please specify a valid semester number."}

    df = sem_df_map[semester]
    student = df[df['RRN'].astype(str) == str(rrn)]
    if student.empty:
        return {"response": "Result not found for the provided RRN."}

    row = student.iloc[0]
    return {
        "Student Name": row.get('NAME_OF_STUDENT', 'N/A'),
        "RRN": rrn,
        f"Semester {semester} Result": row.drop(labels=['RRN', 'NAME_OF_STUDENT']).to_dict()
    }

def get_syllabus_for_semester(sem):
    data = syllabus_df[syllabus_df['SEMESTER'] == sem].copy()

    if data.empty:
        return f"No syllabus data found for semester {sem}."

    def linkify(row):
        if 'SUBJECT_CODE' in row and 'SYLLABUS_IMAGE_LINK' in row:
            subject = row['SUBJECT_CODE']
            link = row['SYLLABUS_IMAGE_LINK']
            if pd.notna(link):
                row['SUBJECT_CODE'] = f'<a href="{link}" target="_blank">{subject}</a>'
        return row

    data = data.apply(linkify, axis=1)

    if 'SYLLABUS_IMAGE_LINK' in data.columns:
        data.drop(columns=['SYLLABUS_IMAGE_LINK'], inplace=True)

    return data.to_html(index=False, border=1, escape=False, classes="syllabus-table")

def get_syllabus_image(subject_code):
    matched_row = syllabus_df[syllabus_df['SUBJECT_CODE'] == subject_code.upper()]
    if not matched_row.empty:
        link = matched_row.iloc[0].get('SYLLABUS_IMAGE_LINK')
        if pd.notna(link):
            return {
                "response": f'<a href="{link}" target="_blank"><img src="{link}" style="max-width:100%;height:auto;" alt="Syllabus Image for {subject_code}"></a>'
            }
        else:
            return {"response": f"No syllabus image link found for course {subject_code}."}
    return {"response": f"No syllabus found for subject code {subject_code}."}

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
                if part in venue_codes:
                    color = last_subject_colors[j] or "#ffffff"
                else:
                    color = subject_colors.get(part, "#ffffff")
                    last_subject_colors[j] = color

                styled_parts.append(f'<div style="background-color: {color}; padding: 4px;">{part}</div>')

            styled_df.iat[i, j] = ''.join(styled_parts)

    return f"<b>Timetable for Section {section}:</b><br><br>" + styled_df.to_html(index=False, border=1, classes="timetable-table", escape=False)

def get_cgpa_arrears(rrn):
    student = cgpa_arrear_df[cgpa_arrear_df['RRN'].astype(str) == str(rrn)]
    if not student.empty:
        row = student.iloc[0]
        return {
            "Student Name": row.get('NAME_OF_STUDENT', 'N/A'),
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
        return {
            "Student Name": row.get('NAME_OF_STUDENT', 'N/A'),
            "RRN": rrn,
            "Semester": semester,
            "SGPA": row.get(column, 'N/A')
        }
    return {"response": f"SGPA for semester {semester} not found for RRN {rrn}."}

# Format response
def format_response_data(response):
    if isinstance(response, dict):
        if any(isinstance(v, dict) for v in response.values()):
            formatted = ""
            for key, val in response.items():
                if isinstance(val, dict):
                    formatted += f"\n{key}:\n"
                    for sub_key, sub_val in val.items():
                        formatted += f"  {sub_key}: {sub_val}\n"
                else:
                    formatted += f"{key}: {val}\n"
            return formatted.strip()
        else:
            return '\n'.join([f"{k}: {v}" for k, v in response.items()])
    elif isinstance(response, str):
        return response
    else:
        return str(response)

# Chat route
@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').lower()
    rrn = extract_rrn_from_question(question)
    subject_code = extract_subject_code(question)

    if rrn:
        if "sgpa" in question:
            semester = extract_semester(question)
            response = get_sgpa(rrn, semester) if semester else {"response": "Please specify semester number for SGPA."}
        elif "attendance" in question:
            response = get_attendance(rrn, subject_code)
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
    elif "syllabus" in question and subject_code:
        response = get_syllabus_image(subject_code)
    elif "syllabus" in question:
        semester = extract_semester(question)
        response = get_syllabus_for_semester(semester) if semester else {"response": "Please specify a semester number."}
    elif "timetable" in question:
        section = extract_section(question)
        response = get_timetable_for_section(section) if section else {"response": "Please specify section A or B."}
    else:
        response = {"response": "Sorry, I couldn't understand your question."}

    return jsonify({'response': format_response_data(response)})

if __name__ == '__main__':
    app.run(debug=True)