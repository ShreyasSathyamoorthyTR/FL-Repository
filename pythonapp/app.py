import psycopg2
import csv
import json
from contextlib import contextmanager
import pandas as pd
from flask import (Flask, Response, stream_with_context, render_template, redirect, url_for,
                   request, session, make_response)
from io import StringIO
import configparser

# Configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Database credentials
hostname = 'localhost'
database = 'dump'
username = config.get('database', 'username')
pwd = config.get('database', 'pwd')
port_id = config.getint('database', 'port_id')

# Initialize Flask app
app = Flask(__name__)

# In-memory caches
extracted_data_cache = {}
extracted_data_cache_areas = {}

# Utility functions
def to_capital(x):
    xx = []
    y = ""
    for i in range(0, len(x)):
        if x[i] == " ":
            xx.append(i)
    for i in xx:
        y = x[:i+1] + x[i+1].capitalize() + x[i+2:]
    return y

def to_hyphen(text):
    return '-'.join(text.lower().split(" "))

# Routes
@app.route('/')
def index():
    return render_template("index.html")

'''
This API retrieves the URL (get_url) and state (get_state) information from the input text box.
It then matches the input with the database and extracts the required data (extracted_data).
This data is stored in a cache as a dictionary (extracted_data_cache).

There are two main outcomes based on the condition:
1. If a URL is entered, the user is redirected to the `display_all_fields` function.
2. If a state is entered, the output data is assigned to `data_table=extracted_data`.
'''
@app.route('/', methods=['POST', 'GET'])
def input_url_and_state():
    get_url = request.form.get('url')
    get_state = request.form.get('state')
    x = ""
    conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit = True
    if get_url:
        cur.execute(f"SELECT * FROM dumps WHERE URL='{get_url}' LIMIT 1")
        x = "url"
    elif get_state:
        get_state = get_state.strip()
        cur.execute(f"SELECT * FROM dumps WHERE state @> ARRAY['{to_capital(get_state.capitalize())}'] OR state @> ARRAY['{get_state.capitalize()}']")
        x = "state"
    extracted_data = cur.fetchall()
    session_id = request.cookies.get('session_id')
    extracted_data_cache[session_id] = extracted_data
    if x == "url":
        que = get_url.strip('http://www.').strip('.com')
        return redirect(url_for('display_all_fields', session_id=f'url_{que}'))
    elif x == "state":
        condition = True
        return render_template('index.html', condition5=condition, data_table=extracted_data, condition4=condition)
    else:
        return "Data entered is Invalid"



'''
This function displays all columns from the extracted data. When a button is clicked,
it will render the template from the `display_all_fields_post` function.
'''

@app.route('/extraction/<session_id>')
def display_all_fields(session_id):
    condition = True
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    middle = f"Select the dumps required for the url {extracted_data[0][1]}"
    return render_template('index.html', condition=condition, middle=middle)


'''
This function is used to display the data for the selected column from the extracted data.

This function displays the data for the selected column. The output is saved in a variable called `data`.
For columns related to pages, it returns a list of page categories stored in the variable `page_category`, which is sorted and deduplicated.
'''

@app.route('/extraction', methods=['POST', 'GET'])
def display_all_fields_post():
    button_id = request.form['button_id']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    condition = True
    middle = f"The dumps for the url {extracted_data[0][1]}"
    if button_id == "law_firm_name":
        return render_template('index.html', condition=condition, data=(extracted_data[0][2]), condition1=condition, middle=middle)
    elif button_id == "phone_number":
        return render_template('index.html', condition=condition, data=(extracted_data[0][6]), condition2=condition, middle=middle)
    elif button_id == "geographic_location":
        return render_template('index.html', condition=condition, data=(extracted_data[0][3]), condition2=condition, middle=middle)
    elif button_id == "state":
        return render_template('index.html', condition=condition, data=(extracted_data[0][4]), condition2=condition, middle=middle)
    elif button_id == "city":
        return render_template('index.html', condition=condition, data=(extracted_data[0][5]), condition2=condition, middle=middle)
    elif button_id == "all_details":
        return render_template('index.html', condition=condition, data=extracted_data[0][1:], condition3=condition, middle=middle, condition4=condition)
    elif button_id == "pages" or request.args.get('par') == "pages":
        page_category = [i['page_category'] for i in extracted_data[0][8] if len(i) != 0]
        extracted_data.append(page_category)
        return render_template('index.html', page_category=sorted(list(set(page_category))), condition=condition, condition2=condition, middle=middle)


