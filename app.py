import pickle
import base64
import json
import random
import MySQLdb.cursors
import pymysql
import numpy as np
import io
import nltk
nltk.download('popular')
import re
import streamlit as st
import pandas as pd 
import matplotlib.pyplot as plt     
import mysql.connector

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
from sklearn.utils.multiclass import unique_labels
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import TweetTokenizer
from keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from PIL import Image
from functools import wraps
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()

intents = json.loads(open('chatbot/intents.json').read())
words = pickle.load(open('chatbot/words2.pkl','rb'))
classes = pickle.load(open('chatbot/classes2.pkl','rb'))

app = Flask(__name__)
model = load_model('model/model.h5')
model_chat = load_model('chatbot/chatbot_model2.h5')

app.secret_key = 'xyzsdfg'

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'eyeu'

mysql = MySQL(app)

# Fungsi untuk memeriksa apakah pengguna sudah login


def check_logged_in():
    if 'loggedin' not in session:
        return False
    return True

# Dekorator untuk memeriksa login sebelum akses ke halaman


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_logged_in():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods=['GET', 'POST'])
@login_required
def home():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('home.html', user=user, message=message)



@app.route("/login", methods=['GET', 'POST'])
def login():
    mesage = ''
    print(request.form)
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['password'] = user['password']
            return redirect(url_for('home'))
        else:
            mesage = 'Mohon periksa E-mail atau password Anda!'

    return render_template('login.html', mesage=mesage)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('email', None)
    return redirect(url_for('login'))


@ app.route('/register', methods=['GET', 'POST'])
def register():
    mesage = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))
        account = cursor.fetchone()
        if account:
            mesage = 'Akun sudah tersedia!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            mesage = 'Alamat E-mail tidak diketahui!'
        elif not name or not password or not email:
            mesage = 'Mohon Isi form terlebih dahulu !'
        else:
            cursor.execute(
                'INSERT INTO user VALUES (NULL, % s, % s, % s)', (name, email, password, ))
            mysql.connection.commit()
            return redirect(url_for('login'))
    elif request.method == 'POST':
        mesage = 'Please fill out the form !'
    return render_template('register.html', mesage=mesage)


@app.route("/about", methods=['GET', 'POST'])
@login_required
def about():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Mendapatkan jumlah ulasan dari fungsi
    jumlah_ulasan = hitung_jumlah_ulasan()

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('about.html', user=user, message=message, jumlah_ulasan=jumlah_ulasan)



@app.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
            name = request.form['name']
            password = request.form['password']
            email = request.form['email']

            if not name or not password or not email:
                message = 'Mohon isi semua kolom!'
            else:
                cursor.execute(
                    'UPDATE user SET name = %s, email = %s, password = %s WHERE id = %s',
                    (name, email, password, id,)
                )
                mysql.connection.commit()
                return redirect(url_for('profil'))

        cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
        user = cursor.fetchone()
        return render_template('profil.html', user=user, message=message)

    finally:
        cursor.close()


@app.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    id = session.get('id')
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM user WHERE id = %s', (id,))
        mysql.connection.commit()
        return redirect(url_for('register'))
    finally:
        cursor.close()


@app.route("/konsultasi", methods=['GET', 'POST'])
@login_required
def konsultasi():

    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('konsultasi.html', user=user, message=message)


@app.route("/blog")
def blog():
    return render_template("blog1.html")

@app.route("/chatbotest")
def chatbotest():
    return render_template("chatbotest.html")

@app.route("/tester")
@login_required
def tester():
    return render_template("tester.html")


@app.route("/produk", methods=['GET', 'POST'])
@login_required
def produk():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('produk.html', user=user, message=message)


@app.route("/chat", methods=['GET', 'POST'])
@login_required
def chat():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('chat.html', user=user, message=message)


@app.route("/chat/dr-bima-arya-fatah-sp-m", methods=['GET', 'POST'])
@login_required
def chat_dr_bima():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('dr.bima.html', user=user, message=message)


