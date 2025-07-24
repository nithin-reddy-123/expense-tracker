from datetime import date, timedelta
import platform
import sqlite3
import bcrypt
import json
import re
import pandas as pd
import streamlit as st
import plotly.express as px
from langchain_groq import ChatGroq
from PIL import Image
import pytesseract
from database import insert_user, get_user_by_username, insert_expense, get_expenses_by_user, get_all_users

if platform.system() == "Darwin":  # macOS local dev
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

st.markdown("<h1 style='text-align: center;'>Expense tracker</h1>", unsafe_allow_html=True)

query_params = st.query_params

# Your Groq API Key stored in secrets file
api_key = st.secrets["api"]["api_key"]

# Setup LLM
llm = ChatGroq(
        groq_api_key=api_key,
        model_name="llama3-8b-8192",
        streaming=True
    )

page = st.query_params.get("page", "login")

def update_url(new_url):
    st.query_params = {"page":new_url}
    st.rerun()


def extract_expense_from_text(text):
    today = date.today()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    current_year = today.year
    current_month = today.month

    prompt = f"""
    Extract a single total expense from the following text.

    Output must be valid JSON with the following keys:
    - description (brief and human-readable)
    - amount (float, without $ symbol)
    - date (in YYYY-MM-DD format). 
      → If "today" is mentioned, use "{today_str}".
      → If "yesterday" is mentioned, use "{yesterday_str}".
      → If a day and month are mentioned (e.g., "20th May") **without a year**, assume the year is {current_year}.
      → If only a day is mentioned (e.g., "20th May") **without month and year**, assume the month is {current_month} and the year is {current_year}.
      → Otherwise, use the date from the text or default to "{today_str}" if missing.

    - category (e.g., Food, Travel, Shopping, Medical, Utilities, etc.)

    Assume the total expense includes all line items. Only return ONE total expense.

    Return valid JSON only.

    Text:
    \"\"\"{text}\"\"\"
    """

    response = llm.invoke(prompt)

    try:
        json_match = re.search(r"\{.*?\}", response.content, re.DOTALL)
        if not json_match:
            raise ValueError("No valid JSON object found in LLM response")
        parsed = json.loads(json_match.group())
        return parsed
    except Exception as e:
        st.error(f"Failed to extract expense from text: {e}")
        st.write("Raw LLM output:")
        st.code(response.content)
        return None

