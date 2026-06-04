"""Report service – fetches data and generates CSV, Excel, and PDF reports."""

import io
import csv
from datetime import datetime
from bson import ObjectId
from app.database.mongodb import get_db
from app.utils.timezone import format_date, format_datetime

import openpyxl
from fpdf import FPDF


def get_report_data(start_date, end_date, team="All", employee_id="All"):
    """
    Fetch flattened task data across a date range.
    Filterable by team and employee_id.
    Returns a list of dicts representing rows.
    """
    db = get_db()
    
    # Base query for submissions
    query = {
        "week_start": {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date, datetime.min.time()),
        }
    }
    
    if employee_id and employee_id != "All":
        query["employee_id"] = ObjectId(employee_id)
        
    subs = list(db.weekly_submissions.find(query).sort("week_start", -1))
    
    # We might need to filter by team if employee_id isn't provided,
    # or just to enforce team boundaries.
    # To do this efficiently, let's fetch matching employees first.
    emp_query = {"role": "employee"}
    if team and team != "All":
        emp_query["team"] = team
    if employee_id and employee_id != "All":
        emp_query["_id"] = ObjectId(employee_id)
        
    employees = list(db.employees.find(emp_query))
    emp_dict = {str(e["_id"]): e for e in employees}
    
    rows = []
    for sub in subs:
        emp = emp_dict.get(str(sub["employee_id"]))
        if not emp:
            continue # Employee doesn't match team filter
            
        emp_name = emp.get("name", "Unknown")
        emp_team = emp.get("team", "")
        week_label = f"{format_date(sub['week_start'])} to {format_date(sub['week_end'])}"
        sub_date = format_datetime(sub.get("submitted_at"))
        
        for task in sub.get("tasks", []):
            cd = task.get("completion_date")
            cd_fmt = format_date(cd) if isinstance(cd, datetime) else cd or "N/A"
            
            sd = task.get("start_date")
            sd_fmt = format_date(sd) if isinstance(sd, datetime) else sd or "N/A"
            
            rows.append({
                "Employee": emp_name,
                "Team": emp_team,
                "Week": week_label,
                "Submitted At": sub_date,
                "Task Name": task.get("task_name", ""),
                "Description": task.get("task_description", ""),
                "Type": task.get("task_type", ""),
                "Start Date": sd_fmt,
                "Completion Date": cd_fmt,
            })
            
    return rows


def generate_csv(data: list[dict]) -> io.StringIO:
    """Generate a CSV buffer from report data."""
    output = io.StringIO()
    if not data:
        return output
        
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    output.seek(0)
    return output


def generate_excel(data: list[dict]) -> io.BytesIO:
    """Generate an Excel (.xlsx) buffer from report data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tasks Report"
    
    if not data:
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
        
    headers = list(data[0].keys())
    ws.append(headers)
    
    # Basic styling for headers
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        
    for row in data:
        ws.append([row[h] for h in headers])
        
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def generate_pdf(data: list[dict], title="Task Report") -> io.BytesIO:
    """Generate a simple PDF buffer from report data."""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    if not data:
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, "No data available.", new_x="LMARGIN", new_y="NEXT")
        output = io.BytesIO(pdf.output())
        return output

    # For PDF, we might need to subset columns to fit on the page.
    # Let's pick the most important ones to prevent overlap:
    # Employee, Team, Task Name, Type, Status/Completion
    cols = ["Employee", "Task Name", "Type", "Completion Date"]
    
    pdf.set_font("helvetica", "B", 10)
    col_widths = [45, 85, 25, 35]
    
    # Header
    for i, col in enumerate(cols):
        pdf.cell(col_widths[i], 10, col, border=1)
    pdf.ln()
    
    # Rows
    pdf.set_font("helvetica", "", 9)
    for row in data:
        # Truncate strings to fit
        emp = str(row.get("Employee", ""))[:20]
        task = str(row.get("Task Name", ""))[:50]
        typ = str(row.get("Type", ""))[:15]
        comp = str(row.get("Completion Date", ""))[:15]
        
        pdf.cell(col_widths[0], 8, emp, border=1)
        pdf.cell(col_widths[1], 8, task, border=1)
        pdf.cell(col_widths[2], 8, typ, border=1)
        pdf.cell(col_widths[3], 8, comp, border=1)
        pdf.ln()
        
    output = io.BytesIO(pdf.output())
    return output
