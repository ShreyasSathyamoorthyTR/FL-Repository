import psycopg2
import tempfile,csv,json,os,io
from contextlib import contextmanager
import pandas as pd
from flask import Response, stream_with_context,Blueprint,render_template,redirect,url_for, request, session,make_response,send_file, Flask
from io import StringIO
import configparser


config = configparser.ConfigParser()
config.read('config.ini')
    
    
extracted_data_cache = {}
extracted_data_cache_areas = {}

hostname='localhost'
database='dump'
username=config.get('database', 'username')
pwd=config.get('database', 'pwd')
port_id=config.getint('database', 'port_id')
from flask import Flask

app =Flask(__name__)

#Api which will display the front page
@app.route('/')
def index():
    return render_template("index.html")

'''
This Api is used to get the url(get_url) and state(get_state) information from the input text box
Then we will be matching that input with the database and extract the required data(extracted_data)
Then it is appended to a cache as a dictionary(extracted_data_cache)
'''
'''
TWO MAIN OUTPUTS as we have if condition
IF url is entered, then it redirects to display_all_fields function
ELSE if state is entered, then the output data is 'data_table=extracted_data'
'''

@app.route('/', methods=['POST','GET'])
def input_url_and_state():
    get_url=request.form.get('url')
    get_state=request.form.get('state')
    x=""
    conn=psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit= True
    if len(get_url)!=0:
        cur.execute(f"SELECT * FROM dumps WHERE URL='{get_url}' LIMIT 1")
        x="url"
    elif len(get_state) != 0:
        get_state=get_state.strip()
        def to_capital(x):
            xx=[]
            y=""
            for i in range(0,len(x)):
                if x[i]==" ":
                    xx.append(i)
            for i in xx:
                y=x[:i+1]+x[i+1].capitalize()+x[i+2:]
            return y
        cur.execute(f'''SELECT * FROM dumps WHERE state @> ARRAY['{to_capital(get_state.capitalize())}'] or state @> ARRAY['{get_state.capitalize()}']''')
        x="state"
    extracted_data=cur.fetchall()
    if x=="url":
        session_id = request.cookies.get('session_id')
        extracted_data_cache[session_id] = extracted_data
        que=(get_url.strip('http://www.')).strip('.com')
        return redirect(url_for('display_all_fields',session_id=f'url_{que}'))
    elif x=="state":
        session_id = request.cookies.get('session_id')
        extracted_data_cache[session_id] = extracted_data
        condition=True
        #extracted_data will contain list of dictionaries which contains all the details about the matching law_firms
        return render_template('index.html',condition5=condition,data_table=extracted_data,condition4=condition)
    else:
        extracted_data=[]
        return "Data entered is Invalid"


'''
This function is used to display all the columns from the extracted data and when that button is clicked
it will render the template from display_all_fields_post function
'''




@app.route('/extraction/<session_id>')
def display_all_fields(session_id):
    condition=True
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    middle=f"Select the dumps required for the url {extracted_data[0][1]}"
    return render_template('index.html',condition=condition,middle=middle)
    
    

'''
This function is used to display the selected column data from the extracted data
'''
'''
This function is used for displaying the column selected
And the OUTPUT  is saved in a variable 'data'
except for column pages it will return a list of page categories in a variable 'page_category=sorted(list(set(page_category)))'

'''




@app.route('/extraction', methods=['POST','GET'])
def display_all_fields_post():
    button_id=request.form['button_id']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    condition=True
    middle=f"The dumps for the url {extracted_data[0][1]}"
    if button_id=="law_firm_name":
        return render_template('index.html',condition=condition,data=((extracted_data[0][2])),condition1=condition,middle=middle)
    if button_id=="phone_number":
        return render_template('index.html',condition=condition,data=((extracted_data[0][6])),condition2=condition,middle=middle)
    if button_id=="geographic_location":
        return render_template('index.html',condition=condition,data=((extracted_data[0][3])),condition2=condition,middle=middle)
    if button_id=="state":
        return render_template('index.html',condition=condition,data=((extracted_data[0][4])),condition2=condition,middle=middle)
    if button_id=="city":
        return render_template('index.html',condition=condition,data=((extracted_data[0][5])),condition2=condition,middle=middle)
    if button_id=="all_details":
        return render_template('index.html',condition=condition,data=extracted_data[0][1:],condition3=condition,middle=middle,condition4=condition)   
    if button_id=="pages" or request.args.get('par')=="pages" :
        page_category=[]
        for i in extracted_data[0][8]:
            if len(i)!=0:
                page_category.append(i['page_category'])
        extracted_datas=extracted_data
        extracted_datas.append(page_category) 
        extracted_data=extracted_datas
        return render_template('index.html',page_category=sorted(list(set(page_category))),condition=condition,condition2=condition,middle=middle)
     



'''
This function will display all the main categories of the selected page
If there are multiple categories of same name, then it will return a list of specific page categories of the main category in variable 'specific_category_content=sorted(specific_lists)'
Else it will return the output data in 'category_content'
'''



