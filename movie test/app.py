#flask imports 
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import sqlite3
#password hasher import
from werkzeug.security import generate_password_hash, check_password_hash
import re
from markupsafe import escape
from flask import jsonify


app = Flask(__name__)
#secret key
app.secret_key = b'\xc6\xa8\x0f\x04\xb0\xd4\x05xuv4\xbfa\x17\xc0\xa4\x9eB\x10\x00\xd2\x93\x16\xdb'
#fask debug
#app.config['TEMPLATES_AUTO_RELOAD'] = True

#open movie database integration 
OMDB_API_KEY = 'bff6e1b4'
OMDB_BASE_URL = 'http://www.omdbapi.com/'

#database initilization
@app.before_request
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

    # Create the reviews table with the review_id as the primary key if it doesn't exist
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



def sanitize_input(input_text):
    #Sanitize user input to prevent harmful inputs
    if not input_text:
        return ''
    #Remove SQL meta-characters 
    sanitized = re.sub(r'[;\'\"--]', '', input_text)
    return escape(sanitized.strip())



def validate_username(username):
    #Validate username to allow only alphanumeric and underscores
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username)) and len(username) <= 50


def validate_email(email):
    #Validate email format
    return bool(re.match(r'^[^@]+@[^@]+\.[^@]+$', email)) and len(email) <= 100


#home route
@app.route('/')
def home():
    return render_template('home.html')

# #login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = sanitize_input(request.form.get('identifier'))
        password = request.form.get('password')

        if not identifier or not password:
            flash("Both email/username and password are required.", "danger")
            return redirect(url_for('login'))

        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()

        if '@' in identifier and validate_email(identifier):
            cursor.execute('SELECT * FROM users WHERE email = ?', (identifier,))
        elif validate_username(identifier):
            cursor.execute('SELECT * FROM users WHERE username = ?', (identifier,))
        else:
            flash("Invalid username or email format.", "danger")
            return redirect(url_for('login'))

        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template('login.html')



# #register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username'))
        email = sanitize_input(request.form.get('email'))
        password = request.form.get('password')

        if not validate_username(username):
            flash("Invalid username. Use only letters, numbers, and underscores.", "danger")
            return redirect(url_for('register'))

        if not validate_email(email):
            flash("Invalid email address.", "danger")
            return redirect(url_for('register'))

        if not password or len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        conn = sqlite3.connect('movies.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                           (username, email, hashed_password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
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

    # Fetch the logged-in user's username
    cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    # If user is not found, you can return to login or handle it
    if user_data:
        user_name = user_data[0]
    else:
        flash("User not found.", "danger")
        return redirect(url_for('login'))
    
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
                           user_name=user_name,  # Pass user_name to the template
                           watchlist=movie_titles,  
                           plan_to_watch=plan_movies, 
                           reviews=detailed_reviews) 


# #search page
@app.route('/search', methods=['POST'])
def search():
    query = sanitize_input(request.form.get('query'))
    
    # Check for dangerous patterns
    if re.search(r"(DROP|DELETE|INSERT|ALTER|UPDATE|--|;)", query, re.IGNORECASE):
        flash("Invalid search term detected.", "danger")
        return redirect(url_for('home'))
    
    if query:
        return redirect(url_for('movies', query=query))
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
   # Check if the movie is already in the user's watchlist for the selected category
    cursor.execute("SELECT * FROM watchlist WHERE user_id = ? AND movie_imdb_id = ? AND category = ?", 
                   (user_id, imdb_id, category))
    existing_entry = cursor.fetchone()

    if existing_entry:
        flash("This movie is already in your watchlist.", "info")
    else:
        try:
            cursor.execute("INSERT INTO watchlist (user_id, movie_imdb_id, category) VALUES (?, ?, ?)", 
                           (user_id, imdb_id, category))
            conn.commit()
            flash("Movie added to your list!", "success")
        except sqlite3.Error as e:
            flash("An error occurred while adding the movie to the watchlist.", "danger")
            
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
    
    # Check if the movie is already in the user's "Plan to Watch" list
    cursor.execute("SELECT * FROM watchlist WHERE user_id = ? AND movie_imdb_id = ? AND category = 'plan'", (user_id, imdb_id))
    existing_movie = cursor.fetchone()
    
    if existing_movie:
        flash("This movie is already in your Plan to Watch list.", "warning")
        return redirect(url_for('profile'))  # or another appropriate redirect

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

