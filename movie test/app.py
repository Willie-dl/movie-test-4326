#team 4 
#flask imports 
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import sqlite3
#password hasher import
from werkzeug.security import generate_password_hash, check_password_hash
import re
import os

app = Flask(__name__)
#secret key
app.secret_key = b'\xc6\xa8\x0f\x04\xb0\xd4\x05xuv4\xbfa\x17\xc0\xa4\x9eB\x10\x00\xd2\x93\x16\xdb'
#fask debug
#app.config['TEMPLATES_AUTO_RELOAD'] = True

#open movie database integration 
OMDB_API_KEY = 'bff6e1b4'
OMDB_BASE_URL = 'http://www.omdbapi.com/'

#database initilization
@app.before_first_request
def initialize_database():
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    #Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    #Movies
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_imdb_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            genre TEXT,
            release_year TEXT,
            description TEXT,
            poster TEXT
        )
    ''')

    #Watchlist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            user_id INTEGER,
            movie_imdb_id TEXT,
            category TEXT,  -- 'watchlist' or 'plan'
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    #Reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            user_id INTEGER,
            movie_imdb_id TEXT,
            review_text TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
#home route
@app.route('/')
def home():
    return render_template('home.html')

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #get username or email 
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        #check if logged in prompt again if not
        if not identifier or not password:
            flash("Both email/username and password are required.", "danger")
            return redirect(url_for('login'))

        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()

        #Check if an email or a username is imputted in user input box
        #if it has @ = email
        #no @ = username
        if '@' in identifier:
            cursor.execute('SELECT * FROM users WHERE email = ?', (identifier,))
        else:
            cursor.execute('SELECT * FROM users WHERE username = ?', (identifier,))
        
        user = cursor.fetchone()
        conn.close()
        #check if password matches 
        if user and check_password_hash(user[3], password):
            #store user id in session
            session['user_id'] = user[0]
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))
        else:
            #in case user inputs wrong credentials
            flash("Invalid credentials. Please try again.", "danger")
    
    return render_template('login.html')

#register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        #hash the password with sha256
        hashed_password = generate_password_hash(password, method='sha256')
        #insert user into database
        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                           (username, email, hashed_password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        #check for duplicate user
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")
        finally:
            conn.close()
    return render_template('register.html')
#logout route
#disconnects session
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

#profile route
@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'user_id' not in session:
        flash("Please log in to access your profile.", "danger")
        #Redirect to login page if not logged in
        #prevents non registered useres from adding to database
        return redirect(url_for('login')) 
    
    user_id = session['user_id']
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    
    #get watchlist movies from ombd using their IMDB id 
    cursor.execute("SELECT movie_imdb_id FROM watchlist WHERE user_id = ? AND category = 'watchlist'", (user_id,))
    watchlist = cursor.fetchall()

    #get plan to watch list
    cursor.execute("SELECT movie_imdb_id FROM watchlist WHERE user_id = ? AND category = 'plan'", (user_id,))
    plan_to_watch = cursor.fetchall()

    #get reviews with movie ID
    cursor.execute("SELECT movie_imdb_id, review_text FROM reviews WHERE user_id = ?", (user_id,))
    reviews = cursor.fetchall()

    #Initialize lists
    movie_titles = []
    detailed_reviews = []

    #get movie titles for watchlist
    for movie_id in watchlist:
        response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': movie_id[0]})
        movie_data = response.json()
        if movie_data.get('Response') == 'True':
            title = movie_data.get('Title', 'Unknown Title')
            movie_titles.append((title, movie_id[0]))  # Store title with IMDb ID
        else:
            movie_titles.append(("Unknown Title", movie_id[0]))  # Handle case where movie data is not found

    #get movie titles and reviews for Plan to Watch
    plan_movies = []
    for movie_id in plan_to_watch:
        response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': movie_id[0]})
        movie_data = response.json()
        if movie_data.get('Response') == 'True':
            title = movie_data.get('Title', 'Unknown Title')
            plan_movies.append((title, movie_id[0]))  # Store title with IMDb ID
        else:
            plan_movies.append(("Unknown Title", movie_id[0]))  # Handle case where movie data is not found

    #get detailed reviews with movie titles
    for movie_id, review_text in reviews:
        response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': movie_id})
        movie_data = response.json()
        title = movie_data.get('Title', 'Unknown Title')
        detailed_reviews.append((title, movie_id, review_text))  # Store title, IMDb ID, and review text

    conn.close()

    
    return render_template('profile.html', 
                           watchlist=movie_titles,  
                           plan_to_watch=plan_movies, 
                           reviews=detailed_reviews) 


#search page
@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query')
    if query:
        return redirect(url_for('movies', query=query))
    #if user enters nothing
    else:
        flash("Please enter a search term.", "danger")
        return redirect(url_for('home'))

#add to watchlist button
@app.route('/add_to_watchlist/<string:imdb_id>', methods=['POST'])
def add_to_watchlist(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to add movies to your watchlist.", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    category = request.form.get('category')

    if not category:
        flash("Please select a category for the movie.", "danger")
        return redirect(url_for('movies'))

    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    #add to watchlist code
    try:
        cursor.execute("INSERT INTO watchlist (user_id, movie_imdb_id, category) VALUES (?, ?, ?)", (user_id, imdb_id, category))
        conn.commit()
        flash("Movie added to your list!", "success")
    except sqlite3.Error as e:
        flash("An error occurred while adding the movie to the watchlist.", "danger")
    finally:
        conn.close()

    return redirect(url_for('profile'))

@app.route('/add_to_plan/<string:imdb_id>', methods=['POST'])
def add_to_plan(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to add movies to your Plan to Watch list.", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    #Insert into the database to plan to watch 
    try:
        cursor.execute("INSERT INTO watchlist (user_id, movie_imdb_id, category) VALUES (?, ?, 'plan')", (user_id, imdb_id))
        conn.commit()
        flash("Movie added to your Plan to Watch list!", "success")
    except sqlite3.Error as e:
        flash("An error occurred while adding the movie to the Plan to Watch list.", "danger")
    finally:
        conn.close()

    return redirect(url_for('profile'))


@app.route('/remove_from_watchlist/<string:imdb_id>', methods=['POST'])
def remove_from_watchlist(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to manage your Watchlist.", "danger")
        return redirect(url_for('login'))
    #gets user id to remove the movie from list  they made
    user_id = session['user_id']
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM watchlist WHERE user_id = ? AND movie_imdb_id = ? AND category = 'watchlist'", (user_id, imdb_id))
        conn.commit()
        flash("Movie removed from your Watchlist.", "success")
    except sqlite3.Error as e:
        flash("An error occurred while removing the movie.", "danger")
    finally:
        conn.close()

    return redirect(url_for('profile'))


@app.route('/remove_from_plan/<string:imdb_id>', methods=['POST'])
def remove_from_plan(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to manage your Plan to Watch list.", "danger")
        return redirect(url_for('login'))
    #gets user id to remove the movie from list
    user_id = session['user_id']
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM watchlist WHERE user_id = ? AND movie_imdb_id = ? AND category = 'plan'", (user_id, imdb_id))
        conn.commit()
        flash("Movie removed from your Plan to Watch list.", "success")
    except sqlite3.Error as e:
        flash("An error occurred while removing the movie.", "danger")
    finally:
        conn.close()

    return redirect(url_for('profile'))




@app.route('/add_review/<string:imdb_id>', methods=['POST'])
def add_review(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to add a review.", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    review_text = request.form.get('review_text').strip()
    
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reviews (user_id, movie_imdb_id, review_text) VALUES (?, ?, ?)", (user_id, imdb_id, review_text))
    conn.commit()
    conn.close()
    
    flash("Review added successfully!", "success")
    return redirect(url_for('movie_detail', imdb_id=imdb_id))



#deletes reviews from movie page
@app.route('/delete_review/<string:movie_id>', methods=['POST'])
def delete_review(movie_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to delete a review.", "danger")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE user_id = ? AND movie_imdb_id = ?", (user_id, movie_id))
    conn.commit()
    conn.close()
    
    flash("Review deleted successfully!", "success")
    return redirect(url_for('profile'))


#shows movies list
#connected with open movie database
@app.route('/movies')
def movies():
    query = request.args.get('query', 'Batman')
    page = request.args.get('page', 1, type=int)

    response = requests.get(OMDB_BASE_URL, params={
        'apikey': OMDB_API_KEY,
        's': query,
        'page': page
    })
    data = response.json()

    movies_list = []
    total_pages = 1

    if data.get('Response') == 'True':
        omdb_movies = data.get('Search', [])
        total_results = int(data.get('totalResults', 0))
        per_page = 10
        total_pages = (total_results + per_page - 1) // per_page

        for omdb_movie in omdb_movies:
            movies_list.append({
                'Title': omdb_movie.get('Title'),
                'Year': omdb_movie.get('Year'),
                'Poster': omdb_movie.get('Poster'),
                'imdbID': omdb_movie.get('imdbID')
            })
    #if search retuens nothing
    else:
        flash("No movies found.", "danger")

    return render_template('movies.html', movies=movies_list, page=page, total_pages=total_pages, query=query)

#movie detail page
@app.route('/movie/<string:imdb_id>')
def movie_detail(imdb_id):
    #Check if user is logged in
    #Redirect to login page if not logged in
    if 'user_id' not in session:
        flash("Please log in to view movie details.", "danger")
        return redirect(url_for('login'))
    #get movie details using their IMDb ID
    response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': imdb_id})

    movie_data = response.json()

    if movie_data.get('Response') == 'True':
        title = movie_data.get('Title')
        genre = movie_data.get('Genre')
        release_year = movie_data.get('Year')
        description = movie_data.get('Plot')
        poster = movie_data.get('Poster', url_for('static', filename='placeholder.jpg'))

        #show reviews that users leave 
        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT users.username, reviews.review_text
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            WHERE reviews.movie_imdb_id = ?
        """, (imdb_id,))
        reviews = cursor.fetchall()

        conn.close()

        return render_template('movie_detail.html', movie={
            'title': title,
            'genre': genre,
            'release_year': release_year,
            'description': description,
            'poster': poster,
            'imdb_id': imdb_id
        }, reviews=reviews)

    flash("Movie not found in OMDb.", "danger")
    return redirect(url_for('movies'))

#method to manually add movies to the database
#only used if not found in OMDB database
#not really needed unless its some obscure film or some very new fil
#essentially another search 
@app.route('/add_or_update_movie', methods=['POST', 'GET'])
def add_or_update_movie():
    if request.method == 'POST':
        movie_id = request.form.get('movie_id')

        #validate IMDb ID format
        if not movie_id or not re.match(r'^tt\d{7,8}$', movie_id):
            flash("Invalid IMDb ID. Please provide a valid ID like 'tt0111161'.", "danger")
            return redirect(url_for('add_or_update_movie'))

        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()

        #Check if the movie already exists
        cursor.execute("SELECT id FROM movies WHERE movie_imdb_id = ?", (movie_id,))
        existing_movie = cursor.fetchone()
        #Redirect to the movie details page if it exists already
        if existing_movie:
            flash(f"The movie already exists. Redirecting to its details page.", "info")
            conn.close()
            return redirect(url_for('movie_detail', imdb_id=movie_id))

        #get movie details from OMDb
        response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': movie_id})
        if response.ok:
            movie_data = response.json()
            if movie_data.get('Response') == 'True':
                #Extract movie details
                title = movie_data.get('Title')
                genre = movie_data.get('Genre')
                year = movie_data.get('Year')
                description = movie_data.get('Plot')
                poster = movie_data.get('Poster')

                #Add the movie to the database
                cursor.execute("""
                    INSERT INTO movies (movie_imdb_id, title, genre, release_year, description, poster)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (movie_id, title, genre, year, description, poster))
                conn.commit()
                flash(f"Movie '{title}' added successfully!", "success")
            else:
                flash("Movie not found in OMDb. Please check the IMDb ID.", "danger")
        else:
            flash("Failed to fetch movie details. Please try again later.", "danger")

        conn.close()
        return redirect(url_for('add_or_update_movie'))

    return render_template('add_or_update_movie.html')





#debug stuff
# @app.route('/debug_reviews')
# def debug_reviews():
#     conn = sqlite3.connect('movies.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM reviews")
#     reviews = cursor.fetchall()
#     conn.close()
#     return f"All Reviews in database: {reviews}"

# @app.route('/debug_all_reviews')
# def debug_all_reviews():
#     conn = sqlite3.connect('movies.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT users.username, reviews.movie_imdb_id, reviews.review_text FROM reviews JOIN users ON reviews.user_id = users.id")
#     all_reviews = cursor.fetchall()
#     conn.close()

#     # Display all reviews for diagnostic purposes
#     return f"All reviews in database: {all_reviews}"

# @app.route('/debug_users')
# def debug_users():
#     conn = sqlite3.connect('movies.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM users")
#     users = cursor.fetchall()
#     conn.close()
#     return f"Users in database: {users}"

# @app.route('/debug_watchlist')
# def debug_watchlist():
#     conn = sqlite3.connect('movies.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM watchlist")
#     watchlist = cursor.fetchall()
#     conn.close()
#     return f"Watchlist entries: {watchlist}"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