@app.route("/category_main", methods=['POST','GET'])
def page_category():
    category_main=request.form['category_main']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extracted_data.append(category_main)
    
    
    condition=True
    lists=[]
    page_category=extracted_data[1]
    middle=f"The dumps for the url {extracted_data[0][1]}"
    for i in extracted_data[0][8]:
        if len(i)!=0:
            if i['page_category'] == category_main:
                lists.append(i)
    if len(lists)==1:
        category_content=lists[0]
        return render_template('index.html',page_category=sorted(list(set(page_category))),category_content=category_content,condition=condition,condition2=condition,middle=middle)
    if len(lists)>=2:
        specific_lists=[]
        for i in lists:
            specific_lists.append(i['specific_page_Category'])
        extracted_data.append(specific_lists)
        return render_template('index.html',page_category=sorted(list(set(page_category))),specific_category_content=sorted(specific_lists),condition=condition,condition2=condition,middle=middle)

'''
This function will get the selected specific page category in the variable 'specific_category_main'
then it will return 'specific_data=specific_data' which has the details of the page
'''




@app.route("/specific_category_main", methods=['POST','GET'])
def specific_page_Category():
    specific_category_main=request.form['specific_category_main']
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    page_category=extracted_data[1]
    middle=f"The dumps for the url {extracted_data[0][1]}"
    specific_lists=extracted_data[-1]
    condition=True
    for i in extracted_data[0][8]:
        if len(i)!=0:
            if i["page_category"]==extracted_data[-2] and i['specific_page_Category']==specific_category_main:
                specific_data=i
    return render_template('index.html',page_category=sorted(list(set(page_category))),specific_category_content=sorted(specific_lists),condition=condition,condition2=condition,middle=middle,specific_data=specific_data)

def to_hiffen(text):
    text_list=list((text.lower()).split(" "))
    out=""
    for i in text_list:
        out=out+(i+"-")
    return out
    




@app.route("/specific_area", methods=['POST','GET'])
def specific_area():
    main_area=request.form['main_area']
    conn=psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit= True
    script=f'''
    SELECT specific_category FROM area_new WHERE area='{(main_area)}'
    '''
    cur.execute(script)
    specific_category= (cur.fetchall())
    dicccc={
        "main_areas":"",
        "specific_category_list":[]
    }
    dicccc['main_areas']=main_area
    
    
    
    new=(specific_category[0][0][0])
    specific_categories=list(new[1:-1].split("','"))
    specific_category=[]
    for i in specific_categories:
        yz=' '.join(list(i.split("-")))
        specific_category.append(((yz)))
    dicccc['specific_category_list']=specific_category
    
    
    extracted_data=[]
    session_id = request.cookies.get('session_id_areas')
    extracted_data.append(dicccc)
    extracted_data_cache_areas[session_id] = extracted_data
    
    
    
    return render_template('index.html',specific_category=extracted_data[0]['specific_category_list'])




@app.route("/main_category", methods=['POST','GET'])
def main_category():
    main_category=request.form['specific_category']
    main_category='-'.join(list(main_category.split(" ")))
    session_id = session.get('session_id_areas')
    extracted_data = extracted_data_cache_areas.get(session_id, [])
    conn=psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
    cur = conn.cursor()
    conn.autocommit= True
    script=f'''
    SELECT content FROM area_new WHERE area='{(extracted_data[0])['main_areas']}'
    '''
    cur.execute(script)
    dataa=cur.fetchall()
    return render_template('index.html',contentt=(dataa[0][0][main_category]),specific_category=extracted_data[0]['specific_category_list'])





#function to download the json file
@app.route("/download_json")
def download_json():
    data_to_json=[]
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extract=[]
    for i in extracted_data:
        if len(i)==9:
            if isinstance(i[0], int) and isinstance(i[8], list ) and isinstance(i[3], list) and isinstance(i[4], list):
                extract.append(i) 
    extracted_data=extract
    for i in range(0,len(extracted_data)):
        data_to_json_format = extracted_data[i][1:]
        data_to_jsons={"URL":data_to_json_format[0],
                        "Law Firm Name": data_to_json_format[1],
                        "Geographic Location": data_to_json_format[2],
                        "City": data_to_json_format[4],
                        "State": data_to_json_format[3],
                        "Phone Number": data_to_json_format[5]
                        }
        data_to_json.append(data_to_jsons)
    json_data = json.dumps(data_to_json)
    response = make_response(json_data)
    response.headers['Content-Disposition'] = 'attachment; filename=data.json'
    response.mimetype = 'application/json'
    return response





#function to download the csv file
@app.route("/download_csv")
def download_csv():
    data_to_json=[]
    session_id = session.get('session_id')
    extracted_data = extracted_data_cache.get(session_id, [])
    extract=[]
    for i in extracted_data:
        if len(i)==9:
            if isinstance(i[0], int) and isinstance(i[8], list ) and isinstance(i[3], list) and isinstance(i[4], list):
                extract.append(i) 
    extracted_data=extract
    for i in range(0,len(extracted_data)):
        data_to_json_format = extracted_data[i][1:]
        data_to_jsons={"URL":data_to_json_format[0],
                        "Law Firm Name": data_to_json_format[1],
                        "Geographic Location": data_to_json_format[2],
                        "City": data_to_json_format[4],
                        "State": data_to_json_format[3],
                        "Phone Number": data_to_json_format[5]
                        }
        data_to_json.append(data_to_jsons)
    data=data_to_json
    def generate_csv():
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["URL","Law Firm Name","Geographic Location","City","State","Phone Number"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate()
    response = Response(stream_with_context(generate_csv()), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=sample_data.csv'
    return response


if __name__ == '__main__':
    app.run(port=5001)