#route to adding a review to a movie
@app.route('/add_review/<string:imdb_id>', methods=['POST'])
def add_review(imdb_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        flash("Please log in to add a review.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    review_text = sanitize_input(request.form.get('review_text'))

    # Detect suspicious patterns
    if re.search(r"(DROP|DELETE|INSERT|ALTER|UPDATE|--|;)", review_text, re.IGNORECASE):
        print(f"Suspicious input detected: {review_text}")
        flash("Invalid input detected in review.", "danger")
        return redirect(url_for('movie_detail', imdb_id=imdb_id))

    if not review_text or len(review_text) > 500:
        flash("Invalid review. Please ensure it is not empty and under 500 characters.", "danger")
        return redirect(url_for('movie_detail', imdb_id=imdb_id))

    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    # Check if the user has already reviewed this movie
    cursor.execute("SELECT * FROM reviews WHERE user_id = ? AND movie_imdb_id = ?", (user_id, imdb_id))
    existing_review = cursor.fetchone()

    if existing_review:
        # Flash a warning message if the user has already written a review
        flash("You have already reviewed this movie.", "info")
    else:
        # Add the review if it doesn't already exist
        cursor.execute("INSERT INTO reviews (user_id, movie_imdb_id, review_text) VALUES (?, ?, ?)",
                       (user_id, imdb_id, review_text))
        conn.commit()
        flash("Review added successfully!", "success")

    conn.close()
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
    query = sanitize_input(request.args.get('query', 'Batman'))
    page = request.args.get('page', 1, type=int)

    # Detect suspicious patterns
    if re.search(r"(DROP|DELETE|INSERT|ALTER|UPDATE|--|;)", query, re.IGNORECASE):
        print(f"Suspicious input detected: {query}")
        flash("Invalid input detected.", "danger")
        return redirect(url_for('home'))

    response = requests.get(OMDB_BASE_URL, params={
        'apikey': OMDB_API_KEY,
        's': query,
        'page': page
    })

    if response.status_code != 200 or not response.text.strip():
        flash("Failed to fetch movies. Please try again later.", "danger")
        return redirect(url_for('home'))

    data = response.json()

    if not data.get('Response') or data.get('Response') == 'False':
        flash(data.get('Error', "No movies found."), "danger")
        return redirect(url_for('home'))

    movies_list = []
    total_pages = 1

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

    return render_template('movies.html', movies=movies_list, page=page, total_pages=total_pages, query=query)

#movie detail page
@app.route('/movie/<string:imdb_id>')
def movie_detail(imdb_id):
    # Check if user is logged in
    if 'user_id' not in session:
        flash("Please log in to view movie details.", "danger")
        return redirect(url_for('login'))
    
    # Get movie details using their IMDb ID
    response = requests.get(OMDB_BASE_URL, params={'apikey': OMDB_API_KEY, 'i': imdb_id})

    # Check if the response status code is 200 (OK)
    if response.status_code == 200:
        try:
            movie_data = response.json()  # Attempt to decode the JSON response

            # Handle the case where OMDb response doesn't have a valid movie
            if movie_data.get('Response') == 'True':
                title = movie_data.get('Title')
                genre = movie_data.get('Genre')
                release_year = movie_data.get('Year')
                description = movie_data.get('Plot')
                poster = movie_data.get('Poster', url_for('static', filename='placeholder.jpg'))

                # Show reviews that users leave 
                conn = sqlite3.connect('movies.db')
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT users.id, users.username, reviews.review_text
                    FROM reviews
                    JOIN users ON reviews.user_id = users.id
                    WHERE reviews.movie_imdb_id = ?
                """, (imdb_id,))
                reviews = cursor.fetchall()

                # Check if the logged-in user has already reviewed this movie
                user_id = session['user_id']
                cursor.execute("SELECT users.username, reviews.review_text FROM reviews JOIN users ON reviews.user_id = users.id WHERE reviews.user_id = ? AND reviews.movie_imdb_id = ?", (user_id, imdb_id))
                existing_review = cursor.fetchone()

                conn.close()

                # If the user has already reviewed
                if existing_review:
                    username = existing_review[0]  # Get the username
                    review_text = existing_review[1]  # Get the review text
                    # Remove the user's review from the list of reviews
                    reviews = [r for r in reviews if r[1] != username]
                    # Insert the current user's review at the top of the list
                    reviews.insert(0, (user_id, username, review_text))

                return render_template('movie_detail.html', movie={
                    'title': title,
                    'genre': genre,
                    'release_year': release_year,
                    'description': description,
                    'poster': poster,
                    'imdb_id': imdb_id
                }, reviews=reviews, has_reviewed=bool(existing_review), user_id=user_id)

            else:
                flash("Movie not found in OMDb.", "danger")
                return redirect(url_for('movies'))

        except requests.exceptions.JSONDecodeError:
            flash("Error decoding movie data from OMDb.", "danger")
            return redirect(url_for('movies'))

    else:
        flash(f"Failed to retrieve movie details. Status code: {response.status_code}", "danger")
        return redirect(url_for('movies'))
    
@app.route('/edit_review/<imdb_id>', methods=['POST'])
def edit_review(imdb_id):
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('Please log in to edit your review.', 'error')
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    user_id = session['user_id']
    review_text = request.form.get('review_text')

    # Validate the review text
    if not review_text or len(review_text) > 500:
        flash('Review must be under 500 characters.', 'error')
        return redirect(url_for('movie_detail', imdb_id=imdb_id))  # Redirect to movie detail page if validation fails

    # Update the review in the database
    conn = sqlite3.connect('movies.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reviews 
        SET review_text = ? 
        WHERE user_id = ? 
        AND movie_imdb_id = ?
    """, (review_text, user_id, imdb_id))
    conn.commit()

    conn.close()

    flash('Your review has been updated successfully!', 'success')
    return redirect(url_for('movie_detail', imdb_id=imdb_id))




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
            return redirect(url_for('home'))

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

        # After processing, return to the home page with flash messages
        return redirect(url_for('home'))

    return '', 204  # In case the request method is not POST, do nothing

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)