@app.route("/riwayat-deteksi", methods=['GET', 'POST'])
@login_required
def history():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('history.html', user=user, message=message)

@app.route('/deteksi', methods=['GET', 'POST'])
@login_required
def deteksi():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
     

    if request.method == 'POST':
        # Cek apakah file telah dipilih
        if 'file' not in request.files:
            return render_template('deteksi.html', message='File belum dipilih')

        file = request.files['file']

        # Cek apakah file kosong
        if file.filename == '':
            return render_template('deteksi.html', message='File belum dipilih')

        # Simpan file ke direktori tertentu (opsional)
        file_path = 'histori/' + file.filename
        file.save(file_path)

        # Proses file menggunakan model
        img = Image.open(file_path)
        img = np.array(img.resize((94, 55)))
        img = np.expand_dims(img, axis=0)
        pred = model.predict(img)

        # Hapus file yang diunggah setelah diproses (opsional)
        # import os
        # os.remove(file_path)

        # Tampilkan hasil prediksi di halaman web
        # actual_class = 'normal'  # sesuaikan dengan kelas yang sesuai dengan gambar
        predicted_class = 'Normal' if pred[0] > 0.5 else 'Katarak'

        # Konversi gambar ke format yang dapat ditampilkan di HTML
        img_str = image_to_base64(img)

        return render_template('deteksi.html',user=user, message=f'Prediksi: {predicted_class}',
                               predicted_class=predicted_class, img_str=img_str)

    return render_template('deteksi.html', user=user, message=message)

def image_to_base64(image):
    # Konversi gambar menjadi format base64 agar bisa ditampilkan di HTML
    img = Image.fromarray(image[0])
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = "data:image/png;base64," + \
        base64.b64encode(buffer.getvalue()).decode()
    return img_str


@app.route("/chatbot")
def chatbot():
    id = session.get('id')
    message = ''
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM user WHERE id = %s', (id,))
    user = cursor.fetchone()
    return render_template('chatbot.html', user=user, message=message)

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    return chatbot_response(userText)

def clean_up_sentence(sentence):
    # tokenize the pattern - split words into array
    sentence_words = nltk.word_tokenize(sentence)
    # stem each word - create short form for word
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence

def bow(sentence, words, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0]*len(words)  
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s: 
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    return(np.array(bag))

def predict_class(sentence, model_chat):
    # filter out predictions below a threshold
    p = bow(sentence, words,show_details=False)
    res = model_chat.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def getResponse(ints, intents_json):
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if(i['tag']== tag):
            result = random.choice(i['responses'])
            break
    return result

def chatbot_response(msg):
    ints = predict_class(msg, model_chat)
    res = getResponse(ints, intents)
    return res

@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

# Database configuration
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'eyeu',
}