'''
This function displays all the main categories of the selected page. 
If there are multiple categories with the same name, it will return a list of specific page categories for the main category, stored in the variable `specific_category_content`, which is sorted.
Otherwise, it will return the output data in `category_content`.
'''

@app.route("/category_main", methods=['POST', 'GET'])
def page_category():
    category_main = request.form['category_main']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extracted_data.append(category_main)
    condition = True
    lists = [i for i in extracted_data[0][8] if len(i) != 0 and i['page_category'] == category_main]
    if len(lists) == 1:
        category_content = lists[0]
        return render_template('index.html', page_category=sorted(list(set(extracted_data[1]))), category_content=category_content, condition=condition, condition2=condition, middle=f"The dumps for the url {extracted_data[0][1]}")
    elif len(lists) >= 2:
        specific_lists = [i['specific_page_Category'] for i in lists]
        extracted_data.append(specific_lists)
        return render_template('index.html', page_category=sorted(list(set(extracted_data[1]))), specific_category_content=sorted(specific_lists), condition=condition, condition2=condition, middle=f"The dumps for the url {extracted_data[0][1]}")

'''
This function retrieves the selected specific page category, which is stored in the variable `specific_category_main`.
It then returns `specific_data`, which contains the details of the selected page.
'''
@app.route("/specific_category_main", methods=['POST', 'GET'])
def specific_page_Category():
    specific_category_main = request.form['specific_category_main']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    specific_lists = extracted_data[-1]
    specific_data = next((i for i in extracted_data[0][8] if len(i) != 0 and i["page_category"] == extracted_data[-2] and i['specific_page_Category'] == specific_category_main), None)
    return render_template('index.html', page_category=sorted(list(set(extracted_data[1]))), specific_category_content=sorted(specific_lists), condition=True, condition2=True, middle=f"The dumps for the url {extracted_data[0][1]}", specific_data=specific_data)

@app.route("/specific_area", methods=['POST', 'GET'])
def specific_area():
    main_area = request.form['main_area']
    conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit = True
    script = f"SELECT specific_category FROM area_new WHERE area='{main_area}'"
    cur.execute(script)
    specific_category = cur.fetchall()
    dicccc = {"main_areas": main_area, "specific_category_list": []}
    specific_categories = list((specific_category[0][0][0])[1:-1].split("','"))
    dicccc['specific_category_list'] = [ ' '.join(i.split("-")) for i in specific_categories ]
    session_id = request.cookies.get('session_id_areas')
    extracted_data_cache_areas[session_id] = [dicccc]
    return render_template('index.html', specific_category=dicccc['specific_category_list'])

@app.route("/main_category", methods=['POST', 'GET'])
def main_category():
    main_category = '-'.join(request.form['specific_category'].split(" "))
    session_id = session.get('session_id_areas')
    extracted_data = extracted_data_cache_areas.get(session_id, [])
    conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit = True
    script = f"SELECT content FROM area_new WHERE area='{extracted_data[0]['main_areas']}'"
    cur.execute(script)
    dataa = cur.fetchall()
    return render_template('index.html', contentt=dataa[0][0].get(main_category, ""), specific_category=extracted_data[0]['specific_category_list'])

#function to download the json file
@app.route("/download_json")
def download_json():
    data_to_json = []
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extracted_data = [i for i in extracted_data if len(i) == 9 and isinstance(i[0], int) and isinstance(i[8], list) and isinstance(i[3], list) and isinstance(i[4], list)]
    for data in extracted_data:
        data_to_json.append({
            "URL": data[1],
            "Law Firm Name": data[2],
            "Geographic Location": data[3],
            "City": data[4],
            "State": data[5],
            "Phone Number": data[6]
        })
    json_data = json.dumps(data_to_json)
    response = make_response(json_data)
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    response.mimetype = 'application/json'
    return response

#function to download the csv file
@app.route("/download_csv")
def download_csv():
    data_to_json = []
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extracted_data = [i for i in extracted_data if len(i) == 9 and isinstance(i[0], int) and isinstance(i[8], list) and isinstance(i[3], list) and isinstance(i[4], list)]
    for data in extracted_data:
        data_to_json.append({
            "URL": data[1],
            "Law Firm Name": data[2],
            "Geographic Location": data[3],
            "City": data[4],
            "State": data[5],
            "Phone Number": data[6]
        })

    def generate_csv():
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["URL", "Law Firm Name", "Geographic Location", "City", "State", "Phone Number"])
        writer.writeheader()
        for row in data_to_json:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate()

    response = Response(stream_with_context(generate_csv()), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=sample_data.csv'
    return response

# Run the Flask app
if __name__ == '__main__':
    app.run(port=5001)