def plot_expenses_charts(expenses, start_date, end_date):

    if not expenses:
        st.warning("No expenses found")
        return
    
    df = pd.DataFrame(expenses)
    
    if df.shape[1] == 6:
        df.columns = ["id", "user_id", "amount", "category", "date", "description"]
    elif df.shape[1] == 5:
        df.columns = ["user_id", "amount", "category", "date", "description"]
    else:
        st.error(f"Unexpected number of columns in expenses data: {df.shape[1]}")
        st.write(df.head())
        return
    
    if df['date'].dtype == object:
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    
    df = df.dropna(subset=['date'])
    
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    if df_filtered.empty:
        st.warning("No expenses found in the selected date range")
        return
    
    df_bar = df_filtered.groupby('date')['amount'].sum().reset_index()
    
    df_pie = df_filtered.groupby('category')['amount'].sum().reset_index()
    
    st.subheader(f"Expenses from {start_date} to {end_date}")
    
    # Bar chart: Expenses over time
    fig_bar = px.bar(
        df_bar,
        x='date',
        y='amount',
        labels={'date': 'Date', 'amount': 'Amount'},
        title="Expenses Over Time"
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Pie chart: Expenses by category
    fig_pie = px.pie(
        df_pie,
        names='category',
        values='amount',
        title="Expenses by Category"
    )
    st.plotly_chart(fig_pie, use_container_width=True)


def expense_tracker():
    #If user refreshed tab
    if 'username' not in st.session_state:
        update_url("login")
    
    #variables to track chosen way to add expense
    manual_input=None
    uploaded_file=None
    form_input=None

    st.header(f"Welcome, {st.session_state.username}!")

    print(f"users {get_all_users}")
    #drop down to select the way to add an expense
    expense_way = st.selectbox("How do you want to add an expense:",
                               ["By describing expense","Expense form","Uploading expense image"])
    # st.write(f"You've selected :{expense_way}");

    # by entering expense description
    if expense_way == "By describing expense":
        manual_input = st.text_area("Enter your expense manually here, try including expense amount and expense description:", height=150)
        submit_input = st.button("Submit")
        if manual_input and submit_input:
            expense_description_data=extract_expense_from_text(manual_input)
            if expense_description_data:
                st.write("Parsed expense data: ", expense_description_data)
                try:
                    insert_expense(
                            st.session_state.user_id,
                            float(expense_description_data["amount"]),
                            expense_description_data["category"],
                            expense_description_data["date"],  
                            expense_description_data["description"]
                    )
                    expenses = get_expenses_by_user(st.session_state.user_id)
                    print(f"expenses {expenses}")
                    st.success("Expense successfully added!")
                    st.session_state.last_added_date = expense_description_data["date"]
                except Exception as e:
                    st.error(f"Error inserting into database: {e}")

    #by uploading expense file
    elif expense_way == "Uploading expense image":
        uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        upload_button = st.button("Upload")
        if uploaded_file and upload_button:
            img = Image.open(uploaded_file)
            text = pytesseract.image_to_string(img)
            st.write(text);
            expense_data=extract_expense_from_text(text)
            if expense_data:
                st.write("Parsed expense data: ", expense_data)
                try:
                    insert_expense(
                        st.session_state.user_id,
                        float(expense_data["amount"]),
                        expense_data["category"],
                        expense_data["date"], 
                        expense_data["description"]
                    )
                    expenses = get_expenses_by_user(st.session_state.user_id)
                    print(f"expenses {expenses}")
                    st.success("Expense successfully added!")
                    st.session_state.last_added_date = expense_data["date"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error inserting into database: {e}")
            
    #by filling form
    else:
        form_input = st.form("expense_form")
        with form_input:
            description = st.text_input("Expense Description")
            amount = st.number_input("Expense Amount", min_value=0.0, format="%.2f")
            expense_date = st.date_input("Expense Date", value=date.today())
            category = st.selectbox("Category", ["Food", "Travel", "Utilities", "Shopping", "Other"])
            submitted = st.form_submit_button("Add Expense")

        if submitted:
            insert_expense(st.session_state.user_id,amount,category,expense_date,description)
            expenses = get_expenses_by_user(st.session_state.user_id)
            print(f"expenses {expenses}")
            st.success(f"Added: {description} | ₹{amount:.2f} | {expense_date} | Category: {category}")
            st.session_state.last_added_date = expense_date
    st.header("View Expenses by Date Range")

    # Default dates: last 30 days
    today = date.today()
    last_added_raw = st.session_state.get("last_added_date", today)
    last_added = pd.to_datetime(last_added_raw).date() if isinstance(last_added_raw, str) else last_added_raw

    default_start = min(today - timedelta(days=30), last_added)
    default_end = today

    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=default_end)

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
    else:
        # Fetch expenses for user
        expenses = get_expenses_by_user(st.session_state.user_id)  # your function here
        plot_expenses_charts(expenses, start_date, end_date)

def login_page():
    error_message = None

    username = st.text_input("Username", value="", max_chars=16, placeholder="Enter your username").strip()
    password = st.text_input("Password", max_chars=16, placeholder="Enter your password", type="password")

    st.write("Don't have an account already?")
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        if st.button("Signup"):
            update_url("signup")
            # st.rerun()
    with col3:
        if st.button("Login"):
            if not username or not password:
                error_message = "Please enter both username and password"
            else:
                result = get_user_by_username(username)
                if result and bcrypt.checkpw(password.encode(), result[1].encode()):
                    st.session_state.user_id = result[0]
                    st.session_state.username = username
                    update_url("expenses")
                    # st.rerun()
                else:
                    error_message = "Invalid username or password"

    if error_message:
        st.error(error_message)




def signup_page():
    error_message=None
    success_message=None
    username = st.text_input("Choose username", key="signup_username").strip()
    password = st.text_input("Choose password", type="password", key="signup_password")
    confirm = st.text_input("Confirm password", type="password", key="signup_confirm_password")
    col1,col2,col3 = st.columns([2,5,1.25])
    with col1:
        if st.button("Back to Login"):
            update_url("login")
            # st.rerun()
    with col3:
        if st.button("Register"):
            if not username or not password or not confirm:
                error_message = "Please fill in all fields"
            elif password != confirm:
                error_message = "Passwords do not match"
            elif len(password) < 6:
                error_message = "Password must be at least 6 characters"
            else:
                hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                try:
                    insert_user(username, hashed_pw)
                    success_message = "Signup successful! Login now"
                except ValueError:
                    error_message = "Username already exists"
                except Exception:
                    error_message = "Something went wrong. Please try again."
    if error_message:
        st.error(error_message)
    if success_message:
        st.success(success_message)

if page=="login":
    login_page()
elif page=="signup":
    signup_page()
elif page=="expenses":
    expense_tracker()