# Function to insert data into MySQL
def insert_data_to_mysql(data):
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # Modify the SQL statement to include id_review as auto-increment
            sql = """
                CREATE TABLE IF NOT EXISTS input_review (
                    id_review INT AUTO_INCREMENT PRIMARY KEY,
                    nama VARCHAR(255) NOT NULL,
                    tanggal TIMESTAMP NOT NULL,
                    review TEXT NOT NULL
                )
            """
            cursor.execute(sql)

            # Insert data into the table
            sql_insert = "INSERT INTO input_review (nama,  review) VALUES (%s, %s)"
            cursor.execute(sql_insert, (data['nama'], data['review']))
        connection.commit()
        print("Data inserted successfully!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        connection.close()

# Enable CORS for all routes
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

app.after_request(add_cors_headers)

# Route to render the form



# Route to handle form submission
@app.route('/submit', methods=['POST', 'OPTIONS'], endpoint='submit_form')
def submit_form():
    if request.method == 'OPTIONS':
        # Preflight request, respond successfully
        return jsonify({'status': 'success'})

    data_to_insert = request.get_json()
    insert_data_to_mysql(data_to_insert)
    return jsonify({'status': 'success'})

@app.route('/visualisasi')
def visualisasi():
   return render_template('visualisasi.html')

from flask import Response
import time

@app.route('/visualisasi-data')
def visualisasi_data():
   start_time = time.time()
   while True:
       # Ambil data dari database atau sumber lain
       data = {
           'labels': ['Positif', 'Negatif', 'Netral'],
           'values': [jumlah_positif, jumlah_negatif, jumlah_netral]
       }
       # Jika data sudah ada, atau sudah mencapai waktu timeout, kirim data sebagai respon
       if data or time.time() > start_time + 30: # 30 detik adalah waktu timeout
           return jsonify(data)
       # Jika belum ada data, tunda respon selama 1 detik
       time.sleep(1)


# Pembuatan Dashboard
import pandas as pd
import matplotlib.pyplot as plt

#Implementasi Model
import nltk
import re
import pickle
from sklearn.utils.multiclass import unique_labels
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.tokenize import TweetTokenizer

#DBMS
import pymysql
def is_table_empty(table, host='localhost', user='root', password='', database='eyeu'):
    # Establish a connection to the MySQL database
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    
    # Create a cursor object to execute SQL queries
    cursor = connection.cursor()
    
    # Check if the table is empty
    query_check_empty = f"SELECT COUNT(*) FROM {table}"
    cursor.execute(query_check_empty)
    count_result = cursor.fetchone()[0]

    # Close the cursor and the database connection
    cursor.close()
    connection.close()

    return count_result == 0

#Implemnetasi Model dengan Data Baru
def read_mysql_table(table, host='localhost', user='root', password='', database='eyeu'):
    # Establish a connection to the MySQL database
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    
    # Create a cursor object to execute SQL queries
    cursor = connection.cursor()
    
    query = f"SELECT * FROM {table}"
    cursor.execute(query)
    result = cursor.fetchall()
    
    # Convert the result to a Pandas DataFrame
    df = pd.DataFrame(result)
    
    # Assign column names based on the cursor description
    df.columns = [column[0] for column in cursor.description]
    
    # Close the cursor and the database connection
    cursor.close()
    connection.close()
    
    return df

table_name = 'input_review'

if not is_table_empty(table_name):
    df = read_mysql_table(table_name)
    # #menyimpan tweet. (tipe data series pandas)
    data_content = df['review']

    # casefolding
    data_casefolding = data_content.str.lower()
    data_casefolding.head()

    #filtering

    #url
    filtering_url = [re.sub(r'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''', " ", str(tweet)) for tweet in data_casefolding]
    #cont
    filtering_cont = [re.sub(r'\(cont\)'," ", tweet)for tweet in filtering_url]
    #punctuatuion
    filtering_punctuation = [re.sub('[!"”#$%&’()*+,-./:;<=>?@[\]^_`{|}~]', ' ', tweet) for tweet in filtering_cont]
    #  hapus #tagger
    filtering_tagger = [re.sub(r'#([^\s]+)', '', tweet) for tweet in filtering_punctuation]
    #numeric
    filtering_numeric = [re.sub(r'\d+', ' ', tweet) for tweet in filtering_tagger]

    # # filtering RT , @ dan #
    # fungsi_clen_rt = lambda x: re.compile('\#').sub('', re.compile('rt @').sub('@', x, count=1).strip())
    # clean = [fungsi_clen_rt for tweet in filtering_numeric]

    data_filtering = pd.Series(filtering_numeric)

    # #tokenize
    tknzr = TweetTokenizer()
    data_tokenize = [tknzr.tokenize(tweet) for tweet in data_filtering]
    data_tokenize

    #slang word
    path_dataslang = open("Data/kamus_bahasa_baku_halodoc1000.csv")
    dataslang = pd.read_csv(path_dataslang, encoding = 'utf-8', header=None, sep=";")

    def replaceSlang(word):
      if word in list(dataslang[0]):
        indexslang = list(dataslang[0]).index(word)
        return dataslang[1][indexslang]
      else:
        return word

    data_formal = []
    for data in data_tokenize:
      data_clean = [replaceSlang(word) for word in data]
      data_formal.append(data_clean)
    len_data_formal = len(data_formal)
    # print(data_formal)
    # len_data_formal

    nltk.download('stopwords')
    default_stop_words = nltk.corpus.stopwords.words('indonesian')
    stopwords = set(default_stop_words)

    def removeStopWords(line, stopwords):
      words = []
      for word in line:  
        word=str(word)
        word = word.strip()
        if word not in stopwords and word != "" and word != "&":
          words.append(word)

      return words
    reviews = [removeStopWords(line,stopwords) for line in data_formal]

    # Specify the file path of the pickle file
    file_path = 'model/training.pickle'

    # Read the pickle file
    with open(file_path, 'rb') as file:
        data_train = pickle.load(file)
        
    # pembuatan vector kata
    vectorizer = TfidfVectorizer()
    train_vector = vectorizer.fit_transform(data_train)
    reviews2 = [" ".join(r) for r in reviews]

    load_model = pickle.load(open('model/model_svm.pkl','rb'))

    result = []

    for test in reviews2:
        test_data = [str(test)]
        test_vector = vectorizer.transform(test_data)
        pred = load_model.predict(test_vector)
        result.append(pred[0])
        
    unique_labels(result)

    df['label'] = result

    def delete_all_data_from_table(table, host='localhost', user='root', password='', database='eyeu'):
        # Establish a connection to the MySQL database
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        
        # Create a cursor object to execute SQL queries
        cursor = connection.cursor()
        
        # Delete all data from the specified table
        query = f"DELETE FROM {table}"
        cursor.execute(query)
        
        # Commit the changes
        connection.commit()
        
        # Close the cursor and the database connection
        cursor.close()
        connection.close()

    delete_all_data_from_table('input_review')

    def insert_df_into_hasil_model(df, host='localhost', user='root', password='', database='eyeu'):
        # Establish a connection to the MySQL database
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

        # Create a cursor object to execute SQL queries
        cursor = connection.cursor()

        # Insert each row from the DataFrame into the 'hasil_model' table
        for index, row in df.iterrows():
            query = "INSERT INTO hasil_model (id_review, nama, tanggal, review, label) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (row['id_review'], row['nama'], row['tanggal'], row['review'], row['label']))

        # Commit the changes
        connection.commit()

        # Close the cursor and the database connection
        cursor.close()
        connection.close()

    insert_df_into_hasil_model(df)

    table_name = 'hasil_model'
    hasil_df = read_mysql_table(table_name)
    hasil_df.to_csv('Data/hasil_model.csv')
    data = pd.read_csv('Data/hasil_model.csv')
else:
    # Membaca data dari file CSV
    data = pd.read_csv('Data/hasil_model.csv')

data = data[['review', 'label']]

# Menghitung jumlah data dengan label positif, negatif, dan netral
jumlah_positif = len(data[data['label'] == 1])
jumlah_negatif = len(data[data['label'] == 0])
jumlah_netral = len(data[data['label'] == -1])

#Menghitung jumlah ulasan pada tentang kami 
def hitung_jumlah_ulasan(host='localhost', user='root', password='', database='eyeu'):
    try:
        # Konfigurasi koneksi ke database MySQL
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
   
        # Membuat kursor
        cursor = connection.cursor()

        # Query SQL untuk menjumlahkan data ulasan
        query = f"SELECT COUNT(*) FROM hasil_model"

        # Mengeksekusi query
        cursor.execute(query)

         # Mendapatkan hasil
        hasil_jumlah = cursor.fetchone()[0]

        # Menampilkan hasil
        print(f"Jumlah Ulasan: {hasil_jumlah}")

        return hasil_jumlah  # Return the counted value

    except pymysql.Error as e:
        print(f"Error: {e}")

    finally:
        # Menutup kursor dan koneksi
        cursor.close()
        connection.close()

# Panggil fungsi untuk menjumlahkan data ulasan
hitung_jumlah_ulasan()

if __name__ == '__main__':
    app.run(debug=True)